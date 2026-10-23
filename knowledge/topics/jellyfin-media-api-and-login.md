# Jellyfin 媒体系统 API 密钥与管理员最后登录

- 条目 ID：KB-TOPIC-JELLYFIN-001
- 适用条件：Linux/容器中部署 Jellyfin 媒体服务器，需找外部程序（如“芯龙短片”）的 API 通信密钥，或管理员最后登录时间。
- 来源：案件 20261021162519O 的 `answer/Q18.json`、`answer/Q19.json`（`verified.json` revision 3）。
- 复核方法：`jellyfin.db` 的 `ApiKeys`/`Users`/`ActivityLogs` 表 + 同时间日志行交叉；密钥只在题解中出现，通用条目脱敏。

## 一、定位数据与日志

```text
/var/lib/jellyfin/data/jellyfin.db          # 常见数据目录
/var/lib/jellyfin/data/                     # 也可能在容器 volume 下
/var/log/jellyfin/log_YYYYMMDD.log          # 运行日志
```

```powershell
ges.exe glob -p "**/jellyfin.db" --path "/evidence_mounts/eid-<eid>/" --json
ges.exe copy "/evidence_mounts/eid-<eid>/.../jellyfin-data/jellyfin.db" --dest "<output>\exports"
ges.exe copy "/evidence_mounts/eid-<eid>/.../jellyfin-log/" --recursive --dest "<output>\exports"
```

## 二、外部程序 API 密钥

```sql
SELECT Id, Name, AccessToken, DateCreated, DateLastActivity FROM ApiKeys;
SELECT Id, Username, LastLoginDate, LastActivityDate FROM Users;
SELECT * FROM ActivityLogs ORDER BY ActivityDate DESC LIMIT 20;
```

- 先按 `Name` 精确匹配外部程序名（如“芯龙短片”），取该行 `AccessToken`；不要取相邻的 `AppSecret`、商户 key 或其他应用配置。
- `Users.LastLoginDate` 与 `ActivityLogs.AuthenticationSucceeded` 可印证用户登录时间，不能单独证明某 API key 曾被使用。
- 题目要求“全小写”时按原值检查大小写，不自行改写。

## 三、管理员最后登录时间

- `Users.LastLoginDate` 形如 `2025-10-21 10:47:52.6957766`，Jellyfin 以 **UTC** 存储，无时区后缀。
- 日志行形如 `[2025-10-21 10:47:52.697 +00:00] Authentication request for <user> has succeeded`，可确认 UTC 并精确到秒。
- 北京时间 = UTC + 8 小时，按题干 `YYYYMMDD-HHMMSS` 输出；毫秒/微秒直接截断，不进位。
- “最后登录”取 `LastLoginDate` 最新值；如为空，用 `ActivityLogs`/日志中最后一次 `AuthenticationSucceeded` 补证。

## 证据来源要求

- 数据库路径 + 表名 + `ApiKeys.Name`/`AccessToken` 行（题解可留原值，通用条目脱敏）；
- `Users.Username`、`LastLoginDate` 原始值与 UTC→+8 换算；
- 日志文件路径 + 行号 + 原始时间戳；
- 记录数据库/日志的复制命令与哈希（如题要求）。

## 易错点

- 把 PHP 站点的 `appid`/`appsecret`/商户 key 当作 Jellyfin API key；应以 `ApiKeys.Name` 与外部程序名对应。
- `LastLoginDate` 直接当北京时间，差 8 小时。
- 取微秒/毫秒参与格式化，导致秒级进位错误。
- 只看 `Users.LastLoginDate` 不看日志，无法证明时区；两者应一致。
- 把管理员的“最后活动时间”当“最后登录时间”，二者字段不同。

