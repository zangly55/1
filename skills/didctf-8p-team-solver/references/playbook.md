# 火眼 GES CLI 工作手册

## 已核实入口

E:\取证工具\GoldenEyesV4\goldeneyes.exe --help 只显示 server/port/reader 等服务参数。实际案件操作使用配套 CLI：

~~~powershell
$ges = 'E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\bin\ges.exe'
& $ges --help
& $ges status
~~~

Windows 用 ges.exe，避免旧 ges.cmd 对 |、& 等字符二次解析。参数仍须整体引用，复杂搜索式通过 UTF-8 pattern 文件输入。

实际操作按需读取：
- 案件选择、导入：E:\取证工具\GoldenEyesV4\skills\ges-case-management\SKILL.md。
- 检索、导出：E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\SKILL.md。
- 明确要求原始检材哈希：E:\取证工具\GoldenEyesV4\skills\ges-original-evidence-hash\SKILL.md。

它们是产品用法参考；已授权且目标明确的操作无需重复确认。技能编辑或工具预检时，不创建案件、不导入检材、不读取现有案件内容。

## 2026-10-19 本机实测：CLI 可用、列案成功

本次验证在 PowerShell 中执行，工作目录为 `E:\取证工具\GoldenEyesV4`。程序不在 PATH 也可通过完整路径调用，无需另装 CLI。

### 第一步：确认文件与入口

~~~powershell
$ges = 'E:\取证工具\GoldenEyesV4\skills\ges-case-analysis\bin\ges.exe'
Test-Path -LiteralPath $ges
& $ges --help
~~~

此前帮助调用已成功，返回“GES 案件数据命令行工具”，列出 `status`、`case`、`evidence`、`ls`、`read`、`grep`、`copy` 等命令。`goldeneyes.exe --help` 只有服务启动参数，不能替代这个 CLI。

### 第二步：查询当前案件后台

~~~powershell
& $ges status --json
$statusExitCode = $LASTEXITCODE
~~~

本次退出码为 **1**，关键返回：

~~~json
{
  "code": "case_backend_unreachable",
  "operation": "status",
  "message": "未发现可达的单机版 GES 案件服务；请切换到 ges-case-management 选择案件。",
  "candidates": [],
  "discovery": {
    "signals": {"saved_config": "miss", "netstat": "ok", "wmi": "ok"}
  }
}
~~~

这说明 CLI 已运行，但没有发现可达的案件后台；不能当成“火眼未安装”“没有案件”或“检材内容为空”。不要反复重试 status，不靠启动主程序或猜端口恢复，下一步列案。

### 第三步：列出本机案件（本次成功）

~~~powershell
& $ges case ls --json
$listExitCode = $LASTEXITCODE
~~~

本次退出码 **0**，返回 `cases` 数组，`returned=2`、`total=2`、`next_offset=null`、`source_complete=true`。实际记录如下：

| 案件名称 | 案件编号 | 原检材完整路径 | 当时状态 |
|---|---|---|---|
| 222 | 20261018151503W | `A:\手机镜像\手机.tar` | `ges_url=未打开`，`availability.state=closed` |
| 111 | 20261014203107C | `A:\计算机镜像\计算机检材.E01` | `ges_url=未打开`，`availability.state=closed` |

两项 `availability.verified` 均为 false，`reason=backend_not_verified`。该次仅证明 **CLI 能调用且本地案件列表能读取**，不证明案件已打开、原镜像仍在线或解析完成。上表为历史实测记录，后续必须重新列案，不把历史编号设为默认目标。

### 第四步：确定目标后打开并复查（本次尚未执行）

当用户只要求测试且未指定案件时，报告候选并询问选择；当用户已经提供案件编号，或检材完整路径唯一对应一案时，直接使用已确定目标，不重复问同一问题。

以下是后续操作方法，**不属于本次已经成功验证的结果**：

~~~powershell
# $caseNumber 必须来自当前列表及用户已确定的目标。
& $ges case open $caseNumber
if ($LASTEXITCODE -ne 0) { throw '案件打开失败；保留错误，不开始内容分析' }
$statusText = & $ges status --json
if ($LASTEXITCODE -ne 0) { throw '案件后台仍不可达；检查打开结果' }
$caseStatus = $statusText | ConvertFrom-Json
# 按实际返回字段提取 $cid 和 $gesUrl；不猜字段位置或默认端口。
& $ges --cid $cid --ges-url $gesUrl evidence ls --json
& $ges --cid $cid --ges-url $gesUrl ls /case/ --json
& $ges --cid $cid --ges-url $gesUrl ls /evidence_mounts/ --json
~~~

逐个检查退出码与实际返回。案件打开后仍须核对目标检材路径和解析状态，不能把 open 成功当作所有数据就绪。JSON 分页未完整就继续读取，错误不当作空结果。

## 正确的案件上下文

1. status 成功时记录真实 cid、GES URL、检材，再用显式 cid/URL 执行 case ls；status 失败才用裸 case ls。
2. 只按用户指定完整案件编号或与原检材完全一致的路径定位，不挑第一个案件，不按相似名称匹配。
3. 已指定目标时 case open <真实案件号> 后重新 status。case open 会启动/复用案件后台，不靠启动 goldeneyes.exe 猜端口。
4. 新检材已授权建案时，按管理技能创建/导入；目标案件不明确才询问。导入超时先查 evidence ls --path，避免重复导入。
5. 多任务使用 ges init --scope cwd --cid <真实cid> --ges-url <真实URL>，保持各成员 cwd 一致；也可每次显式传 cid/URL。默认用户上下文可被其他会话覆盖。
6. 实际解析/分析开始后的等待计入 DeepSeek 45 分钟。长任务用终端异步会话或 CLI 异步参数，队长持续监督。

~~~powershell
& $ges case ls
# 下列变量必须来自真实返回，不可照搬示例编号。
& $ges case open $caseNumber
& $ges status
& $ges init --scope cwd --cid $cid --ges-url $gesUrl
& $ges evidence ls
~~~

## 分析与提取

~~~powershell
& $ges ls /case/
& $ges ls /evidence_mounts/
& $ges grep '关键词A|关键词B' --syntax keyword --path /case/
& $ges read $foundVirtualPath --offset 0 --limit 100
& $ges glob -p '**/*.db' --path $knownEvidenceMount
& $ges copy $foundDatabasePath --dest $localOutput
~~~

$found/$known 路径均须来自本次 CLI 返回。/case/、/evidence_mounts/ 是 GES 虚拟路径，不能交给本地 Get-Content、sqlite3、os.listdir；先 copy 再在工作副本计算。SQLite 检查源目录及复制结果中的同名 WAL/SHM、copied_sidecars（若返回）和 warnings，再核对本地文件；不能假定 CLI 必然带齐旁文件，缺失则按实际存在的路径补导出并记录一致性限制。

计算机检材先执行 evidence partitions --eid <真实eid> --json。仅真实 state=encrypted 且有用户提供的恢复材料时按管理技能解密，不按盘符猜状态或猜密钥。

## DeepSeek 解题时，GPT 的并行准备清单

DeepSeek 启动后，GPT 立即执行实际火眼命令，同时持续监视首轮截止时间。准备按需推进，不机械重做已完成事项：

| 准备目标 | 火眼调用 | 保存内容 |
|---|---|---|
| 连接与身份 | `status --json`；不可达则 `case ls --json`，确定目标后 `case open` | 当前案件、真实 cid/URL、检材路径、退出码 |
| 解析就绪 | 显式绑定 cid/URL 的 `evidence ls --json`；按需 `task ls --eid <实际eid> --json` | eid、当前解析状态、活动任务和归属 |
| 数据导航 | `ls /case/ --json`、`ls /evidence_mounts/ --json`，再有界展开 | 与题目相关的真实路径，不猜目录 |
| 检索条件 | `index status --json`，计算机检材按需 `evidence partitions --eid <实际eid> --json` | 索引覆盖情况、分区真实状态 |
| 共用材料 | 已分配给 GPT 的 `copy <已发现路径> --dest <work/prep/exports/...>` | 导出范围、完成状态、manifest、文件清单 |

上述查询均固定到同一已确认案件，使用 `& $ges --cid $cid --ges-url $gesUrl ...`；不要在并行期间修改对方的用户默认上下文。GPT 作为唯一状态操作执行者负责打开/切换、init、导入和索引/解析任务创建，DeepSeek 在自己的 progress.json 请求准备，并读取 GPT 的 prep.json 获取结果。

GPT 的准备产物写 work/prep/，八名 DeepSeek 成员的检查点和导出分别写 work/deepseek/members/<Pxx>/；启动器独占团队状态、分工清单、成员 state.json、runner.lock 和 attempt 日志。队长写简报、交接、答案与 verified.json；P07 独写 WP，P08 独写用户指定知识库，具体按 team.md。两者可读取对方的已完成产物。一次导出/索引/解析只登记一个执行者，分配与状态写 prep.json，再开始操作。长任务用异步/短等待，每 20–30 秒检查 dsh 和新答案；不让准备阻塞 45 分钟截断。

启动 DeepSeek 前按 templates.md 初始化 prep.json，连接状态为 preparing，未知绑定为 null；核实目标后更新 ready 和真实 cid/URL。DeepSeek 等待中整理题目、复用已就绪材料，每 20–30 秒重读，不把 preparing 当作失败。无法推进才设 blocked 并写明原因。绑定更新后两侧都用最新值，并核对案件号仍与简报目标一致。

共享案件后台由 GPT 从 dsh 进程树外打开。到期交接时保留有用的 GPT 准备产物与活动任务，按归属处理 DeepSeek 残留；不停止用户原有或 GPT 准备中的共享服务。

## 空结果、分页与后台任务

- ls 的 JSON 列表键为 entries，grep/glob 为 matches。按 next_offset 分页；next_offset=null 且 source_complete=true 才表示范围完整。
- keyword 仅 index_state=current、index_coverage=covered 时支持“不存在”的结论；否则查看 index status，按需构建或使用有界 regex。
- 长时间 copy 用 --async，记录 job_id、manifest；查询 job status，不重复提交。只信 completed 且 result_current 不为 false 的结果。
- 到期对本次可取消的复制任务调用 job cancel <job-id>，再确认状态。不取消别人的任务、不重启共享服务。
- 不能安全取消的解析/解密任务记录 task_id、归属和状态，由 GPT 接续复用。

## 引用和归档

保存命令、输出范围、实际路径、行号与案件/检材编号。/case/ 可点击溯源先 read，复制完整 Goldeneyes://<case_number>/<node_id> 基址并追加 #<实际行号>，写成 [[1]](实际链接)。未返回基址就不造；挂载原文件和本地副本使用路径/偏移。

依据可定位，重要推导与汇总独立复核；不以重复输出凑双证。格式遵题目，版本、时区和编码一致。旧 APK 案例中的 DCloud 统计域名、权限分类、Manifest 编码只作为线索，不套入新题。

首轮结束先交付已解题，再由 GPT 接续。各成员绑定同一已确认案件，写目录不冲突，队长逐题归档；交接后补齐 P07/P08 未完成的 WP/知识库。此处 GPT 接续阶段按可用槽位分工；DeepSeek 首轮固定六名解题手、一名 WP 编写者、一名知识库整理者，不使用其他模型。

## 解密后挂载异常与复制冲突

以下为2026-10-21案例暴露的故障处理路径，不保证其他版本行为相同；参数先看本机帮助。

- `state=decrypted`只证明后端状态，不证明文件视图已更新。通过GES核对实际目录、分区大小、时间及目标文件；卷名/D:等字样不是检材身份证明。若约40GB检材分区映射到约296GB本机卷，立即停止该路由的内容读取，将路由标为不可用。
- 用户确认重新挂载或重新打开后，先重新发现已确定案件后台；必要时对同一已确认案件执行case open，再status核对。端口可能变化：原子更新prep.json的case_binding及所有成员使用的绑定，不只新增一个无效的顶层ges_url字段。
- 不臆造mount/remount子命令，不因CLI参数报错把同样命令反复重试；case open等命令是否支持--json以帮助为准。不重复解密已decrypted分区、不杀共享服务。
- 可用--no-daemon做一次有界的前台查询区分缓存问题；它不保证修复映射。新旧虚拟路径分别核实身份后再使用。若只剩界面可导出，准确说明需导出的检材目录；已得到密码确认不反复求同一授权。
- 目录copy若因后端返回重复路径而报清洗后名称冲突，保存错误与清单，确认失败任务已结束。先缩小到题目需要的子目录；仍失败时可逐个导出已发现的少量必要文件作为例外。记录每个文件的成功状态、大小、哈希与关联文件；不能因个别文件成功把整目录标ready，也不绕过GES读取虚拟挂载本地路径。
- 用户手动操作完成后先检查文件可读性，再要求更多手动步骤。若电脑控制被用户停止，停止界面输入，保持已授权的独立分析范围；不通过另一种UI自动化绕过停止。
- 用户重启后，旧端口拒绝连接、缓存status或失败调用附带空列表，都不证明内容为空。重新列案发现同一案件的服务并核对检材，更新 `prep.case_binding` 后再查询；只在有效绑定、完整分页下解释空结果。
- “恢复任务成功”与“目标文件已恢复”分别登记：任务所属eid、类型、task_id、状态，以及实际结果节点/导出清单/文件可读性。一次刷新或前台查询仍未暴露结果时，记录“该接口未见”，不反复扫描同一路径或要求重启；先检查存储归属，再提出一次具体的结果导出需求。详见 [server-forensics.md](server-forensics.md)。
- UI输入返回成功后需观察实际状态变化；一次有界重查仍无变化就记录无可见响应，不声称已刷新，也不将权限原因当作已确诊。AV明确阻止文件读取时保留错误与文件版本，使用已授权的可读原始记录交叉验证；历史文件不能充当当前版本，不关闭防护或绕过阻止。

本案恢复原因是用户重新挂载后重新连接原案件，原始分区视图才恢复；不要把该次成功写成通用“--no-daemon能解锁”规则。
