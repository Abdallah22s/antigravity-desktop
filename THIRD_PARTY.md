# Third-party components

Antigravity Desktop 1.2 uses Python and its Tkinter/ttk interface to Tcl/Tk.
Qt, PySide6 and Shiboken6 are not included in the 1.2 runtime distribution.

This desktop edition, interface and distribution are maintained by Abdallah22s:
https://github.com/Abdallah22s/antigravity-desktop

The patching/account core is based on QNIX-Dev's MIT-licensed project:
https://github.com/QNIX-Dev/eligibility-antigravity-patcher
The original copyright notice and the desktop modification notice are in LICENSE.

Python and Tcl/Tk are not modified by this project. Python's license and the
Tcl/Tk notices available in the build Python distribution are included in
`licenses`, along with PyInstaller metadata. Historical LGPLv3/GPLv3 license
texts remain in the source tree for the earlier Qt release. The exact build
environment packages are listed in `BUILD-DEPENDENCIES.txt`; that list may include
optional tools that are explicitly excluded from the application bundle.

Corresponding upstream sources and component notices:

- Python: https://www.python.org/downloads/source/ and https://docs.python.org/3/license.html
- Tcl/Tk: https://www.tcl-lang.org/software/tcltk/ and https://www.tcl-lang.org/software/tcltk/license.html
- PyInstaller (build tooling): https://pyinstaller.org/en/stable/license.html

This application is an independent utility and is not affiliated with or endorsed
by the makers of Antigravity or Google. The app icon is original
project artwork. The project source is licensed under MIT; see `LICENSE`.
