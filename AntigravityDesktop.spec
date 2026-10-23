# Build from an isolated Windows x64 environment using build-desktop.ps1.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
datas = [
    (str(root / "assets"), "assets"),
    (str(root / "licenses"), "licenses"),
    (str(root / "LICENSE"), "."),
    (str(root / "THIRD_PARTY.md"), "."),
    (str(root / "USER_GUIDE.txt"), "."),
    (str(root / "installer" / "BUILD-DEPENDENCIES.txt"), "."),
]
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    datas.append((str(python_license), "licenses/python"))
for toolkit in ("tcl8.6", "tk8.6"):
    for filename in ("license.terms", "license.txt"):
        notice = Path(sys.base_prefix) / "tcl" / toolkit / filename
        if notice.is_file():
            datas.append((str(notice), "licenses/" + toolkit))
datas += copy_metadata("pyinstaller")

a = Analysis(
    [str(root / "desktop_launcher.py")],
    pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["rich", "questionary", "prompt_toolkit", "PySide6", "shiboken6", "PyQt6", "PyQt5"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="AntigravityDesktop",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=True,
    icon=str(root / "assets" / "app.ico"),
    version=str(root / "installer" / "version-info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AntigravityDesktop")
