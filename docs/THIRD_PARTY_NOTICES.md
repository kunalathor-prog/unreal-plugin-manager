# Third-party components

This application uses Python, PySide6/Shiboken6, Qt, and the PyInstaller bootloader. Their licenses are separate from the license chosen by the application publisher.

The Windows build collects dependency-provided license files into `_internal/licenses` and records versions in `_internal/components.json`. Python's license is included. The publisher must verify that the collected materials cover the exact redistributed binaries and Qt third-party components before distributing a release.

- Python: Python Software Foundation license and its included third-party notices. https://docs.python.org/3/license.html
- Qt for Python / PySide6 / Shiboken6: upstream open-source or commercial licensing terms, as applicable. https://doc.qt.io/qtforpython-6/licenses.html
- Qt: applicable LGPL/GPL/commercial terms and third-party notices. https://doc.qt.io/qt-6/licensing.html
- PyInstaller: GPL with the bootloader distribution exception. https://pyinstaller.org/en/stable/license.html

This build uses a directory distribution with dynamically loaded Qt libraries. That alone does not establish license compliance. Before sale, the publisher must choose and satisfy the applicable Qt licensing route, provide corresponding source/relinking materials and notices where required, and avoid customer terms that conflict with those rights. See https://www.qt.io/development/open-source-lgpl-obligations.

The application is not affiliated with or endorsed by Epic Games. Unreal Engine and associated marks belong to their respective owners. The Windows icon is an original geometric design generated from `scripts/make_icon.py`. The existing source-tree banner is not included in the Windows package because its distribution rights have not been established.
