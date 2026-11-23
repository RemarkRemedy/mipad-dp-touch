"""Serial-scoped requests to the Pad Display macOS companion."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from AppKit import NSRunningApplication
from Foundation import NSDistributedNotificationCenter

ROOT = Path.home() / 'Library/Application Support/Pad Display'
CHANNEL = 'dev.tj.paddisplay.request'
ACTIONS = {'display', 'android', 'brightness-auto', 'brightness-manual', 'fix-microphone',
           'open-panel', 'toggle-audio', 'toggle-wake', 'select'}


def devices():
    adb = shutil.which('adb') or '/opt/homebrew/bin/adb'
    found = set()
    for port in ('5037', '5038'):
        result = subprocess.run([adb, '-P', port, 'devices', '-l'], capture_output=True,
                                text=True, timeout=5)
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) > 2 and fields[1] == 'device' and 'device:yingtian' in fields:
                found.add(fields[0])
    return sorted(found)


def select(serial):
    action(serial, 'select')


def action(serial, name):
    if name not in ACTIONS or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', serial):
        raise ValueError('Invalid Pad Display request.')
    app = Path('/Applications/Pad Display.app')
    if not (app / 'Contents/Resources/pad_target.py').is_file():
        raise RuntimeError('Install the serial-aware Pad Display companion first.')
    if not NSRunningApplication.runningApplicationsWithBundleIdentifier_('dev.tj.paddisplay'):
        subprocess.run(['open', '-gj', '-b', 'dev.tj.paddisplay', '--args', '--background'],
                   check=True, timeout=5)
    token = str(uuid.uuid4())
    inbox = ROOT / 'requests'
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    request = inbox / token
    response = inbox / (token + '.reply')
    tmp = inbox / (token + '.tmp')
    tmp.write_text(json.dumps(dict(serial=serial, action=name)))
    os.replace(tmp, request)
    try:
        end = time.monotonic() + 20
        while time.monotonic() < end:
            NSDistributedNotificationCenter.defaultCenter().postNotificationName_object_userInfo_deliverImmediately_(
                CHANNEL, token, None, True)
            for _ in range(5):
                if response.exists():
                    reply = response.read_text()
                    if reply != 'OK':
                        raise RuntimeError(reply)
                    return
                time.sleep(.1)
        raise RuntimeError('Pad Display is busy or did not accept the request.')
    finally:
        request.unlink(missing_ok=True)
        response.unlink(missing_ok=True)
