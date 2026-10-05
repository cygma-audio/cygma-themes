#!/usr/bin/env python3
"""Install local Cygma theme files, with verified backups and reversible changes."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from dataclasses import dataclass

VARIANTS = ("ember", "porcelain", "nocturne")
APPS = ("vscode", "vscodium", "windows-terminal", "kitty", "alacritty", "wezterm", "neovim", "gtk")
SUPPORTED = {
    "linux": tuple(app for app in APPS if app != "windows-terminal"),
    "windows": tuple(app for app in APPS if app not in ("kitty", "gtk")),
}
REPOSITORY = Path(__file__).absolute().parent.parent


class InstallError(Exception):
    """A change cannot safely be completed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def absolute_path(value: str | Path) -> Path:
    if ".." in str(value).replace("\\", "/").split("/"):
        raise InstallError(f"Parent traversal is not allowed: {value}")
    return Path(value).absolute()


def assert_safe(path: Path) -> None:
    """Reject symlinks, Windows junctions/reparse points, and non-directory parents."""
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise InstallError(f"Refusing a symlink or reparse point: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise InstallError(f"Expected a directory: {part}")


def read_file(path: Path) -> bytes | None:
    assert_safe(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise InstallError(f"Expected an ordinary file with one link: {path}")
    return path.read_bytes()


def make_directories(path: Path, created: list[Path]) -> None:
    assert_safe(path)
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        created.append(directory)
        assert_safe(directory)


def atomic_write(path: Path, content: bytes, mode: int = 0o644) -> None:
    """Replace only a regular file, using a flushed temporary sibling."""
    read_file(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".cygma-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, mode)
        assert_safe(path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class Layout:
    platform: str
    home: Path
    config: Path
    data: Path
    local: Path
    roaming: Path
    state: Path
    nvim: Path
    kitty: Path

    @classmethod
    def create(cls, target_root: str | Path | None = None, platform: str | None = None) -> "Layout":
        if platform is not None and target_root is None:
            raise InstallError("--platform requires --target-root; real installs use the current OS")
        platform = platform or ("windows" if os.name == "nt" else "linux" if sys.platform.startswith("linux") else "unsupported")
        if platform not in SUPPORTED:
            raise InstallError("The installer supports Linux and Windows only")
        if target_root is not None:
            root = absolute_path(target_root)
            assert_safe(root)
            home = root / "home"
            local, roaming = home / "AppData/Local", home / "AppData/Roaming"
            config = local if platform == "windows" else home / ".config"
            data, state = home / ".local/share", root / ".cygma-state"
            return cls(platform, home, config, data, local, roaming, state, config / "nvim", config / "kitty")
        home = absolute_path(Path.home())

        def environment_path(name: str, fallback: Path) -> Path:
            value = os.environ.get(name)
            result = absolute_path(value) if value else fallback
            if value and not Path(value).is_absolute():
                raise InstallError(f"{name} must be an absolute path")
            return result

        local = environment_path("LOCALAPPDATA", home / "AppData/Local")
        roaming = environment_path("APPDATA", home / "AppData/Roaming")
        config = environment_path("XDG_CONFIG_HOME", local if platform == "windows" else home / ".config")
        data = environment_path("XDG_DATA_HOME", home / ".local/share")
        state = local / "Cygma/installer" if platform == "windows" else environment_path("XDG_STATE_HOME", home / ".local/state") / "cygma-themes"
        appname = os.environ.get("NVIM_APPNAME", "nvim")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", appname):
            raise InstallError("NVIM_APPNAME must be a simple directory name")
        kitty = environment_path("KITTY_CONFIG_DIRECTORY", config / "kitty")
        return cls(platform, home, config, data, local, roaming, state, config / appname, kitty)

    def targets(self, app: str, variant: str) -> dict[str, Path]:
        if app not in SUPPORTED[self.platform] or variant not in VARIANTS:
            raise InstallError(f"Unsupported app/variant on {self.platform}: {app}/{variant}")
        if app in ("vscode", "vscodium"):
            base = self.home / (".vscode" if app == "vscode" else ".vscode-oss") / "extensions" / f"cygma-audio.cygma-{variant}"
            return {"package.json": base / "package.json", "theme": base / "themes" / f"cygma-{variant}.json", "LICENSE": base / "LICENSE"}
        if app == "windows-terminal":
            return {"theme": self.local / "Microsoft/Windows Terminal/Fragments/Cygma" / f"cygma-{variant}.json"}
        if app == "kitty":
            return {"theme": self.kitty / "themes" / f"cygma-{variant}.conf"}
        if app == "alacritty":
            base = self.roaming if self.platform == "windows" else self.config
            return {"theme": base / "alacritty/themes" / f"cygma-{variant}.toml"}
        if app == "wezterm":
            base = self.local / "Cygma/wezterm" if self.platform == "windows" else self.config / "wezterm"
            return {"theme": base / "colors" / f"cygma-{variant}.toml"}
        if app == "neovim":
            return {"theme": self.nvim / "colors" / f"cygma_{variant}.lua"}
        return {version: self.data / "themes" / f"cygma-{variant}" / version / "gtk.css" for version in ("gtk-3.0", "gtk-4.0")}


def source_files(repository: Path, app: str, variant: str) -> dict[str, bytes]:
    def required(relative: str) -> bytes:
        path = repository / "ports" / relative
        content = read_file(path)
        if content is None:
            raise InstallError(f"Missing generated theme: {path}; run scripts/build.py first")
        return content

    if app in ("vscode", "vscodium"):
        package = json.loads(required("vscode/package.json"))
        themes = [theme for theme in package["contributes"]["themes"] if theme["path"].replace("./", "") == f"themes/cygma-{variant}.json"]
        if len(themes) != 1:
            raise InstallError(f"Expected exactly one VS Code theme for {variant}")
        package["name"], package["publisher"] = f"cygma-{variant}", "cygma-audio"
        package["displayName"] = f"Cygma {variant.title()}"
        package["contributes"] = {"themes": themes}
        return {"package.json": json_bytes(package), "theme": required(f"vscode/themes/cygma-{variant}.json"), "LICENSE": required("vscode/LICENSE")}
    if app == "windows-terminal":
        fragment = json.loads(required("windows-terminal/cygma.json"))
        schemes = [scheme for scheme in fragment["schemes"] if scheme["name"] == f"Cygma {variant.title()}"]
        if len(schemes) != 1:
            raise InstallError(f"Expected exactly one Windows Terminal scheme for {variant}")
        return {"theme": json_bytes({"schemes": schemes})}
    if app == "gtk":
        return {version: required(f"gtk/cygma-{variant}/{version}/gtk.css") for version in ("gtk-3.0", "gtk-4.0")}
    if app == "neovim":
        return {"theme": required(f"neovim/colors/cygma_{variant}.lua")}
    extension = "conf" if app == "kitty" else "toml"
    return {"theme": required(f"{app}/cygma-{variant}.{extension}")}


def load_manifest(layout: Layout) -> dict:
    raw = read_file(layout.state / "manifest.json")
    if raw is None:
        return {"version": 1, "platform": layout.platform, "files": {}}
    try:
        value = json.loads(raw)
        if value["version"] != 1 or value["platform"] != layout.platform or not isinstance(value["files"], dict):
            raise ValueError("unsupported version/platform")
        for key, entry in value["files"].items():
            expected = {str(path) for path in layout.targets(entry["app"], entry["variant"]).values()}
            if key != entry["target"] or key not in expected:
                raise ValueError("target outside the permitted theme paths")
            if not re.fullmatch(r"[0-9a-f]{64}", entry["installed_hash"]):
                raise ValueError("invalid installed hash")
            prior = entry["original_hash"]
            if prior is not None and not re.fullmatch(r"[0-9a-f]{64}", prior):
                raise ValueError("invalid original hash")
            backup = f"backups/{digest(key.encode())}-{prior}.bin" if prior is not None else None
            if entry["backup"] != backup:
                raise ValueError("invalid backup path")
            if not isinstance(entry["original_mode"], int) or not 0 <= entry["original_mode"] <= 0o777:
                raise ValueError("invalid original mode")
        return value
    except (ValueError, KeyError, TypeError, InstallError) as error:
        raise InstallError(f"Invalid manifest {layout.state / 'manifest.json'}: {error}") from error


@dataclass
class Change:
    path: Path
    before: bytes | None
    after: bytes | None
    mode: int = 0o644
    before_mode: int = 0o644
    recovery_backup: bool = False


def plan(layout: Layout, repository: Path, apps: list[str], variants: list[str], uninstall: bool) -> list[Change]:
    manifest = load_manifest(layout)
    updated = copy.deepcopy(manifest)
    backups: list[Change] = []
    changes: list[Change] = []
    for app in apps:
        for variant in variants:
            targets = layout.targets(app, variant)
            sources = {} if uninstall else source_files(repository, app, variant)
            for name, path in targets.items():
                key = str(path)
                previous = manifest["files"].get(key)
                if uninstall and previous is None:
                    continue
                before = read_file(path)
                mode = stat.S_IMODE(path.stat().st_mode) & 0o777 if before is not None else 0o644
                if previous is not None and (before is None or digest(before) != previous["installed_hash"]):
                    raise InstallError(f"Installed file was changed or removed; preserve your edits before retrying: {path}")
                if previous is not None and previous["backup"]:
                    backup_path = layout.state / previous["backup"]
                    backup_content = read_file(backup_path)
                    if backup_content is None or digest(backup_content) != previous["original_hash"]:
                        raise InstallError(f"Backup is missing or changed: {backup_path}")
                if uninstall:
                    after = backup_content if previous["backup"] else None
                    del updated["files"][key]
                    changes.append(Change(path, before, after, previous["original_mode"], mode))
                    continue
                after = sources[name]
                if previous is None:
                    prior_hash = digest(before) if before is not None else None
                    backup_name = f"backups/{digest(key.encode())}-{prior_hash}.bin" if before is not None else None
                    previous = {"app": app, "variant": variant, "target": key, "original_hash": prior_hash,
                                "original_mode": mode, "backup": backup_name}
                    if backup_name:
                        backup_path = layout.state / backup_name
                        old_backup = read_file(backup_path)
                        if old_backup is not None and old_backup != before:
                            raise InstallError(f"Backup conflict: {backup_path}")
                        if old_backup is None:
                            backups.append(Change(backup_path, None, before, 0o600, recovery_backup=True))
                updated["files"][key] = {**previous, "installed_hash": digest(after)}
                if before != after:
                    changes.append(Change(path, before, after, 0o644, mode))
    if updated != manifest:
        manifest_path = layout.state / "manifest.json"
        changes.append(Change(manifest_path, read_file(manifest_path), json_bytes(updated), 0o600, 0o600))
    return backups + changes


def transact(changes: list[Change], created: list[Path]) -> None:
    attempted: list[Change] = []
    try:
        for change in changes:
            if read_file(change.path) != change.before:
                raise InstallError(f"File changed during installation: {change.path}")
            make_directories(change.path.parent, created)
            attempted.append(change)
            if change.after is None:
                change.path.unlink()
            else:
                atomic_write(change.path, change.after, change.mode)
    except BaseException as error:
        failures = []

        def restore(change: Change) -> None:
            try:
                if change.before is None:
                    assert_safe(change.path)
                    change.path.unlink(missing_ok=True)
                else:
                    atomic_write(change.path, change.before, change.before_mode)
            except (OSError, InstallError) as restore_error:
                failures.append(f"{change.path}: {restore_error}")

        # Recover target files first. A second I/O failure must never destroy the
        # only copy of the user's original bytes in a newly created backup.
        for change in reversed(attempted):
            if not change.recovery_backup:
                restore(change)
        if not failures:
            for change in reversed(attempted):
                if change.recovery_backup:
                    restore(change)
        if failures:
            raise InstallError("Rollback needs manual recovery; retain installer state/backups. " + "; ".join(failures)) from error
        raise


def run(layout: Layout, repository: Path, apps: list[str], variants: list[str], *, dry_run: bool = False, uninstall: bool = False) -> int:
    for app in apps:
        if app != "all" and app not in SUPPORTED[layout.platform]:
            raise InstallError(f"{app} is not supported on {layout.platform}; use its supported OS")
    if "all" in apps:
        apps = list(SUPPORTED[layout.platform])
    apps = list(dict.fromkeys(apps))
    variants = list(VARIANTS) if "all" in variants else list(dict.fromkeys(variants))
    for variant in variants:
        if variant not in VARIANTS:
            raise InstallError(f"Unknown variant: {variant}")

    def describe(changes: list[Change]) -> None:
        for change in changes:
            action = "remove" if change.after is None else "restore" if uninstall and change.path != layout.state / "manifest.json" else "write"
            print(f"{'Would ' if dry_run else ''}{action}: {change.path}")
        if not changes:
            print("No changes needed.")

    # Preflight checks every requested file before creating even the lock directory.
    changes = plan(layout, repository, apps, variants, uninstall)
    if dry_run or not changes:
        describe(changes)
        return len(changes)
    created: list[Path] = []
    lock = layout.state / ".lock"
    locked = False
    try:
        make_directories(layout.state, created)
        assert_safe(lock)
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as error:
            raise InstallError(f"Installer lock exists: {lock}; another install may be running") from error
        locked = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(str(os.getpid()) + "\n")
        changes = plan(layout, repository, apps, variants, uninstall)
        transact(changes, created)
        describe(changes)
        return len(changes)
    finally:
        if locked:
            assert_safe(lock)
            lock.unlink()
        for directory in reversed(created):
            try:
                assert_safe(directory)
                directory.rmdir()  # Only empty directories created by this invocation.
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", action="append", choices=(*APPS, "all"), required=True, help="App to install; repeat for multiple apps")
    parser.add_argument("--variant", action="append", choices=(*VARIANTS, "all"), help="Theme variant; default: all")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing anything")
    parser.add_argument("--uninstall", action="store_true", help="Restore prior files or remove unmodified installed files")
    parser.add_argument("--target-root", type=Path, help="Isolate every destination and installer state beneath this directory")
    parser.add_argument("--platform", choices=tuple(SUPPORTED), help="Simulate OS paths; requires --target-root")
    args = parser.parse_args(argv)
    try:
        layout = Layout.create(args.target_root, args.platform)
        run(layout, REPOSITORY, args.app, args.variant or ["all"], dry_run=args.dry_run, uninstall=args.uninstall)
        return 0
    except (InstallError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cygma installer: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        sys.exit("Cygma requires Python 3.10 or newer")
    sys.exit(main())
