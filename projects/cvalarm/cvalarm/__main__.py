"""允许 `python -m cvalarm <子命令>`。"""
from .cli import main

raise SystemExit(main())
