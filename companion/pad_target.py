"""Pin a tablet operation to the selected USB serial, including child helpers."""
import os
from pathlib import Path
import re

FILE = Path.home() / 'Library/Application Support/Pad Display/selected-serial'


def selected():
    serial = os.environ.get('PAD_DISPLAY_SERIAL')
    if serial is None:
        serial = FILE.read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', serial):
        raise ValueError('Select a Pad 9 USB serial in Mipad DP Touch.')
    return serial
