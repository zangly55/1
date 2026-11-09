---
name: ges-case-batch-processing
description: 用于同一已选择且解析完成案件内，跨多个检材和动态 GES 路径执行批量发现、复制、关联、聚合、去重与派生结果；不用于切换案件、导入检材或未解析数据。
metadata:
  requires:
    bins: ["ges"]
  cliHelp: "ges --help"
allowed-tools: Bash(ges*)
---

# 弘连火眼案件批处理

只在同一个已经选择、所需检材已经解析完成的案件内批处理。先执行 `ges status --json`，固定本批次的 `cid`、GES URL、检材 `eid` 和动态路由；运行期间不得切换案件或沿用其他案件的路径、复制目录、缓存与结果。

使用 `ges ls`、`ges glob`、`ges grep` 的 JSON 输出分页发现候选，以一条递归 `ges copy` 完成同一来源范围的批量复制，并通过 `ges job status`/`ges job cancel` 管理异步作业。任何非零退出、`source_complete=false`、失败终态或过期结果都不是空结果或完整结果。

查看或引用内容时使用 `ges read <虚拟路径>`，并配合 `--offset`/`--limit` 分页；仅需让本地代码一次顺序处理单个 `/case/` CSV/chat.txt 时，使用 `ges cat "<虚拟路径>"` 管道给本地程序，例如 `ges cat "/case/path/to/data.csv" | python -c 'import sys, pandas as pd; print(pd.read_csv(sys.stdin, dtype=str).shape)'`。

需要重复扫描、随机访问或处理 SQLite 时，先使用 `ges copy <source> --dest <本地目标目录>` 复制，再处理本地副本；目标必须是当前本地文件或代码环境可访问的路径。

关联、聚合、去重及其他派生数据必须保留 `cid`、`eid`、`source_virtual_path`、`source_record_or_line`。最终事实必须回到对应 `/case/` 文件执行 `ges read`，只使用其返回的真实 `Goldeneyes://` 基址和正文行号生成角标。

完整的外部 agent CLI 契约、分页规则、目标锁、manifest 和恢复流程见同目录 `USAGE.md`。
