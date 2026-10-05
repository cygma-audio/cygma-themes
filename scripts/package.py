#!/usr/bin/env python3
"""Create a deterministic theme archive and a static website; no dependencies."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, str(ROOT/'scripts/build.py'), '--check'], check=True)
    release = ROOT/'releases/cygma-themes-0.1.0.zip'
    release.parent.mkdir(exist_ok=True)
    files = [ROOT/'README.md', ROOT/'LICENSE']
    for folder in ('tokens', 'ports', 'scripts', 'tests', 'docs', 'reports'):
        files += sorted(p for p in (ROOT/folder).rglob('*') if p.is_file()
                        and '__pycache__' not in p.parts and p.suffix != '.pyc')
    # Include the showcase source without recursively including the release.
    files += sorted(p for p in (ROOT/'site').rglob('*') if p.is_file() and p.suffix != '.zip')
    with zipfile.ZipFile(release, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == '.sh' else 0o644) << 16
            archive.writestr(info, path.read_bytes())
    downloads = ROOT/'site/downloads'
    downloads.mkdir(exist_ok=True)
    shutil.copyfile(release, downloads/'cygma-themes.zip')
    shutil.copytree(ROOT/'site', ROOT/'dist', dirs_exist_ok=True)
    print(f'Packaged {len(files)} source/theme files: {release}')
    print(f'Static website: {ROOT / "dist"}')


if __name__ == '__main__':
    main()
