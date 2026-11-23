"""Install a signed fork build, keeping its requirement and a recoverable backup."""
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
NAME = 'Mipad DP Touch — Pad Display.app'
BUILT = ROOT / 'dist-pyi' / NAME
INSTALLED = Path('/Applications') / NAME


def run(*args):
    return subprocess.run(args, check=True)


def requirement(bundle):
    run('codesign', '-dv', '--verbose=4', bundle)
    result = subprocess.run(['codesign', '-d', '-r-', bundle], check=True, capture_output=True, text=True)
    return next(line for line in (result.stdout + result.stderr).splitlines() if line.startswith('designated =>'))


def verify(bundle):
    run('codesign', '--verify', '--deep', '--strict', bundle)


verify(BUILT)
req = requirement(BUILT)
cert = Path.home() / '.config/mipad-dp-touch-local-signing/certificate.pem'
fingerprint = subprocess.check_output(['openssl', 'x509', '-in', cert, '-noout', '-fingerprint', '-sha1'], text=True)
expected = fingerprint.split('=')[-1].strip().replace(':', '').lower()
if 'identifier "dev.tj.mipad-dp-touch"' not in req or expected not in req.lower():
    raise SystemExit('Local signing requirement mismatch.')
with tempfile.TemporaryDirectory(dir=INSTALLED.parent, prefix='.mipad-install-') as tmp:
    staged = Path(tmp) / NAME
    run('ditto', BUILT, staged)
    verify(staged)
    if requirement(staged) != req:
        raise SystemExit('Staged signature mismatch.')
    if INSTALLED.exists():
        if requirement(INSTALLED) != req:
            raise SystemExit('Installed signing requirement differs.')
        run('osascript', '-e', 'if application id "dev.tj.mipad-dp-touch" is running then tell application id "dev.tj.mipad-dp-touch" to quit')
        for i in range(50):
            if subprocess.run(['pgrep', '-f', str(INSTALLED / 'Contents/MacOS/MipadDPTouch')], stdout=subprocess.DEVNULL).returncode:
                break
            time.sleep(.2)
        else:
            raise SystemExit('The installed app is still running.')
        backup = ROOT / 'build' / ('mipad-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.app')
        run('ditto', INSTALLED, backup)
        verify(backup)
        if requirement(backup) != req:
            raise SystemExit('Backup signature mismatch.')
        print('Backup', backup)
        os.rename(INSTALLED, Path(tmp) / 'previous.app')
    try:
        os.rename(staged, INSTALLED)
        verify(INSTALLED)
    except BaseException:
        previous = Path(tmp) / 'previous.app'
        if previous.exists():
            if INSTALLED.exists():
                shutil.move(INSTALLED, Path(tmp) / 'failed.app')
            os.rename(previous, INSTALLED)
        raise
print('Installed', INSTALLED, req)
run('open', INSTALLED)
