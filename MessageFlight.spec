# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['message_flight.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'winsdk',
        'message_flight',
        'message_flight.autostart',
        'message_flight.demo_notifications',
        'message_flight.notification_worker',
        'message_flight.plane_banner',
        'message_flight.flight_widget',
        'message_flight.tray_app',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MessageFlight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
