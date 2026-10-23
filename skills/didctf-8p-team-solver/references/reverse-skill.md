# reverse-skill 本机接入

仓库：`E:\取证工具\reverse-skill`，远端 `https://github.com/zhaoxuya520/reverse-skill.git`。本文件适用于 DeepSeek 首轮和 GPT 接续；仅安装或维护技能时不启动解题团队。

## 与现有取证流程配合

- 本技能负责分题、模型、时限、写入者和答案契约；reverse-skill 提供题型方法、路由和工具脚本。只用 DeepSeek/GPT，不执行下游的额外代理或模型编排；lead/specialist 映射到既有队长和 P01–P06，P07/P08 保持归档职责。
- 火眼仍负责检材访问、解析、检索和导出。对 `ges copy` 得到且在 prep.json 标为 ready 的副本，按需使用 jadx、TShark、SQLite、解压或静态分析工具。原镜像不因引入本仓库而换平台；火眼不支持时先说明实际限制，再按用户已有授权处理。
- 按单题或同源题组路由，Hint 仅写样本类型和任务意图，不加入整套题目、全部工具名或模型角色。手机聊天统计应使用取证流程，不因“Android”就全部反编译；服务器日志题不因“容器”就转为渗透任务。路由不合适时读全矩阵，按证据选择并记录理由。
- 先利用已有导出物和轻量查询；需要时再反编译、协议还原或动态分析。相同样本的昂贵处理只指定一个成员执行，其他人复用已完成产物。记录输入身份、命令、工具版本、退出码、输出位置与证据定位。
- 不将读取模块、命中路由或发现工具写成分析成功。补充工具产物仍由 GPT 核对原始证据后发布；其耗时计入原 45 分钟期限，不另起计时。

## 选择与运行

分题前队长读取仓库 `skills/MASTER-ROUTING.md` 和 `skills/tool-index.json`，把相关模块、工具与数据依赖写进 brief.md。解题手实际处理子任务时打开对应模块；不要预加载整个仓库。所有相对引用以原模块目录解析，保留 CTF sidecar 的完整目录关系。

下例在当前成员目录生成路由结果；`$memberOutput`、`$hint` 必须来自本次真实分工。对 GPT 队长使用其准备目录，GPT 子代理使用自己的 `work/gpt/<player>`。不要在安装目录或 `C:\` 默认生成案件文件。

```powershell
$reverseRoot = 'E:\取证工具\reverse-skill'
& "$reverseRoot\skills\scripts\master-route.ps1" -Hint $hint -ProjectRoot $memberOutput -OutDir "$memberOutput\reverse\route"
```

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
& "$reverseRoot\skills\scripts\case-init.ps1" -ProjectRoot "$memberOutput\reverse" -CaseName $scopeName -Hint $hint -Preset offline-sample -Sample $exportedSample -EvidenceOfAuth '用户提供检材并要求离线解题；范围见当前案件 brief.md'
& "$reverseRoot\skills\scripts\case-guard.ps1" -CaseRoot "$memberOutput\reverse\work\$scopeName"
```

`$scopeName` 用题号/样本稳定标识；样本变化须重新核对 scope。case-guard 非零时不能忽略。动态执行未知程序须使用合适隔离环境；日常版本检测或静态查询无需模拟真实案件授权。

## 本机工具入口

2026-10-23 已实际执行下列版本命令。后续以当前文件及 `--version`/帮助输出核实；目录存在、MCP 注册或 npx 可用均不等于工具可调用。默认发现器不覆盖本机全部工具目录，不能只凭索引的 no 重装。

| 工具 | 已验证入口 | 版本 |
|---|---|---|
| Python | `E:\取证工具\GoldenEyesV4\Python311\python.exe` | 3.11.9 |
| jadx CLI | `E:\取证工具\APPAnalysis\bin\jadx\bin\jre\bin\java.exe -jar E:\取证工具\APPAnalysis\bin\jadx\lib\jadx-cli.jar`（调用时分别引用两个路径） | 1.5.3 |
| Java | `E:\取证工具\APPAnalysis\bin\jadx\bin\jre\bin\java.exe` | 17.0.10 |
| TShark | `E:\取证工具\plugins\Wireshark\tshark.exe` | 4.2.0 |
| 7-Zip | `E:\取证工具\APPAnalysis\bin\7z\7z.exe` | 19.00 |
| SQLite | `E:\取证工具\GoldenEyesV4\pyplugin\chat-server\chat_app\graphs\deepagent_graph\skills\builtin\sqlite-evidence-analysis\bin\windows-x64\sqlite3.exe` | 3.53.1 |
| Node.js | `C:\Program Files\nodejs\node.exe` | 24.18.0 |

优先使用上述绝对路径；jadx 使用已验证的 java -jar CLI，不把 jadx.exe 的无输出当成功。SQLite 分析使用 `-readonly` 并保留关联 WAL/SHM；不能靠打开不完整数据库副本得出数据不存在的结论。

需要调用仓库依赖 PATH 的脚本时，只给该进程设置运行时目录，不永久修改系统 PATH。刷新索引由 GPT 队长单独执行，不让八名成员并发刷新：

```powershell
$env:PATH = 'E:\取证工具\GoldenEyesV4\Python311;E:\取证工具\APPAnalysis\bin\jadx\bin\jre\bin;E:\取证工具\APPAnalysis\bin\jadx\bin;' + $env:PATH
& 'E:\取证工具\reverse-skill\skills\scripts\refresh-tool-index.ps1'
```

补充表中的 TShark/7-Zip/SQLite 不属于上游发现器完整目录，核实后写进本案 prep.json 的 tools 记录，由成员复用。仓库 MCP 仅在当前执行端真实暴露且验证调用后使用；Codex 可见的 MCP 不保证 dsh 可见，dsh 优先使用已验证 CLI。

确实缺少必要工具时，成员在 progress.json 的 preparation_requests 写用途、候选 capability 和替代方案，由 GPT 统一处理；优先已有等价工具。按需检查 `skills/scripts/bootstrap-manifest.json` 和 bootstrap 脚本实际副作用，安装范围服从本次授权。不要自动安装全套工具、启服务或改全局 MCP。无授权的新配置动作才向用户确认，普通已授权分析步骤直接继续。安装等待与失败也不重置首轮期限。

## 交接与归档

prep.json 可增 tools、reverse_routes 记录（文档字段，不是编排器参数）：题号/样本、PRIMARY、scope 路径、执行者、输入导出路径、工具实际命令、版本/检测时间、分析输出与状态。未完成产物不得标 ready；成员自己的结果先写 progress.json，由 GPT 合并。

handoff.json 复用上述记录、失败尝试及尚在运行的任务。P07 写复现步骤，P08 写脱敏方法与适用条件；不要把仓库模板、历史题解或工具自报输出当本题证据。
