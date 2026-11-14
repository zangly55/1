# 火眼 GES 分析 Windows 镜像的通用流程

- 条目 ID：KB-TOPIC-GES-WINDOWS-001
- 适用条件：已由队长在火眼单机版/平台版打开目标案件并完成所需解析；成员只做只读查询与自有目录导出。
- 来源：`E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\SKILL.md`、`E:\取证工具\GoldenEyesV4\skills\ges-case-management\SKILL.md`（本机实测 CLI 文档）；案件适用性以 `work/prep/verified.json` 已确认条目为准。

## 2026-11-14：导入前连接检查（未收到检材）

- 来源：用户要求先连接已经启动的火眼，收到检材后再自行分类导入；本次由 Codex 实测，本机 `ges-case-management/SKILL.md`、`USAGE.md` 为操作依据。
- 已验证：火眼主程序文件版本为 4.10.0，相关进程正在运行；技能目录中的 `bin/ges.exe` 可以执行。裸命令 `ges status` 因 PATH 未包含启动器而失败，改用已存在启动器的绝对路径后可运行 CLI。
- 连接结果：`ges status` 报“未发现可达的单机版 GES 案件服务”；随后 `ges case ls` 返回 0 项。对已观察到的本地后台监听地址进行只读状态检查，分别得到连接关闭、HTTP 400（响应 `GESERROR:11`）。错误码含义未确认，不据此断言具体原因。
- 界面检查：窗口枚举可见火眼窗口，但读取状态时工具报告窗口已最小化，未取得案件页面内容。
- 边界：**尚未建立有效案件连接，也未确认真实 cid、案件编号或案件 URL**。列表为零仅表示本次 CLI 未列出案件，不能推定磁盘上不存在旧案件。未收到检材，未执行导入、解析、哈希或分析；仅观察到进程和端口不等于案件 API 可用。
- 后续处理：收到用户提供的完整检材路径后，重新执行状态检查与案件列表；按文件内容和容器结构判断类型，完整路径严格比对以避免重复导入。用户已授权分类导入，按届时实际状态建案或绑定明确目标案件；导入异常先查询同路径检材是否已创建，再决定是否重试。
- 公开归档只保留方法、版本及结果；原始检材、账户身份、本地实时端口、截图和凭据均不上传。

### 后续复核：用户创建案件后

- 用户明确指定后续检材导入其新建的“美亚”案件。重新执行 `ges status` 成功，显示该案件、`cid=1`、检材数 0，并报告自动发现案件服务。
- 使用该次 status 返回的 cid 与 URL 显式执行 `case ls`，得到唯一 URL 匹配案件；名称、案件编号和位置已保存本地准备记录。由此确认的是**案件 API 已连通，当前案件为空**。
- 进一步按案件编号执行 `case open` 时，命令返回“60s 内未能完成自动 init”，原因提示当前未添加检材；直接 `init` 也返回同样的空案件错误。期间显式 cid/URL 的 `status` 仍成功。这说明连接成功与初始化命令成功须分别记录，不能把自动 init 报错记成完整初始化成功。
- 下次导入按已核对的目标案件和当时复核的真实 cid/URL 显式指定，先确认完整检材路径未重复。检材尚未提供，未执行任何导入或解析。此前连接失败保留为先前时点记录，不再代表目前 API 可达性。
- 无独立截图佐证；本次核对依据为 CLI 实际返回，未将命令行结果表述为图形界面验证。

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
