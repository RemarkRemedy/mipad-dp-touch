"""Add serial routing to the existing local Pad Display 0.4.6 source tree."""
import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('workspace', type=Path, help='folder containing pad-display-mac and pad9-*')
parser.add_argument('--check', action='store_true', help='only check the existing sources')
args = parser.parse_args()
workspace = args.workspace.resolve()
here = Path(__file__).resolve().parent
legacy = (workspace / 'pad9-dpin-switch-probe/recover.py').read_text()
match = re.search(r"^SERIAL = '([A-Za-z0-9_-]+)'$", legacy, flags=re.MULTILINE)
if not match:
    parser.error('Expected Pad Display 0.4.6 with its original serial.')
serial = match.group(1)
patch = (here / 'serial-target.patch.in').read_text().replace('@LEGACY_SERIAL@', serial)
with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary) / 'serial-target.patch'
    path.write_text(patch)
    cmd = ['git', 'apply']
    subprocess.run(cmd + ['--check', str(path)], cwd=workspace, check=True)
    if args.check:
        raise SystemExit(0)
    for folder in ('pad9-mic', 'pad9-dpin-audio', 'pad9-brightness', 'pad9-dpin-switch-probe'):
        shutil.copy2(here / 'pad_target.py', workspace / folder)
    data = Path.home() / 'Library/Application Support/Pad Display'
    data.mkdir(parents=True, exist_ok=True)
    selection = data / 'selected-serial'
    if not selection.exists():
        selection.write_text(serial)
    journal = data / 'windows.json'
    dest = data / ('windows-' + serial + '.json')
    if journal.exists() and not dest.exists():
        shutil.copy2(journal, dest)
    subprocess.run(cmd + [str(path)], cwd=workspace, check=True)
subprocess.run(['python3', str(workspace / 'pad-display-mac/local-install.py')], check=True)
for label in ('dev.tj.pad9-mic', 'dev.tj.pad9-speaker'):
    subprocess.run(['launchctl', 'kill', 'SIGTERM', f'gui/{os.getuid()}/{label}'], check=False)
