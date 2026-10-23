# Linux Samba 与面板日志取证

- 条目 ID：KB-TOPIC-SAMBA-001
- 适用条件：Linux/NAS 镜像中需确认 Samba 完整版本标识、共享目录允许访问的用户名，或面板日志被清空后第一次访问的目录；已通过 GES 打开并解析。
- 来源：案件 20261021162519O 的 `answer/Q03.json`、`Q04.json`、`Q05.json`；Q05以2026-10-21的 [独立复核记录](C:/Users/35124/Documents/取证/ESXi-20261021/work/gpt/reference-review/Q05-review.json) 为当前依据。
- 复核方法：包管理记录 + 原始配置/日志/历史命令交叉；面板题以清空事件后的首条目录请求为准。

## 一、Samba 完整版本标识

1. 先看已安装软件表（有解析结果时最快）：

```text
/case/<eid>/Linux基本信息/<主机>_分区N/安装软件/data.csv
行示例：samba,samba-4.10.16-25.el7_9.src.rpm,4.10.16
```

- 第一列包名，第二列 RPM 源包文件名，第三列常只保留主版本。
- **完整标识取 RPM 文件名的 `版本-发行版` 段**：`4.10.16-25.el7_9`；不要只写 `4.10.16`。

2. 用原始文件系统记录复核：

```powershell
ges.exe read "/evidence_mounts/eid-<eid>/<主机>/分区N/var/log/yum.log" --offset 0 --limit 200
ges.exe read "/evidence_mounts/eid-<eid>/<主机>/分区N/etc/samba/smb.conf" --offset 0 --limit 80
ges.exe grep "smbd --version|rpm -qa|yum" --syntax regex --path "/evidence_mounts/eid-<eid>/<主机>/分区N/root/" --glob ".bash_history" --json
```

- `yum.log` 的 `Installed: samba-4.10.16-25.el7_9.x86_64` 是强证据。
- 已保存的 `rpm -qa` / `smbd --version` 输出可作旁证；shell历史中的命令本身不等于执行输出。不同记录可能一个带发行版一个不带，结合已安装包记录判断。

## 二、共享目录允许访问的用户名

在 `smb.conf` 的共享段中找授权字段：

```ini
[my_share]
   path = /var/samba/share
   valid users = <user>
   read only = no
```

- 题目问“允许访问的用户名”通常对应 `valid users`；`write list`/`read list`/`force user` 语义不同，按题干区分。
- 多个用户名用逗号/空格分隔；`@group` 是组，不是用户名。
- 配置若 `include =`/`config file =` 引用子文件，继续跟进，别只看主配置。

## 三、面板日志被清空后第一次访问的目录

宝塔等面板会记录登录/操作/错误/请求日志，删除动作本身也留在 `request` 日志里：

```powershell
ges.exe glob -p "**/panel/logs/request/*.json" --path "/evidence_mounts/eid-<eid>/<主机>/分区N/" --json
ges.exe copy "/evidence_mounts/eid-<eid>/<主机>/分区N/.../panel/logs/request/" --recursive --dest "<output>\exports\nas-request"
```

先比较不同日志目录和日期中的删除/清空事件，再选题干对应事件。本案NAS原始 `/www/wwwlogs/request/2025-10-22.json` 第1、2行如下；较完整的 `nas-request/2025-10-22.json.gz` 第284、285行亦保存同一事件：

```text
2025-10-22 10:46:05 SetBatchData type=4 path=/www/wwwlogs
  data=[go,java,net,nodejs,other,python,request]
2025-10-22 10:46:05 GetDirNew path=/www/wwwlogs
```

- 原始 `files.py` 核对type=4属于删除分支。同秒请求保留原始行序，不打乱前后关系。本题更正答案为 `/www/wwwlogs`。
- 10月23日还有另一组清操作/登录/运行日志事件；旧答案 `/` 误用了这一组，已撤回。题干未明说日期，本案采用与参考方向一致、且有原始删除及连续目录访问记录支持的22日事件解释；不推广为“任何清日志题取最早残存行”。
- 若题干问“物理路径”，核对面板路径映射、容器挂载和请求语义，不直接把任意URL当文件系统路径。
- `bash_history` 的 `cd` 只能作旁证：它没有请求时间，也可能不是同一会话的第一步；与面板请求日志冲突时以请求日志为准。

## 四、面板请求日志还原计划任务

宝塔 `request` 日志的 `AddCrontab` 请求会把任务名和脚本体放在 `sBody` 中：

```text
2025-10-22 05:39:47  AddCrontab  name=采集正版（收费）小说  sBody=... BASE_URL=https://www.xinglo.com ...
```

- 即使计划任务后来被删除，`request` 日志仍保留创建时的 `sBody`；可从中提取 `BASE_URL`、`curl` 目标、脚本路径。
- 与当前 `/var/spool/cron/root`、`/etc/crontab`、宝塔任务表交叉：文件里没有的任务，日志里可能有。
- 题目要域名时去掉协议和路径，只留主机名。

## 证据来源要求

- 版本：安装软件表行号或 `yum.log` 行 + RPM 全名；
- 用户：`smb.conf` 完整共享段（共享名、path、`valid users` 行）；
- 面板：`request` 日志文件路径 + 清空动作与首条 `GetDirNew` 的原始行/时间；
- 需要时补 `/etc/passwd`、`pdbedit -L` 证明账号存在。

## 易错点

- 把 `samba-4.10.16` 当完整版本，漏 `-25.el7_9` 发行版后缀。
- 把 `smbd --version` 的简短输出当最终答案，忽略 RPM 全名。
- 把 `guest ok = yes` 当具体用户名；匿名访客不是账号。
- 把共享名 `[my_share]` 当用户名。
- 只读主 `smb.conf`，漏 `include` 子配置。
- 面板题用 `bash_history` 的 `cd` 猜“第一次访问目录”；没有时间戳，容易把后续操作当首次。以清空事件后的首条 `GetDirNew` 为准。
- 清空日志后第一条请求可能是登录页/静态资源；要找文件管理器的目录请求（`action=GetDirNew`），根目录记为 `/`。
- 只查当前 crontab 文件找不到已删除的采集任务；面板 `request` 日志的 `AddCrontab.sBody` 才是创建时原文。


