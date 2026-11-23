#!/usr/bin/env python3
"""Build and install Pad Display with its persistent, app-specific signing identity."""
from pathlib import Path
import hashlib
import os
import secrets
import sys
import subprocess
from datetime import datetime

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / '.config/mipad-dp-touch-local-signing'
KEYCHAIN = Path.home() / 'Library/Keychains/mipad-dp-touch-local-signing.keychain-db'
IDENTITY = 'Mipad DP Touch Local Code Signing'
OPENSSL = '/opt/homebrew/opt/openssl@3/bin/openssl'
def run(*args, **kwargs):
    result = subprocess.run(list(map(str, args)), **kwargs)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed with exit code {result.returncode}')
    return result


def capture(*args):
    return subprocess.check_output(list(map(str, args)), text=True)


def signing_identity():
    CONFIG.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG, 0o700)
    password = CONFIG / 'keychain-password'
    cert = CONFIG / 'certificate.pem'
    if not password.exists():
        password.write_text(secrets.token_urlsafe(32))
        os.chmod(password, 0o600)
    if not KEYCHAIN.exists():
        run('security', 'create-keychain', '-p', password.read_text(), KEYCHAIN)
        run('security', 'set-keychain-settings', '-lut', '21600', KEYCHAIN)
    run('security', 'unlock-keychain', '-p', password.read_text(), KEYCHAIN)
    if not cert.exists():
        temp = CONFIG
        run(OPENSSL, 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '36500',
            '-subj', '/CN=' + IDENTITY, '-addext', 'keyUsage=critical,digitalSignature',
            '-addext', 'extendedKeyUsage=critical,codeSigning',
            '-keyout', temp / 'key.pem', '-out', cert, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(OPENSSL, 'pkcs12', '-export', '-inkey', temp / 'key.pem', '-in', cert,
            '-out', temp / 'identity.p12', '-passout', 'file:' + str(password), '-name', IDENTITY,
            '-keypbe', 'PBE-SHA1-3DES', '-certpbe', 'PBE-SHA1-3DES', '-macalg', 'sha1')
        os.chmod(temp / 'key.pem', 0o600)
        os.chmod(temp / 'identity.p12', 0o600)
        run('security', 'import', temp / 'identity.p12', '-k', KEYCHAIN, '-P', password.read_text(),
            '-T', '/usr/bin/codesign', '-T', '/usr/bin/security')
        (temp / 'key.pem').unlink()
    der = subprocess.check_output([OPENSSL, 'x509', '-in', str(cert), '-outform', 'DER'])
    fingerprint = hashlib.sha1(der).hexdigest().upper()
    run('security', 'set-key-partition-list', '-S', 'apple-tool:,apple:,codesign:', '-s',
        '-k', password.read_text(), KEYCHAIN, stdout=subprocess.DEVNULL)
    current = capture('security', 'list-keychains', '-d', 'user')
    keychains = [line.strip().strip('"') for line in current.splitlines() if line.strip()]
    if str(KEYCHAIN) not in keychains:
        run('security', 'list-keychains', '-d', 'user', '-s', *keychains, KEYCHAIN)
    return fingerprint



def sign_app(app):
    fingerprint = signing_identity()
    sign = ['codesign', '--force', '--sign', fingerprint, '--keychain', KEYCHAIN, '--timestamp=none']
    executable = app / 'Contents/MacOS/MipadDPTouch'
    for path in sorted(app.rglob('*'), key=lambda p: -len(p.parts)):
        if path.is_symlink() or path == executable:
            continue
        if path.is_file():
            with path.open('rb') as stream:
                magic = stream.read(4).hex()
            if magic in {'cffaedfe','feedfacf','cafebabe','cafebabf','cefaedfe','feedface'}:
                run(*sign, path)
        elif path.suffix in {'.framework', '.app', '.xpc', '.bundle'}:
            run(*sign, path)
    run(*sign, app)
    run('codesign', '--verify', '--deep', '--strict', app)


if __name__ == '__main__':
    sign_app(Path(sys.argv[1]))
