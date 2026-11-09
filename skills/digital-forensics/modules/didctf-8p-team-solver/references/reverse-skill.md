# reverse-skill 本机接入

> 发行版说明：下文的实测记录属于维护者历史环境；路径已参数化。运行前读取 [环境与安装](../../../references/environment.md)，将占位符解析为当前真实路径并复查依赖，不能把历史成功视为本次已执行。

配置状态：Windows 常用取证与逆向环境已验证并接入；详细工具、适用边界和未配置依赖见 [reverse-environment.md](reverse-environment.md)。先读取 `{FORENSIC_RUNTIME}\tools.json`，只使用其 ready 能力。WSL/Linux 工具按用户要求暂不配置；商业软件、硬件、在线服务不因安装方法包而自动就绪。

当前方法库：`{REVERSE_SKILL_ROOT}`，复制自用户提供的 `{REVERSE_SKILL_SOURCE}`，2026-10-23 接入。目录名 1.0.1 与内部 VERSION=1.1.0 不一致，保留原文件，不据此宣称升级。它不是 Git checkout。

原 Git 版 `{REVERSE_COMPAT_ROOT}` 保留，其远端为 `https://github.com/zhaoxuya520/reverse-skill.git`，接入时提交 `cab634bd855fc287f6e420c1f36fd1a6b9245960`。本地包的 case-init 缺少 `-Preset`/`-Sample` 且将 offline 的 ready_for_act 设为 false，因此离线 scope 创建及门禁仍使用原 Git 版的已验证脚本；题型路由、方法模块和工具索引使用当前本地包。不要将未就绪的 scope 强行标 ready。本文件适用于 GPT 子代理首轮和 GPT 接续；仅安装或维护技能时不启动解题团队。

## 与现有取证流程配合

- 本技能负责分题、模型、时限、写入者和答案契约；reverse-skill 提供题型方法、路由和工具脚本。只用 GPT，不执行下游的额外代理或模型编排；lead/specialist 映射到既有队长和 P01–P06，P07/P08 保持归档职责。
- 火眼仍负责检材访问、解析、检索和导出。对 `ges copy` 得到且在 prep.json 标为 ready 的副本，按需使用 jadx、TShark、SQLite、解压或静态分析工具。原镜像不因引入本仓库而换平台；火眼不支持时先说明实际限制，再按用户已有授权处理。
- 按单题或同源题组路由，Hint 仅写样本类型和任务意图，不加入整套题目、全部工具名或模型角色。手机聊天统计应使用取证流程，不因“Android”就全部反编译；服务器日志题不因“容器”就转为渗透任务。路由不合适时读全矩阵，按证据选择并记录理由。
- 先利用已有导出物和轻量查询；需要时再反编译、协议还原或动态分析。相同样本的昂贵处理只指定一个成员执行，其他人复用已完成产物。记录输入身份、命令、工具版本、退出码、输出位置与证据定位。
- 不将读取模块、命中路由或发现工具写成分析成功。补充工具产物仍由 GPT 核对原始证据后发布；其耗时计入原 45 分钟期限，不另起计时。

## 选择与运行

分题前队长读取仓库 `skills/MASTER-ROUTING.md`、`{FORENSIC_RUNTIME}\tools.json` 和本案需要的环境说明，把相关模块、工具与数据依赖写进 brief.md。上游 `skills/tool-index.json` 仅作发现参考，旧版会把 npx 当作 MCP 就绪，不能单独据此判定可用。解题手实际处理子任务时打开对应模块；不要预加载整个仓库。所有相对引用以原模块目录解析，保留 CTF sidecar 的完整目录关系。

下例在当前成员目录生成路由结果；`$memberOutput`、`$hint` 必须来自本次真实分工。对 GPT 队长使用其准备目录，GPT 子代理使用自己的 `work/gpt/<player>`。不要在安装目录或 `C:\` 默认生成案件文件。

```powershell
$reverseRoot = '{REVERSE_SKILL_ROOT}'
$reversePsHost = '{PWSH_EXE}'
& $reversePsHost -NoProfile -ExecutionPolicy Bypass -File "$reverseRoot\skills\scripts\master-route.ps1" -Hint $hint -ProjectRoot $memberOutput -OutDir "$memberOutput\reverse\route"
```

下载包带有 Windows 来源标记，直接 `& script.ps1` 可能因未签名而被拒绝；上述参数仅用于这次子进程，不修改系统执行策略。后续片段复用 `$reversePsHost`，执行前确认该运行时路径仍存在。

读取输出的 `primary_skill` 对应 SKILL.md；歧义时参考 `skills/routing.md`。已由队长路由且目标未变时直接复用记录。常见入口如下，实际选择以当前目标和仓库配置为准：

| 目标 | 仓库内参考 |
|---|---|
| 磁盘、内存、浏览器/系统伪影、时间线 | `skills/digital-forensics/SKILL.md` |
| APK、smali、应用算法 | `skills/apk-reverse/SKILL.md` |
| PCAP、协议字段、通信重建 | `skills/protocol-reverse/SKILL.md` |
| EXE/ELF/so 的静态分析 | `skills/reverse-engineering/SKILL.md`；按可用工具转 IDA/Ghidra/radare2 模块 |
| .NET / C# | `skills/dotnet-reverse/SKILL.md` |
| JS 签名或前端算法 | `skills/js-reverse/SKILL.md` |
| 恶意程序配置与行为 | `skills/malware-analysis/SKILL.md` |
| ZIP、媒体隐写、专项 CTF | `skills/ctf-sandbox/SKILL.md` → `CTF-Sandbox-Orchestrator/ctf-sandbox-orchestrator/SKILL.md` → 对应 `competition-*/SKILL.md`，仅取方法，不启动额外编排 |

使用仓库 ACT 工作流前，为用户要求分析的实际导出样本建立 scope；沿用当前任务授权，记录来源，不将授权扩展至检材中出现的公网地址。模块提示的报告、journal 输出服从本技能单写入者规则：成员只写自己目录，P07/P08 消费 verified.json，正式知识库仍是用户既定路径，不并发回写共享仓库。

```powershell
$reverseOpsRoot = '{REVERSE_COMPAT_ROOT}'
& $reversePsHost -NoProfile -ExecutionPolicy Bypass -File "$reverseOpsRoot\skills\scripts\case-init.ps1" -ProjectRoot "$memberOutput\reverse" -CaseName $scopeName -Hint $hint -Preset offline-sample -Sample $exportedSample -EvidenceOfAuth '用户提供检材并要求离线解题；范围见当前案件 brief.md'
& $reversePsHost -NoProfile -ExecutionPolicy Bypass -File "$reverseOpsRoot\skills\scripts\case-guard.ps1" -CaseRoot "$memberOutput\reverse\work\$scopeName"
```

`$scopeName` 用题号/样本稳定标识；样本变化须重新核对 scope。case-init 内部路由仅作范围记录，实际 PRIMARY 以本地包 master-route 输出为准。case-guard 非零时不能忽略。动态执行未知程序须使用合适隔离环境；日常版本检测或静态查询无需模拟真实案件授权。

## 已验收工具的调用路由

本表是实际选工具的入口，适用于 GPT 子代理首轮和 GPT 接续。先依据题目选择最小所需工具集，再从 `{FORENSIC_RUNTIME}\tools.json` 读取对应 `name` 的 `command`、`prefix_args`、`status`、`validation` 和 `limitation`。ready 表示已记录的本机检查通过，不代表设备、符号、在线数据库或每项功能均已验证。已有可靠 GES 记录足以回答时无需额外运行工具；确需补充分析且输入、范围和依赖已满足时，直接调用选定工具取得证据，不停留在列工具或建议用户操作。

| 题目或导出物 | 优先调用的已验收工具/库 | 调用条件与结果 |
|---|---|---|
| 聊天库、浏览器库、结构化统计 | `sqlite3`、`python` | SQLite 只读，保留 WAL/SHM；输出实际查询、统计口径和记录定位。 |
| APK/DEX、资源、smali、应用算法 | `jadx`、`apktool` | 分别用于 Java 代码阅读、资源/smali 解码；只为涉及代码或资源的题反编译。Java 由包装入口提供。 |
| EXE/ELF/so、二进制配置 | `rabin2` → 按需 `analyzeHeadless` 或 `r2`；Python 的 `pefile`、`lief`、`capstone`、`unicorn` | 先查格式、导入和字符串，再分析相关函数；Ghidra 必须走包装入口。Unicorn 仅在已明确架构和边界的局部模拟中使用。 |
| 指令、二进制差异、数值转换 | `rasm2`、`radiff2`、`rax2`；`rahash2` | 只处理所需片段/副本；原始检材全量哈希仍遵守专用 GES 技能的启用条件。 |
| .NET 程序 | `ilspycmd` | 从类型/方法定位到反编译结果，保存程序集和方法身份。 |
| PCAP、协议、会话时间线 | `tshark`、Python 的 `dpkt`、`construct` | 保留过滤条件、帧号、流号和时间基准，必要时重建协议。 |
| ZIP/压缩包、已知明文题 | `7zip`；条件满足时 `bkcrack`；Python 的 `lz4`、`zstandard` | 先列目录再提取到成员目录；bkcrack 仅用于适用的 ZipCrypto 且具备所需已知明文的题。 |
| 内存镜像 | `volatility3` | 先确认镜像类型与所需符号；本机帮助/导入检查通过不代表本案符号已齐全。 |
| EVTX、注册表、Office 文档 | Python 的 `python-evtx`、`regipy`、`oletools` | 使用独立 Python，按实际格式解析并保留事件/键/宏定位；不执行导出的宏。 |
| 图片、媒体元数据、隐写线索 | `exiftool`、Python 的 `pillow` | 先检查元数据和图像结构，再按题意提取；保留原导出副本。 |
| 密码算法、约束求解 | Python 的 `pycryptodome`、`z3-solver` | 从样本证据确定参数和约束，保存可复现计算及验证结果。 |
| JS 算法、混淆代码 | `node`、`jshookmcp` | 优先静态分析；桥接先发现/描述能力，按环境说明调用。桥接协议可用不代表浏览器、原生调试或外部服务已配置；未知 JS 不直接在宿主执行。 |
| 本地规则匹配、配置中的秘密线索 | Python 的 `yara-python`；`trivy` | YARA 使用 Python API；Trivy 仅启用已验收的离线 secret 扫描，漏洞数据库未就绪，不声称漏洞扫描可用。 |
| 已授权靶场的 Web 专项题 | `sqlmap`、`nuclei`、`ffuf` | 先核对用户授权的具体目标与范围；目前主要完成版本/模板检查，实际扫描按题按需验证。不能把检材里的域名自动当扫描目标。 |
| 设备连接、应用动态分析 | `adb`、`frida` | 仅主机端工具已检查；实际设备、权限、匹配版本的 server/Gadget 就绪后再用，缺条件转准备请求。 |
| 已复核解题过程图 | `plantuml` | P07 按需生成 WP 图示；仅使用已复核事实，不能以画图替代证据。 |

Python 列中使用的是发行包名，导入名以环境说明和实际包 API 为准（例如 `yara-python` 导入 `yara`，`pycryptodome` 导入 `Crypto`）。全部使用独立环境的 `python\Scripts\python.exe`，不要向火眼 Python 安装依赖。

队长在 brief.md 为有关题目记录所选工具、用途和唯一执行者；在 prep.json 的 `tools` / `reverse_routes` 保存工具命令与限制、输入导出路径、输出路径及任务状态。成员先复用这些记录，自己的实际调用和结果写 progress.json，由 GPT 合并，不能并发写 prep.json。工具可用与分析产物完成分开记录；只有实际成功并核对输出后，产物才能标 ready。

每个新 shell 使用绝对命令路径，或先 dot-source `{FORENSIC_RUNTIME}\activate.ps1`；不要假定上一个 shell 的 PATH 会保留。`prefix_args` 按参数列表传递，不能遗漏 `jshookmcp` 的桥接脚本。遇中文路径兼容问题，仅将导出副本复制到成员独占的 ASCII 暂存目录，记录映射，方法见环境说明。

## 本机工具入口

2026-10-23 已补齐独立 Windows 环境。完整工具表和验证记录见 [reverse-environment.md](reverse-environment.md)，不再用火眼自带 Python 安装这些依赖。目录存在、MCP 注册或 npx 可用均不等于工具可调用。

| 工具 | 已验证入口 | 版本 |
|---|---|---|
| Python | `{FORENSIC_RUNTIME}\python\Scripts\python.exe` | 3.11.9，已装取证库 |
| jadx CLI | `{FORENSIC_RUNTIME}\bin\jadx.cmd` | 1.5.3 |
| Java | `{FORENSIC_RUNTIME}\tools\jdk\jdk-25.0.4.1+1\bin\java.exe` | 25.0.4.1 |
| Ghidra / apktool / ILSpy / radare2 | `{FORENSIC_RUNTIME}\bin\` 下对应包装入口，详见 tools.json | 已验收 |
| TShark | `{WIRESHARK_HOME}\tshark.exe` | 4.2.0 |
| 7-Zip | `{APPANALYSIS_HOME}\bin\7z\7z.exe` | 19.00 |
| SQLite | `{GOLDENEYES_HOME}\pyplugin\chat-server\chat_app\graphs\deepagent_graph\skills\builtin\sqlite-evidence-analysis\bin\windows-x64\sqlite3.exe` | 3.53.1 |
| Node.js | `{NODE_EXE}` | 24.18.0 |

优先使用 tools.json 的绝对路径；jadx/Ghidra 使用已验证包装入口。原生工具的中文路径兼容处理见环境说明。SQLite 分析使用 `-readonly` 并保留关联 WAL/SHM；不能靠打开不完整数据库副本得出数据不存在的结论。

需要调用仓库依赖 PATH 的脚本时，只给该进程设置运行时目录，不永久修改系统 PATH。刷新索引由 GPT 队长单独执行，不让八名成员并发刷新：

```powershell
. '{FORENSIC_RUNTIME}\activate.ps1'
& $reversePsHost -NoProfile -ExecutionPolicy Bypass -File '{REVERSE_SKILL_ROOT}\skills\scripts\refresh-tool-index.ps1'
```

tools.json 补充了上游发现器未收录的工具、Python 库和真实可用性，核实后写进本案 prep.json 的 tools 记录，由成员复用。JS Hook 可通过 `{FORENSIC_RUNTIME}\mcp-call.py` 供 GPT 主会话及子代理 共用，参数和会话边界见环境说明；Reqable 仍未就绪。主会话可见的 MCP 不保证每个子代理均可见，按实际工具清单确认。

确实缺少必要工具时，成员在 progress.json 的 preparation_requests 写用途、候选 capability 和替代方案，由 GPT 统一处理；优先已有等价工具。按需检查 `skills/scripts/bootstrap-manifest.json` 和 bootstrap 脚本实际副作用，安装范围服从本次授权。不要自动安装全套工具、启服务或改全局 MCP。无授权的新配置动作才向用户确认，普通已授权分析步骤直接继续。安装等待与失败也不重置首轮期限。

## 交接与归档

prep.json 可增 tools、reverse_routes 记录（文档字段，不是工具调用参数）：题号/样本、PRIMARY、scope 路径、执行者、输入导出路径、工具实际命令、版本/检测时间、分析输出与状态。未完成产物不得标 ready；成员自己的结果先写 progress.json，由 GPT 合并。

handoff.json 复用上述记录、失败尝试及尚在运行的任务。P07 写复现步骤，P08 写脱敏方法与适用条件；不要把仓库模板、历史题解或工具自报输出当本题证据。
