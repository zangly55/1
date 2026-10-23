# 火眼 GES 分析 Windows 镜像的通用流程

- 条目 ID：KB-TOPIC-GES-WINDOWS-001
- 适用条件：已由队长在火眼单机版/平台版打开目标案件并完成所需解析；成员只做只读查询与自有目录导出。
- 来源：`E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\SKILL.md`、`E:\取证工具\GoldenEyesV4\skills\ges-case-management\SKILL.md`（本机实测 CLI 文档）；案件适用性以 `work/prep/verified.json` 已确认条目为准。

## 标准步骤

1. 绑定与自检：只使用 `work/prep/prep.json` 中 `connection_status=ready` 且案件号与简报一致的最新真实 `cid`/`ges_url`。

```powershell
ges.exe status --json
ges.exe --cid <cid> --ges-url <ges_url> case ls --json
ges.exe evidence ls --json
```

2. 先发现虚拟路径，再访问，不猜路径。

```powershell
ges.exe ls /case/ --json
ges.exe ls /evidence_mounts/ --json
ges.exe glob -p "**/*.db" --path /evidence_mounts/ --json
```

3. 有界检索：`/case/` 可用 keyword；`/evidence_mounts/` 只支持显式 regex，且必须先 `ls/glob` 缩小范围。

```powershell
ges.exe grep "关键词" --path /case/ --json
ges.exe grep "1[3-9][0-9]{9}" --syntax regex --path "/evidence_mounts/eid-<eid>/有界目录" --glob "*.txt" --json
```

4. 本地计算前先导出到本人 `output/exports/`（数据库会连同 `-wal`/`-shm` 一起复制；大目录用 `--async` 并记录 `job_id`）。

```powershell
ges.exe copy "/evidence_mounts/eid-<eid>/路径/app.db" --dest "<成员output>\exports"
ges.exe copy "/evidence_mounts/eid-<eid>/路径/目录/" --recursive --glob "**/*.txt" --dest "<成员output>\exports" --async --manifest "<成员output>\exports\copy.jsonl"
ges.exe job status <job-id> --json
```

5. 引用 `/case/` 记录时，先 `ges read` 取文件顶部真实 `Goldeneyes://<case_number>/<node_id>` 基址，再加正文行号；不得照搬示例、不得用 `cid` 拼接。

```powershell
ges.exe read "/case/.../data.csv" --offset 0 --limit 100
```

## 易错点

- `/case/` 是解析记录，`/evidence_mounts/` 是原始挂载文件系统；两者路径不能互换，后者没有溯源句柄。
- keyword 零命中只有在 `index_state=current` 且 `index_coverage=covered` 时才能作为否定结论；否则按 `coverage_hint` 建索引或改用有界 regex 复核。
- `glob` 的 JSON 集合键是 `matches`（不是 `files`）；`ls` 是 `entries`。只有 `next_offset=null` 且 `source_complete=true` 才表示结果完整。
- 目录复制必须 `--recursive`；默认文件数/总大小上限为 200 个、256 MiB，超出要显式提高并分批。
- 中文、空格、括号路径必须整体加引号；含 `|` 等元字符的 pattern 用 `--pattern-file`。
- `ges copy` 导出物是本地副本，不能再标 `Goldeneyes://` 溯源链接。
- 不要重复执行队长已登记的打开、init、导入、索引与解析任务；准备请求写入自己的 `progress.json`。
