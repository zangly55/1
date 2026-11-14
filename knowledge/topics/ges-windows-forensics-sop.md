# 火眼 GES 分析 Windows 镜像的通用流程

- 条目 ID：KB-TOPIC-GES-WINDOWS-001
- 适用条件：已由队长在火眼单机版/平台版打开目标案件并完成所需解析；成员只做只读查询与自有目录导出。
- 来源：`E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\SKILL.md`、`E:\取证工具\GoldenEyesV4\skills\ges-case-management\SKILL.md`（本机实测 CLI 文档）；案件适用性以 `work/prep/verified.json` 已确认条目为准。

## 2026-11-14：导入前连接检查（历史准备记录）

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

### 截图模板预检与交付要求（2026-11-14）

- 来源：用户提供《美亚杯个人赛截图模板（学生组+姓名+手机号）.xlsx》，本次只读检查其 OOXML 结构；原文件未修改，未上传。
- 已核对：模板只有 `Sheet1`；A1 为标题，A2 为序号，B2—E2 为截图1—4，F2 为后续截图提示。A4—A153 为题号1—150，即题号 n 对应第 n+3 行，截图由 B 列起按步骤顺序嵌入。模板当前不含图片。第三行另有本机 IP/MAC 信息截图预留位，本文只记录其布局，没有据此执行采集或公开任何地址。
- 用户最新期限：正式检材和题目齐全后，答案交付上限100分钟，其余交付上限120分钟。未解题和待复核答案在100分钟内持续挖掘；每完成10题先在聊天交付，再同步本地答案文件；共享文档填写已被用户后续取消。
- 用户截图要求：每个重要步骤完成后，先最大化该步骤软件，保留底部任务栏，确保屏幕无无关软件窗口或通知，再保存完整屏幕截图。WP 内将图片放在对应题目的具体关键步骤下，同时把同一实际截图嵌入模板的对应题号行。
- 状态边界：这些是已接受的后续执行要求与模板结构检查，**不是正式检材已分析、截图已拍摄或模板已填完**。真实截图和涉及个人信息的交付文件仅在本地保留；公开归档采用脱敏文字摘要。

### 本轮后续规则修订（2026-11-14，以此为准）

- 用户将截图数量收敛为：**每题只保存一张找到或验证答案的关键操作截图**。截图前最大化相关软件，保留底部任务栏，完整画面不得出现无关软件窗口或通知。同一截图填入模板该题的 B 列位置；此前“每个重要步骤均截图”的约定已被本次修订替代。
- 用户要求 WP 延后：所有其他任务完成后先征求用户同意，收到明确同意才制作 WP，WP 不设时限。当前只保留真实证据定位、操作日志和题目关键截图，不提前生成 WP。授权制作后，图片放在该题对应关键步骤下。
- 答案交付只保留题号与答案；置信度、依据和未解边界单独保留。每完成十题先在聊天交付，再同步本地答案文件；共享表格填写已被用户后续取消。题目尚未下发的准备阶段不虚构题号或答案。
- 对检材内的独立检材，先核对真实格式、来源虚拟路径与父检材，再经 GES 导出完整副本，作为新检材导入并记录父子关系。不得把未完成的解压临时文件或普通应用缓存仅凭扩展名当作独立检材。

### 检材导入后的挂载缓存复核（2026-11-14）

- 后续实际进展：用户已提供检材和完整题目文本，分类导入、解析及原始文件查询均已进行。上文“未收到检材”“未导入”仅描述准备阶段，不再代表当前状态；阶段分析见 [本次个人赛案例](../cases/2026-meiya-individual-evidence-review.md)。
- 本轮观察到解析已完成但普通 `status` 仍显示旧挂载映射；在相同案件绑定下增加全局选项 `--no-daemon` 后，新检材挂载出现且原始文件可读取。命令形式为 `ges.exe --cid <cid> --ges-url <ges_url> --no-daemon status`。这次缺口由守护进程上下文缓存造成，不需要重新导入；其他案件的缺失挂载仍须按其实际状态诊断。
- 用户已取消共享文档填写。答案仍每完成十题先在聊天输出，再同步本地答案文件；聊天使用纯文本代码块保留原题号，避免 Markdown 自动重编号。不要继续填写或恢复此前共享表格。
- 独立抓包从父镜像导出后分别导入，父子关系留在本地清单；导入完成与插件实际支持的分析能力分别记录，基础任务完成不能冒充内存或协议分析已经完成。
- 逐题证据截图只保留一张实际关键查询画面。若使用自制只读查询界面，应明示实际脚本、源文件和返回结果，不冒充火眼界面。真实截图及包含敏感字段的查询输出仅本地留存。

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

### 题目网页文字导出的补充方法（2026-11-14）

- 来源：用户要求提供可在题目网页中自行运行的脚本；作者 Codex。依据 [Microsoft Edge 控制台文档](https://learn.microsoft.com/en-us/microsoft-edge/devtools/console/console-javascript)、[MDN innerText](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/innerText)、[Blob](https://developer.mozilla.org/en-US/docs/Web/API/Blob) 与 [createObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static)。
- 本地交付 JavaScript：读取 `document.body.innerText`；将本次页面文字追加到当前页面内存中的记录数组，完全相同的文字不重复追加；用 Blob 下载带 UTF-8 BOM 的文本，并尝试通过控制台 `copy()` 复制。脚本不请求题库接口、不读取浏览器凭据、不操作答题选项或提交按钮。
- 操作：打开题目页并等待文字加载，在控制台运行；需要分页、切换题目或展开折叠内容时由用户操作后再次运行。内存记录会在页面刷新/重新加载后丢失，但已下载的文件保留。导出包含页面导航等可见文字，尚非整理后的完整题库。
- 已验证：本地 Node.js `--check` 语法检查通过。**尚未在目标比赛页面运行或验证题目数量**。DOM 文字不含图片中文字、未加载分页或不可访问的嵌入页面，必须以题号和总数复核，不能宣称已获取全部题目。
- 原始题目导出文件只在本地保留；公开记录不包含试题正文、账户信息、页面截图、令牌或答案。

