from pathlib import Path


def set_launch_at_login(enabled: bool) -> None:
    app_path = _get_app_bundle_path()
    if app_path is None:
        raise RuntimeError("Launch at login requires running as a .app bundle")
    label = "com.encore.loginitem"
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_path = plist_dir / f"{label}.plist"
    if enabled:
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
""")
    elif plist_path.exists():
        plist_path.unlink()


def _get_app_bundle_path() -> str | None:
    import sys

    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.suffix == ".app":
            return str(parent)
    return None
