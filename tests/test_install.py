"""Installer tests: every destination is inside a TemporaryDirectory."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).absolute().parent.parent
spec = importlib.util.spec_from_file_location("cygma_installer", REPOSITORY / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = installer
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cygma-install-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.target = self.base / "isolated target"
        self.layout = installer.Layout.create(self.target, "linux")
        self.create_sources()

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def create_sources(self):
        package = {"name": "cygma-themes", "publisher": "cygma-audio", "version": "0.1.0",
                   "engines": {"vscode": "^1.80.0"}, "contributes": {"themes": []}}
        schemes = []
        for variant in installer.VARIANTS:
            label = f"Cygma {variant.title()}"
            package["contributes"]["themes"].append({"label": label, "uiTheme": "vs-dark", "path": f"./themes/cygma-{variant}.json"})
            schemes.append({"name": label, "background": "#101010"})
            for relative in (f"vscode/themes/cygma-{variant}.json", f"kitty/cygma-{variant}.conf",
                             f"alacritty/cygma-{variant}.toml", f"wezterm/cygma-{variant}.toml",
                             f"neovim/colors/cygma_{variant}.lua", f"gtk/cygma-{variant}/gtk-3.0/gtk.css",
                             f"gtk/cygma-{variant}/gtk-4.0/gtk.css"):
                self.write(self.repository / "ports" / relative, f"fixture {relative}\n".encode())
        self.write(self.repository / "ports/vscode/package.json", installer.json_bytes(package))
        self.write(self.repository / "ports/vscode/LICENSE", b"MIT fixture license\n")
        self.write(self.repository / "ports/windows-terminal/cygma.json", installer.json_bytes({"schemes": schemes}))

    def run_install(self, apps=None, variants=None, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return installer.run(self.layout, self.repository, apps or ["kitty"], variants or ["ember"], **kwargs)

    def theme(self, app="kitty", variant="ember"):
        return self.layout.targets(app, variant)["theme"]

    def manifest(self):
        return json.loads((self.layout.state / "manifest.json").read_text(encoding="utf-8"))

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.skipTest(f"This environment cannot create symlinks: {error}")

    def test_dry_run_creates_nothing(self):
        self.run_install(apps=["all"], variants=["all"], dry_run=True)
        self.assertFalse(self.target.exists())

    def test_install_uninstall_all_supported_linux_apps(self):
        self.run_install(apps=["all"], variants=["all"])
        manifest = self.manifest()
        self.assertEqual(len(manifest["files"]), 36)
        for path in manifest["files"]:
            self.assertTrue(Path(path).is_relative_to(self.target))
            self.assertTrue(Path(path).is_file())
        self.run_install(apps=["all"], variants=["all"], uninstall=True)
        self.assertEqual(self.manifest()["files"], {})
        for path in manifest["files"]:
            self.assertFalse(Path(path).exists())

    def test_install_uninstall_all_supported_windows_apps(self):
        self.layout = installer.Layout.create(self.target, "windows")
        self.run_install(apps=["all"], variants=["all"])
        self.assertEqual(len(self.manifest()["files"]), 30)
        self.assertIn("AppData", str(self.theme("neovim")))
        self.assertIn("AppData", str(self.theme("alacritty")))
        self.assertNotIn(".config", str(self.theme("wezterm")))
        fragment = json.loads(self.theme("windows-terminal").read_text())
        self.assertEqual([scheme["name"] for scheme in fragment["schemes"]], ["Cygma Ember"])
        self.assertFalse((self.layout.local / "Packages").exists())
        self.run_install(apps=["all"], variants=["all"], uninstall=True)
        self.assertEqual(self.manifest()["files"], {})

    def test_backups_restore_prior_bytes_and_mode(self):
        self.write(self.theme(), b"prior custom Cygma file\x00\xff")
        os.chmod(self.theme(), 0o600)
        original_mode = stat.S_IMODE(self.theme().stat().st_mode)
        self.run_install()
        entry = self.manifest()["files"][str(self.theme())]
        self.assertEqual((self.layout.state / entry["backup"]).read_bytes(), b"prior custom Cygma file\x00\xff")
        self.run_install(uninstall=True)
        self.assertEqual(self.theme().read_bytes(), b"prior custom Cygma file\x00\xff")
        self.assertEqual(stat.S_IMODE(self.theme().stat().st_mode), original_mode)

    def test_reinstall_is_idempotent_and_updates_keep_original_backup(self):
        self.write(self.theme(), b"original")
        self.run_install()
        initial = self.manifest()["files"][str(self.theme())]
        self.assertEqual(self.run_install(), 0)
        self.write(self.repository / "ports/kitty/cygma-ember.conf", b"updated theme")
        self.run_install()
        self.assertEqual(self.theme().read_bytes(), b"updated theme")
        self.assertEqual(self.manifest()["files"][str(self.theme())]["backup"], initial["backup"])
        self.run_install(uninstall=True)
        self.assertEqual(self.theme().read_bytes(), b"original")

    def test_variants_and_vscode_extensions_are_independent(self):
        self.run_install(apps=["vscode"], variants=["ember", "porcelain"])
        package_path = self.layout.targets("vscode", "ember")["package.json"]
        package = json.loads(package_path.read_text())
        self.assertEqual(package["name"], "cygma-ember")
        self.assertEqual(len(package["contributes"]["themes"]), 1)
        self.run_install(apps=["vscode"], variants=["ember"], uninstall=True)
        self.assertFalse(self.theme("vscode", "ember").exists())
        self.assertTrue(self.theme("vscode", "porcelain").exists())

    def test_uninstall_never_touches_untracked_files(self):
        self.write(self.theme(), b"not installed by us")
        unrelated = self.theme().parent / "other.conf"
        self.write(unrelated, b"other")
        self.run_install(uninstall=True)
        self.assertEqual(self.theme().read_bytes(), b"not installed by us")
        self.assertEqual(unrelated.read_bytes(), b"other")
        self.assertFalse(self.layout.state.exists())

    def test_modified_theme_blocks_entire_uninstall(self):
        self.run_install(variants=["all"])
        first = self.theme().read_bytes()
        self.write(self.theme(variant="porcelain"), b"user edits")
        with self.assertRaisesRegex(installer.InstallError, "changed or removed"):
            self.run_install(variants=["all"], uninstall=True)
        self.assertEqual(self.theme().read_bytes(), first)
        self.assertEqual(self.theme(variant="porcelain").read_bytes(), b"user edits")
        self.assertEqual(len(self.manifest()["files"]), 3)

    def test_modified_theme_blocks_reinstall(self):
        self.run_install()
        self.write(self.theme(), b"user edits")
        with self.assertRaises(installer.InstallError):
            self.run_install()
        self.assertEqual(self.theme().read_bytes(), b"user edits")

    def test_missing_managed_file_is_not_silently_replaced(self):
        self.run_install()
        self.theme().unlink()
        with self.assertRaises(installer.InstallError):
            self.run_install()

    def test_corrupted_backup_refuses_uninstall(self):
        self.write(self.theme(), b"original")
        self.run_install()
        entry = self.manifest()["files"][str(self.theme())]
        (self.layout.state / entry["backup"]).write_bytes(b"corrupted")
        before = self.theme().read_bytes()
        with self.assertRaisesRegex(installer.InstallError, "Backup is missing or changed"):
            self.run_install(uninstall=True)
        self.assertEqual(self.theme().read_bytes(), before)

    def test_failure_rolls_back_every_file_and_manifest(self):
        self.write(self.theme(), b"original")
        original_atomic_write = installer.atomic_write
        failed = False

        def fail_once(path, content, mode=0o644):
            nonlocal failed
            if path.name == "manifest.json" and not failed:
                failed = True
                raise OSError("simulated full disk")
            return original_atomic_write(path, content, mode)

        with patch.object(installer, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated full disk"):
                self.run_install(variants=["all"])
        self.assertTrue(failed)
        self.assertEqual(self.theme().read_bytes(), b"original")
        self.assertFalse(self.theme(variant="porcelain").exists())
        self.assertFalse((self.layout.state / "manifest.json").exists())
        self.assertFalse((self.layout.state / ".lock").exists())
        self.assertFalse(list(self.target.rglob(".cygma-*")))

    def test_uninstall_failure_rolls_back_deletes_and_restores(self):
        self.write(self.theme(), b"prior")
        self.run_install(variants=["all"])
        before = {path: Path(path).read_bytes() for path in self.manifest()["files"]}
        before_manifest = (self.layout.state / "manifest.json").read_bytes()
        atomic = installer.atomic_write
        failed = False

        def fail_once(path, content, mode=0o644):
            nonlocal failed
            if path.name == "manifest.json" and not failed:
                failed = True
                raise OSError("simulated manifest failure")
            return atomic(path, content, mode)

        with patch.object(installer, "atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError):
                self.run_install(variants=["all"], uninstall=True)
        for path, content in before.items():
            self.assertEqual(Path(path).read_bytes(), content)
        self.assertEqual((self.layout.state / "manifest.json").read_bytes(), before_manifest)

    def test_failed_rollback_keeps_the_original_recovery_backup(self):
        self.write(self.theme(), b"original bytes")
        atomic = installer.atomic_write
        transaction_failed = False

        def fail_transaction_and_recovery(path, content, mode=0o644):
            nonlocal transaction_failed
            if path.name == "manifest.json":
                transaction_failed = True
                raise OSError("simulated manifest write failure")
            if transaction_failed and path == self.theme():
                raise OSError("simulated original restore failure")
            return atomic(path, content, mode)

        with patch.object(installer, "atomic_write", side_effect=fail_transaction_and_recovery):
            with self.assertRaisesRegex(installer.InstallError, "Rollback needs manual recovery"):
                self.run_install()
        backups = list((self.layout.state / "backups").glob("*.bin"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"original bytes")
        self.assertFalse((self.layout.state / ".lock").exists())

    def test_source_missing_preflight_does_not_write_anything(self):
        (self.repository / "ports/kitty/cygma-nocturne.conf").unlink()
        with self.assertRaisesRegex(installer.InstallError, "Missing generated theme"):
            self.run_install(variants=["all"])
        self.assertFalse(self.target.exists())

    def test_manifest_cannot_redirect_targets_outside_isolated_root(self):
        self.run_install()
        outside = self.base / "outside.txt"
        self.write(outside, b"must remain")
        manifest = self.manifest()
        entry = manifest["files"].pop(str(self.theme()))
        entry["target"] = str(outside)
        manifest["files"][str(outside)] = entry
        self.write(self.layout.state / "manifest.json", installer.json_bytes(manifest))
        with self.assertRaisesRegex(installer.InstallError, "Invalid manifest"):
            self.run_install(uninstall=True)
        self.assertEqual(outside.read_bytes(), b"must remain")

    def test_manifest_cannot_redirect_backup(self):
        self.write(self.theme(), b"prior")
        self.run_install()
        manifest = self.manifest()
        manifest["files"][str(self.theme())]["backup"] = "../../outside"
        self.write(self.layout.state / "manifest.json", installer.json_bytes(manifest))
        with self.assertRaisesRegex(installer.InstallError, "Invalid manifest"):
            self.run_install(uninstall=True)

    def test_symlink_destination_is_refused(self):
        outside = self.base / "outside"
        self.write(outside, b"must remain")
        self.theme().parent.mkdir(parents=True)
        self.symlink(self.theme(), outside)
        with self.assertRaisesRegex(installer.InstallError, "symlink or reparse point"):
            self.run_install()
        self.assertEqual(outside.read_bytes(), b"must remain")

    def test_symlink_parent_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.target.mkdir()
        self.symlink(self.layout.home, outside, directory=True)
        with self.assertRaisesRegex(installer.InstallError, "symlink or reparse point"):
            self.run_install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_source_is_refused(self):
        source = self.repository / "ports/kitty/cygma-ember.conf"
        source.unlink()
        outside = self.base / "outside"
        self.write(outside, b"must not copy")
        self.symlink(source, outside)
        with self.assertRaisesRegex(installer.InstallError, "symlink or reparse point"):
            self.run_install()
        self.assertFalse(self.target.exists())

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_windows_junction_parent_is_refused(self):
        import _winapi
        outside = self.base / "outside"
        outside.mkdir()
        self.target.mkdir()
        _winapi.CreateJunction(str(outside), str(self.layout.home))
        with self.assertRaisesRegex(installer.InstallError, "symlink or reparse point"):
            self.run_install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_hardlinked_destination_is_refused(self):
        outside = self.base / "outside"
        self.write(outside, b"must remain")
        self.theme().parent.mkdir(parents=True)
        try:
            os.link(outside, self.theme())
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaisesRegex(installer.InstallError, "one link"):
            self.run_install()
        self.assertEqual(outside.read_bytes(), b"must remain")

    def test_lock_does_not_get_removed_by_second_installer(self):
        self.write(self.layout.state / ".lock", b"another instance")
        with self.assertRaisesRegex(installer.InstallError, "lock exists"):
            self.run_install()
        self.assertEqual((self.layout.state / ".lock").read_bytes(), b"another instance")
        self.assertFalse(self.theme().exists())

    def test_target_root_ignores_user_environment_paths(self):
        outside = self.base / "outside"
        variables = {key: str(outside) for key in ("HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "KITTY_CONFIG_DIRECTORY", "NVIM_APPNAME")}
        with patch.dict(os.environ, variables):
            self.layout = installer.Layout.create(self.target, "windows")
            self.run_install(apps=["all"], variants=["all"])
        self.assertFalse(outside.exists())
        for target in self.manifest()["files"]:
            self.assertTrue(Path(target).is_relative_to(self.target))

    def test_unsupported_platform_apps_and_parent_traversal_are_refused(self):
        with self.assertRaises(installer.InstallError):
            self.run_install(apps=["windows-terminal"])
        with self.assertRaises(installer.InstallError):
            self.run_install(apps=["all", "windows-terminal"])
        with self.assertRaises(installer.InstallError):
            installer.Layout.create(self.target / ".." / "elsewhere", "linux")
        with self.assertRaises(installer.InstallError):
            installer.Layout.create(platform="windows")
        self.assertFalse(self.target.exists())

    def prepare_wrapper(self):
        destination = self.repository / "scripts"
        destination.mkdir()
        for name in ("install.py", "install.sh", "install.ps1"):
            shutil.copyfile(REPOSITORY / "scripts" / name, destination / name)
        return destination

    def test_powershell_wrapper_forwards_arguments_and_exit_status(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            self.skipTest("PowerShell is not installed")
        scripts = self.prepare_wrapper()
        command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "install.ps1")]
        result = subprocess.run(command + ["--app", "kitty", "--app", "neovim", "--variant", "ember", "--variant", "porcelain", "--dry-run", "--target-root", str(self.target), "--platform", "linux"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cygma-porcelain.conf", result.stdout)
        self.assertIn("cygma_ember.lua", result.stdout)
        self.assertFalse(self.target.exists())
        failed = subprocess.run(command + ["--app", "invalid", "--target-root", str(self.target)], text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)

    def test_bash_wrapper_forwards_arguments_and_exit_status(self):
        bash = shutil.which("bash")
        if not bash and os.name == "nt":
            candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
            bash = str(candidate) if candidate.is_file() else None
        if not bash:
            self.skipTest("Bash is not installed")
        scripts = self.prepare_wrapper()
        command = [bash, str(scripts / "install.sh").replace("\\", "/")]
        result = subprocess.run(command + ["--app", "kitty", "--app", "neovim", "--variant", "ember", "--dry-run", "--target-root", str(self.target), "--platform", "linux"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cygma_ember.lua", result.stdout)
        self.assertFalse(self.target.exists())
        failed = subprocess.run(command + ["--app", "invalid", "--target-root", str(self.target)], text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
