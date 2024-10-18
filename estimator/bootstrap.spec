# -*- mode: python ; coding: utf-8 -*-


from argparse import ArgumentParser

parser = ArgumentParser(description='Make the bundled app.')
parser.add_argument(
    '--debug', action='store_true', default=False,
    help='Make a one directory app for debugging.',
)
options = parser.parse_args()


a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('estimator.toml', '_app_data'),
        ('checkpoint/model.onnx', '_app_data/checkpoint'),
        ('../sketch/assets', '_app_data/sketch/assets'),
        ('../sketch/runtime', '_app_data/sketch/runtime'),
        ('../sketch/styles', '_app_data/sketch/styles'),
        ('../sketch/demo.*', '_app_data/sketch'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if options.debug:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='bootstrap',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='bootstrap',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='bootstrap',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
