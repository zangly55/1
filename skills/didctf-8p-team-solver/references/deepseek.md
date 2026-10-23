# DeepSeek 首轮调用

本机已验证：直接运行 dsh headless 曾报 MISSING_CREDENTIAL；从 ~/.dsh/.credentials.yaml 的 refs.DEEPSEEK_API_KEY 临时读取实际 API Key 并传入子进程后调用成功。不需要重新安装，也不用把密钥发到聊天或写入系统/用户环境变量。

## 正式任务：八人编排器

正式取证必须使用 [team.md](team.md) 的 `run_deepseek_team.py`，真实启动八个独立会话。下面单会话命令是编排器底层机制说明及诊断入口，不可作为正式题组的单人替代。

## 底层：复用限时启动脚本

使用火眼自带 Python 3.11 和 PyYAML。脚本优先读取当前进程已有的 DEEPSEEK_API_KEY；没有时，读取 DSH_HOME（默认用户目录下 .dsh）中的 .credentials.yaml，取 refs.DEEPSEEK_API_KEY 的直接 sk- 密钥。如果将来该字段变为凭据引用 ID，不猜记录结构，应恢复官方凭据服务配置。

把 $work 替换成真实案件工作目录，先按 templates.md 写好题目和提示词：

~~~powershell
$skill = 'C:\Users\35124\.agents\skills\didctf-8p-team-solver'
$py = 'E:\取证工具\GoldenEyesV4\Python311\python.exe'
$work = 'C:\实际案件工作区'
$runnerArgs = @('--prompt-file', "$work\work\deepseek-prompt.txt",
                '--workdir', $work,
                '--output-dir', "$work\work\deepseek",
                '--limit-seconds', '2700')
& $py "$skill\scripts\run_deepseek.py" @runnerArgs
~~~

终端工具 yield_time_ms 设 1000–10000，让命令返回 session_id；用 write_stdin 等待每次不超过 30 秒，期间读 state.json、answers/ 和日志。不要等阻塞 45 分钟的调用返回后才找答案；进行中每 60 秒内给用户有内容的进度更新。

**启动后 GPT 必须同时调用火眼做准备**，执行 SKILL.md 的“GPT 并行调用火眼准备”和 playbook.md 的准备清单。把 dsh 状态检查与火眼连接、检材/目录核对、已分工导出交替推进，并原子更新 work/prep/prep.json 供 DeepSeek 读取。准备不是单纯等待：保留实际命令、退出码、任务归属和材料就绪状态；也不能因准备命令阻塞而错过首轮截止时间。

脚本按本机 dsh.cmd 已验证的内容，直接用 DeepSeek Harness.exe + ELECTRON_RUN_AS_NODE=1 启动 app.asar 内的 CLI，再传 headless --json -。这是同一个 dsh 入口，避开 Windows .cmd 转义问题。安装布局改变时先看 dsh.cmd 再适配；自定义路径用 --dsh。

提示词通过 stdin 传入，不出现在命令行参数里。密钥只放在子进程环境；不改父进程环境、用户注册表和持久配置。日志写入前替换实际 API Key；不要开启环境转储或让 DeepSeek 打印凭据。

## 状态与截止时间

- state.json 原子更新：started_utc、deadline_utc、pid、attempt、status、stdout_log、stderr_log。
- stdout 为 dsh --json 事件流；stderr 为诊断文本（扩展名也是 jsonl，但不保证每行是 JSON）。正式题解以 answers/ 独立 JSON 为准。
- 默认 2700 秒，上限不可提高；--limit-seconds 可更短，用于验证。
- completed / 退出码 0 只表示进程正常退出，必须另查是否每题都解出。
- timed_out / 124：截止已到；tree_stop_confirmed=true 表示本次 Windows Job Object 内所有进程均已终止，cleanup_required=true 表示残留需核实。
- failed / 非零码：保存已有题解，报告故障，按剩余预算决定一次修正重试或转 GPT。
- interrupted / 130：用户或外部中断；如果用户要求停止任务就停止，不自行启动 GPT。
- 同一 output-dir 由 Windows 文件锁独占，重复启动立即拒绝；runner.lock 文件留存不代表仍被占用，锁随进程退出释放，不要删除运行中的锁文件。starting / running / 未清理状态拒绝重启，日志按 attempt 编号分文件。
- 同一题组重试沿用最早 deadline_utc，最多一次恢复重试（总计两次启动）。已过期时直接返回 124，不读取密钥、不启动进程，也不增加启动次数。每个新题组使用独立工作区；不能借新目录给同一题组重置期限。
- 跨会话恢复读取原 state.json；迁移目录时也用 --deadline-utc 传原截止时间。到期直接交接，不再启动 DeepSeek。
- 启动时先挂起子进程，绑定带 KILL_ON_JOB_CLOSE 的 Windows Job Object 后才恢复运行，防止子进程在绑定前逸出。正常退出也清理残留子进程；启动器被强制结束时 Windows 会关闭句柄并清理该作业。崩溃后 state.json 可能仍为 running，恢复时按 PID 与启动时间复核身份，不凭陈旧 PID 杀其他进程。
- 火眼独立服务和服务器任务不一定随 dsh 进程树终止，按 SKILL.md 的后台任务规则处理。

## 无法读取凭据

不打印凭据文件，不展示密钥片段，不复制密钥到 prompt 或技能。只检查文件存在、PyYAML 可用、字段结构和变量是否为空，只输出布尔状态。无法识别格式时报告缺少可用凭据，等待 Models 配置或采用此前已授权的认证方式；不自行持久化密钥。

## Windows 命令行权限故障（2026-10-20 实测修复）

症状：模型正常回复，文件工具可用，但每次 `pwsh` 都报
`SetNamedSecurityInfoW failed (Win32 5): grantWrite(<案件工作区>)`。
这发生在命令启动之前，不能以 dsh 的 `completed` 或退出码 0 判定工具可用。

本次目录 `E:\取证\手机题组-20261020` 的所有者为当前用户，但 ACL 只通过
Authenticated Users 提供 Modify，FullControl 仅给 Administrators/SYSTEM；
当前进程管理员组处于 deny-only 状态。用户明确要求修复后，仅给当前用户补充
该工作区的可继承 FullControl，保持已有 ACL、原检材权限与沙箱配置，故障消失。
这是本机诊断结果，不代表每个 Win32 5 都由相同原因造成。

遇到同类错误先读取目标 ACL、当前身份和失败日志。权限修复需用户授权；
用户已明确要求修复时无需重复确认。仅修改明确的本次工作区，禁止对盘符根、
用户根、原检材或其他项目批量放权；不授予 Everyone，不关闭沙箱，不绕过审批。
若 Set-Acl 本身被拒绝，保留错误并说明阻塞，不擅自接管所有权。

下面片段需替换两个路径；备份目录放在工作区外。保留备份供回滚，不自动重置整棵目录：

~~~powershell
$targetDir = 'E:\实际案件工作区'
$backupFile = 'C:\实际诊断目录\workspace-acl-before.sddl'
$targetAcl = Get-Acl -LiteralPath $targetDir
$targetAcl.Sddl | Set-Content -LiteralPath $backupFile -Encoding ASCII
$userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $userSid,
    [System.Security.AccessControl.FileSystemRights]::FullControl,
    [System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AccessControlType]::Allow)
$targetAcl.AddAccessRule($rule)
Set-Acl -LiteralPath $targetDir -AclObject $targetAcl -ErrorAction Stop
~~~

必须通过 DeepSeek 的真实 `pwsh` 工具验证，而不是让 GPT 代跑后宣称成功：

1. 在原工作区运行 `Write-Output "DS_SHELL_OK"`；检查事件日志中的
   `tool_result.status=completed` 和实际返回字符串。
2. 让 DeepSeek 调用 `ges.exe --cid <已确认cid> --ges-url <已确认URL> status --json`；
   读取真实返回的案件、检材挂载信息。不得为测试猜端口、切换案件或重导检材。
3. 本次两项均通过，火眼返回 cid=1、URL=`http://127.0.0.1:8835`、
   检材 `手机.tar`、无跳过挂载。此 URL 仅是当次结果，不是后续默认值。

诊断单独保存日志，不改解题首轮的 state.json、次数或原截止时间。
只验证模型回复/算术题无法覆盖此故障；正式解题前应加一次真实命令调用。

## 手动临时调用（仅诊断）

~~~powershell
# 不输出 $key，不运行 setx；正式任务使用上述限时脚本。
$credentialPath = Join-Path $env:USERPROFILE '.dsh\.credentials.yaml'
$line = Get-Content -LiteralPath $credentialPath |
  Where-Object { $_ -match '^\s+DEEPSEEK_API_KEY:' } |
  Select-Object -First 1
if (-not $line) { throw '未找到已保存的密钥字段' }
$key = (($line -split ':', 2)[1].Trim().Trim('"', "'"))
if ($key -notmatch '^sk-[A-Za-z0-9_-]+$') { throw '不是已验证的直接密钥格式' }
$previousKey = $env:DEEPSEEK_API_KEY
try {
  $env:DEEPSEEK_API_KEY = $key
  & 'C:\Users\35124\AppData\Local\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd' headless '请只回复：DeepSeek 调用成功'
} finally {
  if ($null -eq $previousKey) {
    Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
  } else {
    $env:DEEPSEEK_API_KEY = $previousKey
  }
  Remove-Variable key,previousKey -ErrorAction SilentlyContinue
}
~~~

手动片段仅适用于已核实的简单 YAML 布局。正式任务使用带 YAML 解析、统一 45 分钟 watchdog 的八人编排器。

## 离线验证

用火眼自带 Python 执行 scripts/test_runner.py：测试使用假密钥和临时进程，验证正常退出、超时杀进程树、根进程先退后的孤儿清理、检查点保留、原期限沿用、跨进程并发锁、一次重试限制、凭据解析和日志脱敏，不访问真实检材或调用 API。

八人离线验证：运行 `scripts/test_team.py`，使用八个独立临时 Python 进程模拟 dsh，不消耗 API。它验证实际八 PID、分工覆盖、统一截止时间、超时清理与脱敏；不能把离线通过称为八个真实 DeepSeek 已连通。
