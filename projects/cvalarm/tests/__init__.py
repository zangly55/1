"""测试包：把测试目录加入 sys.path，使 `import helpers` 在两种加载方式下都成立。

支持：
    python -m unittest discover -s tests          # 顶层模块加载
    python -m unittest tests.test_cli             # 包方式加载
    python tests/run_all.py                       # 逐模块运行
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _path in (_HERE, _ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)
