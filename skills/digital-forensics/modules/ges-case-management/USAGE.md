# 弘连火眼案件准备 Skill 使用说明

本文档面向外部智能体。该 skill 负责分析前准备：列出/打开案件、初始化上下文、
添加检材、等待解析完成。解析后的数据分析应使用 `ges-case-analysis`。

## 必需文件

弘连火眼安装后建议提供以下文件：

```text
%APPDATA%\GoldenEyes\skills\ges-case-management\SKILL.md
%APPDATA%\GoldenEyes\skills\ges-case-management\USAGE.md
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.cmd  (legacy compatibility only)
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges
```

Windows 弘连火眼本体安装目录需要包含：

```text
C:\Program Files\Honglian\GoldenEyesV4\GoldenEyesV4.exe
C:\Program Files\Honglian\GoldenEyesV4\Python311\python.exe
C:\Program Files\Honglian\GoldenEyesV4\Python311\pythonw.exe
C:\Program Files\Honglian\GoldenEyesV4\pyplugin\pygesclient
```

Windows launcher 会从注册表
`HKCU\Software\honglian\GoldenEyesV4`（并兼容 HKLM、32/64 位视图）的默认值或
`Path` 自动定位安装目录，因此 skill 复制到其他目录后仍可使用。launcher 不会更新或
覆盖复制目录中的 skill 文件。

Windows 命令必须使用 `ges.exe` 或不带扩展名的 `ges`（Windows 会优先解析 exe）。
`ges.cmd` 仅用于短期兼容普通参数，不支持含 shell 元字符的 pattern。

需要覆盖自动发现结果时，调用前设置：

```powershell
$env:GOLDENEYES_HOME = "D:\Apps\GoldenEyesV4"
```

## 推荐决策

### 平台版连接

平台用户只需配置 GES 地址和 token，`storage_host` 会自动发现：

```powershell
$env:GES_MASTER_URL = "https://platform.example.com"
# GES_MASTER_TOKEN 由调用环境安全注入
ges case ls
ges case open <cid|case_number|case_name>
ges status
```

案件名称必须完整匹配；重名时使用 `cid` 或完整案件编号。用户没有指定案件时，先展示
`case ls` 结果并询问，不要默认选择第一个。平台 `case open` 只选择远程案件并写入用户
配置，不启动本地程序。也可一次完成初始化：

```powershell
ges init --ges-url <platform_url> --ges-token <认证信息> --case <cid|case_number|case_name>
```

### 1. 用户要使用已有案件

列出案件：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe case ls
```

打开并初始化案件：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe case open <case_number>
```

该命令会：

- 从 `%APPDATA%\GoldenEyes\master.db` 读取案件 `location`。
- 打开案件目录下的 `.gec` 文件。
- 自动发现本次弘连火眼实例的随机 GES 端口。
- 按案件编号确认端口归属。
- 执行 `ges init`，后续命令可以省略 `--cid` 和 `--ges-url`。

只打开、不初始化：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe case open <case_number> --no-init
```

### 2. 用户已经打开案件，且上游知道端口

直接初始化：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe init --cid 1 --ges-url <url>
```

调试端口示例：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe init --cid 1 --ges-url http://127.0.0.1:8999
```

初始化后可检查：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe context
```

### 3. 用户要向当前案件添加检材

先确保已经 `case open` 或 `init`，再运行：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe evidence create --evidence-path "\\devnas.forensix.cn\CTF\检材\VivoBackupFS.zip"
```

默认会创建检材、自动启动解析任务，并阻塞等待解析完成。输出只包含关键节点和粗粒度
进度，适合模型读取。

### 4. 用户没有打开案件，只提供检材路径

可以直接让 CLI 新建案件并导入检材：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe evidence create `
  --evidence-path "\\devnas.forensix.cn\CTF\检材\VivoBackupFS.zip" `
  --case-name "刑侦案件" `
  --investigator "调查员" `
  --case-location ""
```

该流程会：

- 生成启动 JSON。
- 通过无控制台中间进程启动 `GoldenEyesV4.exe --path=<json>`，避免弘连火眼日志污染 CLI 输出。
- 创建新案件并添加检材。
- 自动发现新实例端口，按 `CaseNumber` 验证。
- 自动执行 `ges init`。
- 等待检材解析完成。

`--case-location` 是选填参数：留空或不传时使用默认位置
`~/Documents/GoldenEyes/<case-name>_<case-number>`；需要指定案件保存目录时，将空字符串
替换为目标目录。

如果不希望自动新建案件，使用：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe evidence create --evidence-path <path> --no-bootstrap
```

### 5. 创建 BitLocker 分区解密任务

该任务 API 在弘连火眼单机版和平台版中均可执行。先用 `ges evidence partitions --eid <eid> --json` 核对检材和分区，再执行：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe task bitlocker `
  --eid <eid> `
  --partition "<实际分区名或完整路径>" `
  --password "<BitLocker恢复密钥>" `
  --json
```

恢复密钥可通过重复的 `--password` 提供。CLI 不在文本或 JSON 输出中回显密钥；但明文参数仍可能被系统进程列表或 shell 历史记录看到。命令会保留已有非 BitLocker 密码，相同分区已有任务时不重复创建。使用以下命令查看进度：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe task ls --eid <eid> --keyword bitlockanalyzer --json
```

单机版中，解密任务完成后约 30 秒（刷新周期），`/evidence_mounts/eid-<eid>/` 下会出现以 GES 节点树命名的解密卷目录（如 `新加卷(分区8)/`）。使用以下命令确认卷目录已经出现：

```powershell
%APPDATA%\GoldenEyes\skills\ges-case-management\bin\ges.exe ls /evidence_mounts/eid-<eid>/
```

卷内文件可直接执行 `ls`、`read`、`copy`、`grep`；该视图只读并走完整性校验链，原始分区目录保持不变。本地解密卷发现和刷新仅适用于单机版。

## 重要规则

- 单机版默认 `cid=1`。
- `ges init` 默认覆盖旧配置，并同步更新用户默认配置。
- 如果显式传了 `--ges-url`，或环境变量中存在 `GES_MASTER_URL`/`GES_URL`，但服务不可用，
  `evidence create` 会失败，不会自动创建新案件。
- 想把检材导入已有案件时，先 `ges case open <case_number>` 或 `ges init`。
- `evidence create` 默认按 `--evidence-path` 在当前案件内去重；已存在则不重复添加，任务仍在运行时继续等待。
- 想创建新案件并导入检材时，不要传旧的 `--ges-url`，也不要保留指向旧案件的
  `GES_MASTER_URL`/`GES_URL`。

## 常用参数

指定新案件信息：

```powershell
ges.exe evidence create --evidence-path <path> --case-name "刑侦案件" --case-number-suffix W --investigator "调查员"
```

指定检材编号后 6 位：

```powershell
ges.exe evidence create --evidence-path <path> --number-suffix MP1001
```

只创建检材、不等待解析：

```powershell
ges.exe evidence create --evidence-path <path> --no-wait
```

确实需要重复添加同一路径检材：

```powershell
ges.exe evidence create --evidence-path <path> --no-dedupe
```

创建检材但不自动解析：

```powershell
ges.exe evidence create --evidence-path <path> --no-auto-task
```

补充持有人信息：

```powershell
ges.exe evidence create --evidence-path <path> `
  --person-name "张三" `
  --person-id "320721200203011111" `
  --person-phone "16651847927" `
  --remark "备注"
```

## 推荐流程

已有案件：

```powershell
ges.exe case ls
ges.exe case open <case_number>
ges.exe evidence create --evidence-path <path>
ges.exe context
```

新案件：

```powershell
ges.exe evidence create --evidence-path <path> --case-name "刑侦案件"
ges.exe context
```

检材解析完成后，如需分析解析出的数据，切换到 `ges-case-analysis` skill。

## 排障

- 找不到弘连火眼安装目录：设置 `GOLDENEYES_HOME`。
- 找不到 `pygesclient`：确认 `pygesclient` 位于 `%GOLDENEYES_HOME%\pyplugin`。
- 缺少 `cid` 或 `ges_url`：运行 `ges case open <case_number>`，或直接通过
  `ges evidence create --evidence-path <path>` 新建案件并导入检材。
- 自动发现端口失败：确认目标弘连火眼实例已启动；调试时可用 `--ges-url <url>` 手动指定。
- 只想创建检材不等待解析：添加 `--no-wait`。
- 需要更少或更多进度输出：使用 `--progress-step <percent>`，默认 `20`。
