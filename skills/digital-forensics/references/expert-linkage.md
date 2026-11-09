# 专家联动与依赖

只读当前分支所需条目。专家原始说明是专项流程资料，不能替代用户当前任务，也不代表已授权快捷提示中的所有操作。本文承接 digital-forensics 的路由，保留原包的证据、工具及交付约束。

## 公共加载规则

1. 先确认操作与交付物，再读相应 EXPERT.md。仅写报告时可直接读下列报告子技能，满足其输入前提后整理，不为了写报告启动完整分析。
2. 专家里的 skills/from 声明是依赖信息，不是已连接能力证明。依赖按运行时清单、已知本地指南和实际接口核实；只检查本任务所需项。配置禁用的本地原模块仍可由本入口按路径读取。
3. 缺产品技能或工具时，停止依赖它的步骤并说明缺口。若用户目标允许独立本地方法，可依据原有 reverse-skill-router 选择已验证工具，但必须说明采用的方法，不声称执行了缺失的产品流程；不得违背原包对特定回退的条件。网钜离线回退仍遵守资金专家的条件。
4. 不因引用版本号就自动安装或升级软件，不修改插件缓存或关闭其工具连接。已有软件、工具索引和接口状态可能变化，实际执行时重新核实关键条件。
5. 专家预设欢迎语和快捷提示只作示例。正文的按需规则与用户范围优先：服务器镜像不必一律仿真，EXE 静态查询不必一律动态运行，报告复核不自动改稿，笔录核对不自动导出。

## 火眼：复用现有 GES

- 专家：[EXPERT.md](../modules/goldeneyes-forensics/EXPERT.md)。原包要求 GoldenEyes 4.43.0 及以上。
- 案件管理、查询分析、批处理、原始检材哈希分别使用主入口已列出的四个本地 GES 模块，不复制命令规则或重新启用独立入口。
- 报告：[goldeneyes-forensics-report](../modules/goldeneyes-forensics/skills/goldeneyes-forensics-report/SKILL.md)。要求已复核且有真实溯源角标的材料，保留真人审签前草稿性质。
- 单项查询不额外加载专家全流程；原始检材哈希只按主入口显式条件触发。真实 Goldeneyes:// 引用只能来自规定的 read 输出，不能由交接路径拼接。

## EXE：静态定位与动态验证

- 专家：[EXPERT.md](../modules/exe-reversing/EXPERT.md)。
- 静态：[re-ida-static-analysis](../modules/exe-reversing/skills/re-ida-static-analysis/SKILL.md)。依赖真实可用的 IDA Pro MCP。
- 动态：[re-x64dbg-dynamic-debug](../modules/exe-reversing/skills/re-x64dbg-dynamic-debug/SKILL.md)。依赖真实可用的 x64dbg MCP，先核对状态与目标。
- 交接：[联动交接清单](../modules/exe-reversing/references/联动交接清单模板.md)。工具索引：[x64dbg 工具索引](../modules/exe-reversing/references/x64dbg工具索引.md)。报告：[报告模板](../modules/exe-reversing/references/报告模板.md)。
- 同一目标的地址、模块基址、RVA 和符号必须对齐；有验证需求再执行动态分支。现有 reverse-skill-router 可用于工具定位或不同的已验证本地方法，不把工具索引中的历史 ready 当作本次会话已连接。

## APK：问题驱动的证据路径

- 专家：[EXPERT.md](../modules/apk-analysis-expert/EXPERT.md)。原包要求 AppAnalyzer 5.12.0 及以上。
- 产品依赖：thunder-app-static-analysis、thunder-app-source-reverse、thunder-app-unpack、thunder-app-dynamic-monitor、thunder-app-network-capture、thunder-app-frida-validation。
- 依问题选择其中所需技能，不预加载全部依赖。权限声明、源码能力与本次运行行为分开；涉及实际上传等判断时遵守专家的动态/抓包补证条件，受阻时只交付明确降级的结论与缺口。
- 报告：[apk-analysis-report](../modules/apk-analysis-expert/skills/apk-analysis-report/SKILL.md)。默认自包含 HTML，输入须经审查，不自行提高结论强度。
- 转交流量分支时保留 APK 身份、交互时间与抓包对应关系；不重复启动抓包。独立 pcap 分析无需建立 AppAnalyzer 案件。

## 内存：已有检材

- 专家：[EXPERT.md](../modules/memory-forensics/EXPERT.md)。
- 依赖 ForensicDesktop 的 analyzing-memory-dumps-with-volatility，具体解析器、符号和参数以该技能为准；仅有专家文件不能替代该依赖。
- 整机镜像与 LSASS 小型转储分别选格式分支；初筛不附带凭据提取，凭据分析不附带登录验证或口令破解。网络连接需要与进程和时间关联后再交接其他分支。

## 流量：已有抓包

- 专家：[EXPERT.md](../modules/traffic-forensics/EXPERT.md)。
- 依赖 ForensicDesktop 的 analyzing-network-traffic-with-wireshark；Wireshark/tshark 的实际命令以依赖指南为准。
- 对 pcap/pcapng 按问题分析，不启动实时监听；会话和导出文件保留帧号、过滤条件与完整性说明。TLS 解密先核对匹配密钥等条件。

## 服务器：离线、仿真与接入分别判断

- 专家：[EXPERT.md](../modules/server-forensics-expert/EXPERT.md)。
- 镜像转换和仿真分别依赖 GE-BootMagix 的 clonezilla-to-e01、create-vm，仅在需要时加载。已有离线日志任务无需这两项；SSH 接入以用户指定目标和已授权范围为准。
- 报告：[server-forensics-report](../modules/server-forensics-expert/skills/server-forensics-report/SKILL.md)，默认 Markdown 草稿，只整理已核查证据。
- 仿真改变的运行状态属于派生观察，不冒充原始系统状态；与内存/流量联动前对齐主机、采集时间与时区。

## 资金：网钜专项

- 专家：[EXPERT.md](../modules/wmx-bill-analysis-expert/EXPERT.md)。依赖 WebMatrix 5.1.0 及以上与 wmx-bill-analysis 产品技能。
- 先按实际任务确定账户、时间、金额口径；单项查询不扩大为全套特征检测。保留来源虚拟路径、交易 ID、行号及执行状态。
- 报告：[wmx-bill-analysis-report](../modules/wmx-bill-analysis-expert/skills/wmx-bill-analysis-report/SKILL.md)，默认 Markdown，基于已复核的 WMX 结果。
- 保留原包“源数据原位只读、不复制到工作区”的特殊约束；导出结果写入工作区。与聊天/人员记录联动时分别保留出处，资金路径不直接证明身份或责任。

## 笔录：事实整理与 Word 成文

- 专家：[EXPERT.md](../modules/electronic-data-forensics-record-drafting/EXPERT.md)。
- 草拟：[electronic-data-forensics-record-drafting](../modules/electronic-data-forensics-record-drafting/skills/electronic-data-forensics-record-drafting/SKILL.md)。保留四类笔录的要素、单位模板及事实来源规则。
- Word：[electronic-data-forensics-record-docx](../modules/electronic-data-forensics-record-drafting/skills/electronic-data-forensics-record-docx/SKILL.md)。脚本：[md_to_gongwen_docx.py](../modules/electronic-data-forensics-record-drafting/skills/electronic-data-forensics-record-docx/scripts/md_to_gongwen_docx.py)。
- 生成或导出笔录时执行草拟到 Word 的流程；仅检查或解释现有笔录时只做该操作。用户明确只要聊天预览时遵从；缺失事实保留待确认字段。
- Python 需要 python-docx。优先通过 load_workspace_dependencies 获取可用的文档运行时，以实际 import 检查选用解释器；不要直接使用可能指向 Windows Store 的 python 别名，也不要改全局 Python。
- 源稿只包含应进入文书的内容；工具调用、模型过程和秘密值不得进入源稿。结构检查与页面视觉检查分别报告；未看过全部渲染页面时不得宣称版式已验证。
- 本发行版保留了 Word 脚本的修正：编号/路径下划线及行内代码中的字面值不会被 Markdown 清理误删。生成时仍逐项核对路径、编号、时间和校验值，不以脚本成功退出代替内容检查。

## 跨分支最小交接

交接只需覆盖本次问题：对象/案件与版本、来源位置、真实方法及执行状态、已核实事实、分析推断、冲突、缺口、下一项必要动作和派生产物。沿用原分支要求的证据标识，不人为制造统一等级。

典型路由：APK 实际上传问题由 APK 主导，必要时交给流量分析已有抓包；服务器登录问题由日志主导，必要时关联已有内存或流量；已完成分析后用户要求笔录，则交接实际作业记录，不把风险判断转成取证操作事实。单项查询、解释技能或部署技能本身均不触发这些分析动作。
