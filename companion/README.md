# Pad Display integration for v2.2.5

The Mac menu under **Pad Display → Select Pad** targets one Xiaomi Pad 9 Pro Max by USB debugging serial. It discovers authorized tablets on the local ADB servers at ports 5037 and 5038. A saved selection survives relaunch. The app matches its HID interface by the same serial.

The Pad Display companion handles Android/Mac switching, window recovery, hardware brightness presets, BetterDisplay's slider, audio settings, mic repair and Vector recovery. Existing tablet hooks and the Mac audio bridges are prerequisites. Selecting a tablet does not provision it. With multiple video displays, use Mipad’s cursor reference screen control to choose the Mac display for gestures.

To upgrade an existing Pad Display 0.4.6 workspace, run `python3 companion/upgrade.py /path/to/workspace --check`, then run the same command without `--check`. The companion uses its existing signing identity and installer. Build the host with `bash build_app.sh`, then install with `python3 tools/install_local.py`. This fork uses a separate macOS bundle identifier and an app-specific persistent signing key. Grant the fork Accessibility and Input Monitoring if requested.

The menu reports when the companion accepts a command. The companion panel reports completion and device errors. macOS manages native touch separately from events handled by the host.
