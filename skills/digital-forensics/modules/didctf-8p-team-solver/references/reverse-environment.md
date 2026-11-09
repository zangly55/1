# reverse-skill 环境验收与调用

> 发行版说明：下文的实测记录属于维护者历史环境；路径已参数化。运行前读取 [环境与安装](../../../references/environment.md)，将占位符解析为当前真实路径并复查依赖，不能把历史成功视为本次已执行。

2026-10-23 配置。方法库为 `{REVERSE_SKILL_ROOT}`，独立运行环境为 `{FORENSIC_RUNTIME}`。已配置可在 Windows 直接运行的常用取证、静态逆向和计算工具；这不代表所有模块的硬件、商业软件、在线服务或 Linux 依赖均已就绪。

权威可用性记录：`{FORENSIC_RUNTIME}\tools.json`，含实际命令、前缀参数、验证方式和限制。版本锁定：`requirements-lock.txt`、`node/package-lock.json`；下载校验信息在 `downloads/*.source.json`。本地包的旧发现器把 npx 存在误当成 MCP 可用，因此 **tools.json 的验证状态优先于 tool-index.json 的 available**。

## 可调用入口

| 工具/环境 | 版本 | 本机入口或调用方式 | 已验证范围 |
|---|---|---|---|
| Python | 3.11.9 | `{FORENSIC_RUNTIME}\python\Scripts\python.exe` | pip check、模块导入及下列计算测试 |
| JDK | 25.0.4.1 | `{FORENSIC_RUNTIME}\tools\jdk\jdk-25.0.4.1+1\bin\java.exe` | Java/JAR 运行 |
| jadx | 1.5.3 | `{FORENSIC_RUNTIME}\bin\jadx.cmd` | CLI 启动和版本 |
| apktool | 3.0.2 | `{FORENSIC_RUNTIME}\bin\apktool.cmd` | CLI 启动和版本 |
| Ghidra | 12.2 | `{FORENSIC_RUNTIME}\bin\analyzeHeadless.cmd` | PE 导入、自动分析、项目保存全部成功 |
| radare2 / rabin2 / rasm2 / radiff2 / rahash2 / rax2 | 6.2.4 | `bin/r2.cmd`；其余在 `tools/radare2/radare2-6.2.4-w64/bin/` | 版本，rabin2 实际解析 PE 信息 |
| ILSpy CLI | 11.1.0.9782 | `{FORENSIC_RUNTIME}\bin\ilspycmd.cmd` | 实际枚举 .NET 程序集类型；独立 .NET 10 runtime |
| Frida / frida-tools | 17.24.3 / 14.10.4 | `{FORENSIC_RUNTIME}\python\Scripts\frida.exe` | 主机 CLI；未接设备，不等于设备 Hook 就绪 |
| bkcrack | 1.8.1 | `tools/bkcrack/bkcrack-1.8.1-win64/bkcrack.exe` | CLI 版本 |
| Volatility 3 | 2.28.2 | `{FORENSIC_RUNTIME}\python\Scripts\vol.exe` | CLI 与模块可运行；每案另需匹配内存镜像和符号 |
| YARA | yara-python 4.5.4 | 独立 Python 中 `import yara` | 编译规则并成功匹配；未安装原生 yara.exe |
| Capstone / Unicorn | 5.0.9 / 2.1.4 | 独立 Python 导入 | 反汇编 NOP、仿真执行 NOP |
| Z3 / PyCryptodome | 见版本锁 | 独立 Python 导入 | 约束求解、AES 往返验证 |
| pefile / LIEF | 见版本锁 | 独立 Python 导入 | 实际 PE 解析 |
| python-evtx、regipy、oletools、dpkt、construct、Pillow、lz4、zstandard | 见版本锁 | 独立 Python 导入 | 模块加载；具体检材功能需按案验证 |
| ADB | 31.0.3 | `{APPANALYSIS_HOME}\bin\adb\adb.exe` | 主机版本，未连接设备 |
| TShark / 7-Zip / SQLite / ExifTool | 4.2.0 / 19.00 / 3.53.1 / 12.34 | 绝对路径见 tools.json | 复用本机已有工具，版本确认 |
| Node.js | 24.18.0 | `{NODE_EXE}` | 运行 JS、MCP 客户端 |
| JS Hook MCP | 0.3.4 | 下述 `mcp-call.py` CLI 桥接 | initialize、tools/list、search_tools 成功；未逐一验收所有扩展工具 |
| Trivy | 0.76.1 | `tools/trivy/trivy.exe` | 本地离线 secret 扫描成功；漏洞数据库状态见下文 |
| Nuclei | 3.11.1 | `tools/nuclei/nuclei.exe` | CLI、官方模板语法验证；未对外部目标扫描 |
| ffuf | 2.3.0 | `tools/ffuf/ffuf.exe` | CLI 版本；未对外部目标扫描 |
| SQLMap | 1.10.10.19#dev | `bin/sqlmap.cmd` | 固定提交 c9745f883d2a5b70de8b786fcd3451e9b991da8a；非交互 CLI |
| PlantUML | 1.2026.9 | `bin/plantuml.cmd` | 实际生成序列图 SVG |

`bin/`、`tools/` 的相对路径以 `{FORENSIC_RUNTIME}` 为根。首次使用某能力仍检查其实际输入格式和工具帮助，版本成功不能替代具体题目的执行成功。

## 每个执行进程的环境

在 PowerShell 中点载 `{FORENSIC_RUNTIME}\activate.ps1`，仅影响当前进程及子进程，不修改用户/系统 PATH。GPT 子代理每次新 shell 都要重新加载，或直接使用 tools.json 的绝对路径。不要把新依赖安装到火眼的 Python 中。

```powershell
. '{FORENSIC_RUNTIME}\activate.ps1'
& '{FORENSIC_RUNTIME}\bin\r2.cmd' -v
& '{FORENSIC_RUNTIME}\python\Scripts\python.exe' -m pip check
```

Ghidra 必须用上表包装入口，它为该进程指定 JDK、独立缓存、设置和临时目录。直接调用原版 analyzeHeadless.bat 曾发生路径和 Felix 缓存初始化错误；修正后真实 PE 分析成功，日志为 `{FORENSIC_RUNTIME}\logs\ghidra-console-final.log`。

部分 Windows 原生程序仍不能正确处理中文输入文件路径。遇到该类工具，在成员独占的 ASCII 暂存目录（如 `{FORENSIC_RUNTIME}\cases\<case-id>\P01\`）复制已经由 GES 导出的样本，记录原始检材 → GES 导出物 → ASCII 副本的映射和副本哈希；结果再交回案件工作区。仅对小导出物校验副本，不触发原始大镜像全量哈希。不得对原镜像更名或迁移。两成员不能共写同一目录。

## JS Hook CLI 桥接

没有更改 Codex 全局 MCP 配置。GPT 主会话及子代理可按实际权限通过同一 CLI 访问已安装的 stdio MCP；仍需确认各执行环境实际可用。

把有界请求写入当前成员目录的 JSON 数组，例如：

```json
[{"method":"tools/call","params":{"name":"search_tools","arguments":{"query":"AST deobfuscate","top_k":3,"auto_activate":false}}}]
```

```powershell
& '{FORENSIC_RUNTIME}\python\Scripts\python.exe' -X utf8 '{FORENSIC_RUNTIME}\mcp-call.py' --requests '<成员目录>\requests.json' --workdir '<成员目录>' --log '<成员目录>\jshook.log' --timeout 60
```

先搜索，再 describe_tool 检查 schema，再用 call_tool 调用具体工具。同一文件可写多条请求，按序在同一会话运行；下一次 CLI 调用是新会话，不保留浏览器/调试状态。请求耗时计入团队期限。工具返回 isError 或协议错误不能标成功。

已验收工具发现与搜索；浏览器、设备、原生附加模块及 LLM 分析工具未逐一验收。实际浏览器操作服从当前客户端已有的浏览器/计算机工具规则，不能用桥接规避。桥接不传递无关 API Key，不启用额外模型编排；本团队仍仅 GPT。

## 模块与尚需条件

安装包的 41 个一级场景技能和嵌套 CTF 方法保留完整，按需加载；以下覆盖其主要依赖边界。不得将“有方法文档”写成“整条流程均已实测”。

| 模块/场景 | 当前可用部分 | 尚需条件或未配置部分 |
|---|---|---|
| digital-forensics、protocol-reverse、email-security、threat-hunting | 火眼导出后用 SQLite/TShark/EVTX/注册表/Office/YARA/Python 分析 | 具体检材、内存符号、按案规则 |
| reverse-engineering、radare2、ghidra-reverse、go-rust-reverse、binary-diff、patch-diff-exploit | Ghidra/radare2 静态分析、差分、反汇编与计算 | 特定架构插件、动态复现环境按案确认 |
| dotnet-reverse | ILSpy CLI | dnSpy 调试、商业混淆插件未配置 |
| apk-reverse、mobile-reverse | jadx/apktool/ADB/Frida 主机端 | 真实设备、匹配版本 frida-server/Gadget、Root/调试权限；iOS 另需对应设备与系统 |
| malware-analysis、edr-bypass-re、thick-client、windows-ad | 静态二进制、规则与日志分析 | 未创建动态恶意样本沙箱、AD 域靶场、内核调试环境 |
| js-reverse、browser-extension-reverse | Node、JS Hook 工具发现接口 | 浏览器会话与各插件能力按需验收，不能宣称全部 600+ 工具可用 |
| browser-automation | 当前客户端既有浏览器工具 | agent-browser/独立 Playwright 浏览器运行时未新增安装 |
| docs-generator、diagram-generator、case-review | 文本/Markdown/Mermaid、PlantUML SVG、Python 审查；团队 P07/P08 规则不变 | 独立 Graphviz CLI 未配置，其他布局须实测 |
| code-audit、supply-chain-security | 本地源码分析、Trivy 离线 secret 检查 | Semgrep/CodeQL 未配置；Trivy 漏洞扫描须有有效漏洞库 |
| pentest-tools、attack-chain、api-security、database-security | SQLMap/Nuclei/ffuf 已装，目标须按案确定；离线材料分析可用 | Nmap 当前发布为 7.992，winget 返回旧 7.80；当前终端无管理员权限，安装器流程未执行。安装包已下载并通过 Nmap Software LLC 数字签名验证，路径 `{FORENSIC_RUNTIME}\downloads\nmap-7.992-setup.exe` |
| cloud-k8s、identity-federation、llm-security | 配置/日志/协议的离线分析 | 云账号、集群、SSO/API/模型凭据及明确目标；未配置在线会话 |
| ida-reverse | 可改选 Ghidra/radare2 静态路线 | IDA Pro/IDA 插件及许可不可用；JEB Pro、商业 Binary Ninja 同样未配置 |
| firmware-pentest、pwn-chain | 基础静态逆向/仿真库 | WSL、pwntools、binwalk、unblob、EMBA、Firmadyne 等按用户要求暂不配置 |
| macos-reverse、hardware-security、ot-ics、wifi-wireless、radio-sdr | 方法、导出数据静态分析 | macOS、UART/JTAG 探针、ICS 设备、支持监听的网卡、SDR 等外部条件 |
| CTF 压缩包、隐写与专项方法 | 7-Zip/bkcrack、ExifTool/Pillow、密码与求解库 | 特定格式与专用工具按题核查；不运行额外 CTF 模型编排 |

附加服务状态：Reqable MCP 1.0.1 仅下载运行时，尚缺 Reqable 桌面连接；其 README 的 --help 在实际二进制失败，不能算 ready。Ghidra MCP、Burp MCP、Anything Analyzer、ProxyCat、SecLists 未配置；Ghidra 使用已验证 headless CLI。PentestSwarm 需要额外模型编排/凭据，不接入本团队。

Nuclei 官方模板 v10.5.0 已安装在 `{FORENSIC_RUNTIME}\tools\nuclei-templates\nuclei-templates-10.5.0`，源版本与压缩包摘要保存在 downloads 中。实际调用显式 `-t` 选择相关模板，不能默认向未授权目标运行全库；测试仅使用 `-validate` 验证一个官方模板，没有进行目标扫描。

PlantUML 已完成 SVG 渲染测试；独立 Graphviz CLI 未安装，需要 dot 的图型应先实测或使用 PlantUML 支持的其他布局。不要把序列图通过视为所有布局均可用。

Trivy 漏洞库尚未下载成功：默认 mirror.gcr.io 连接失败，随后官方 ghcr.io/aquasecurity/trivy-db:2 在五分钟期限后超时。记录分别在 `logs/trivy-db.log`、`logs/trivy-db-ghcr.log`；没有把部分文件标成数据库就绪。当前可用的是已经验证的本地离线 secret 扫描，漏洞扫描须待官方数据库下载成功后另行验证。本轮下载进程均已退出。

## 验收记录

- 本地包路由回归：163/163 通过，日志 `{REVERSE_VALIDATION_DIR}\routing`。
- 本地包冒烟：结构一致性通过、11 个脚本语法检查通过、9/9 个路由通过，日志 `{REVERSE_VALIDATION_DIR}\smoke`。
- Python 功能检查：`{FORENSIC_RUNTIME}\validation\python-checks.json`。
- Ghidra：`logs/ghidra-console-final.log` 中 Analysis/Save/Import succeeded。
- JS Hook：`validation/jshook-protocol.json`、`validation/mcp-search-result.json`；会话已在验证后关闭。
- 安装日志：`logs/pip-tools.log`、`logs/npm-tools.log`；pip check 无冲突。
- 没有运行真实检材题组、没有启动八个 GPT 子代理，不能把环境验收写成实战题解成功。

官方依赖依据：[Ghidra 安装要求](https://github.com/NationalSecurityAgency/ghidra#install)、[Frida 安装说明](https://frida.re/docs/installation/)、[pwntools 支持环境](https://docs.pwntools.com/en/stable/install.html)。
