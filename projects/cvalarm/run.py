#!/usr/bin/env python
"""便捷启动器：`python run.py <子命令>` 等价于 `python -m cvalarm <子命令>`。

放在工程根目录，避免用户配置 PYTHONPATH 或安装包即可直接运行。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from cvalarm.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
