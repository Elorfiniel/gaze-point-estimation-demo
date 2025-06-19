# -*- mode: python ; coding: utf-8 -*-


# Runtime customiization for the bundled app
from argparse import ArgumentParser
from glob import glob
from os.path import dirname, join, relpath
from sysconfig import get_path

parser = ArgumentParser(description='Make the bundled app.')
parser.add_argument(
    '--debug', action='store_true', default=False,
    help='Make a one directory app for debugging.',
)
options = parser.parse_args()
purelib_path = get_path('purelib')

# Copy the data files required by the bundled app
datas = [
    ('estimator.toml', '_app_data'),
    ('checkpoint/model.onnx', '_app_data/checkpoint'),
    ('resources/facenet.onnx', '_app_data/resources'),
]

# Copy binary protobuf file required by MediaPipe
try:
    import mediapipe as mp
    modules = ['face_detection', 'face_landmark', 'iris_landmark']
    for module in modules:
        root = join(purelib_path, 'mediapipe', 'modules', module)
        for file in glob(join(root, '*.binarypb')) + glob(join(root, '*.tflite')):
            datas.append((file, dirname(relpath(file, purelib_path))))
except ImportError:
    pass

a = Analysis(
    ['bundle-annotator.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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
        name='annotator',
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
        name='annotator',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='annotator',
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
