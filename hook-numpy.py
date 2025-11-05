# -*- coding: utf-8 -*-

"""
PyInstaller hook for numpy to fix import issues with numpy 2.x
This hook ensures numpy is properly packaged and prevents source directory conflicts
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all numpy submodules
hiddenimports = collect_submodules('numpy')

# Collect numpy data files
datas = collect_data_files('numpy', include_py_files=True)

# Exclude numpy from noarchive to ensure proper packaging
excludes = []
