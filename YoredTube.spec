# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files

spec_datas = [('frontend', 'frontend'), ('ffmpeg.exe', '.'), ('ffprobe.exe', '.'), ('qjs.exe', '.')]
try:
    spec_datas += collect_data_files('yt_dlp_ejs')
except Exception:
    pass

a = Analysis(
    ['backend.py'],
    pathex=[],
    binaries=[],
    datas=spec_datas,
    hiddenimports=['yt_dlp_ejs', 'quickjs', 'brotli', 'pycryptodomex'],
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
    name='YoredTube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
