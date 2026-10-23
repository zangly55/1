# Windows NAS 映射盘符取证检查点

- 条目 ID：KB-TOPIC-NAS-001
- 状态：通用方法（本案实例待 `verified.json` 确认后补入）
- 适用条件：需要确认嫌疑人把 NAS/SMB 共享映射成了哪个本地盘符。

## 检查点与命令

1. 用户级网络驱动器（最直接）：

```text
HKCU\Network\<盘符>        RemotePath = \\NAS\share
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2
```

2. 系统级/会话级映射与最近使用：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Map Network Drive MRU
NTUSER.DAT\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs
```

3. 快捷方式与脚本：`.lnk` 的目标、`net use X: \\NAS\share` 的脚本/命令历史、`PowerShell` 历史（`ConsoleHost_history.txt`）。

```powershell
ges.exe glob -p "**/*.lnk" --path "/evidence_mounts/eid-<eid>/Users/" --json
ges.exe grep "net use|\\\\[A-Za-z0-9._-]+\\" --syntax regex --path "/evidence_mounts/eid-<eid>/Users/" --glob "*.txt" --json
```

4. 导出 `NTUSER.DAT` 后用 Registry Explorer 离线看 `Network` 键；不要直接把注册表当文本 `grep` 猜盘符。

## 证据来源要求

- 两条独立依据：`HKCU\Network\<X>\RemotePath` + 资源管理器 MRU/快捷方式/`net use` 记录之一。
- 盘符答案只写单个字母（如 `Z`），不写 `Z:`，除非题目另有格式要求。

## 易错点

- 盘符可能已被删除但 `MountPoints2` 仍留痕；`Network` 键存在通常比 MRU 更可靠，但仍要与访问记录互证。
- 同一 NAS 可能映射过多个盘符，题目问“嫌疑人 NAS 映射的盘符”通常指案发时仍在用/最近使用的那个，需要时间线佐证。
- 系统盘符与用户盘符、本地磁盘与网络磁盘要区分；不要用 `Get-PSDrive` 的当前会话结果替代镜像证据。
- UNC 路径中的反斜杠在 JSON/正则中要转义，`grep` pattern 建议放 `--pattern-file`。
