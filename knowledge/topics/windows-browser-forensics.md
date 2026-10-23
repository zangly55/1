# Windows 浏览器取证检查点（默认浏览器 / 历史 / 保存的登录）

- 条目 ID：KB-TOPIC-BROWSER-001
- 状态：通用方法（本案实例待 `verified.json` 确认后补入）
- 适用条件：Windows 10/11 镜像，需回答默认浏览器、访问过的站点/端口、浏览器保存的登录口令等问题。

## 检查点与命令

1. 先定位浏览器用户数据（Chrome/Edge 同源 Chromium 结构）：

```text
%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\History
%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Login Data
%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Web Data
%LOCALAPPDATA%\Microsoft\Edge\User Data\<Profile>\History
%LOCALAPPDATA%\Microsoft\Edge\User Data\<Profile>\Login Data
%APPDATA%\Mozilla\Firefox\Profiles\<profile>\places.sqlite
%APPDATA%\Mozilla\Firefox\Profiles\<profile>\logins.json
```

```powershell
ges.exe glob -p "**/User Data/**/History" --path /evidence_mounts/eid-<eid>/ --json
ges.exe glob -p "**/Login Data" --path /evidence_mounts/eid-<eid>/ --json
ges.exe copy "/evidence_mounts/eid-<eid>/.../History" --dest "<成员output>\exports"
```

2. 默认浏览器看 URL 关联的 `UserChoice`（`http`/`https` 都要看）：

```text
HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice
HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.html\UserChoice
```

ProgId 常见值：`MSEdgeHTM`（Edge）、`ChromeHTML`（Chrome）、`FirefoxURL-*`（Firefox）。离线可把 `NTUSER.DAT` 导出后用 Registry Explorer/reg 加载，只读挂载。

3. 历史与登录（导出副本上做，避免锁库）：

```sql
-- History
SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY last_visit_time DESC;
-- Login Data
SELECT origin_url, username_value, length(password_value) FROM logins;
```

Chromium 时间戳是 1601-01-01 起的微秒；口令列通常是 DPAPI 加密的 BLOB，不是明文。

4. 站点端口：对命中 URL 做解析，显式端口优先；`https://host` 默认 443、`http://host` 默认 80，题目问“端口”时不要把默认端口误当自定义端口。

```python
from urllib.parse import urlparse
u = urlparse(url)
port = u.port or (443 if u.scheme == 'https' else 80)
```

## 证据来源要求

- 至少两条独立依据：注册表 `UserChoice` + 浏览器 `Preferences`/历史记录；或 `History.urls` + `Login Data.logins`。
- 引用 `/case/` 记录须用 `ges read` 顶部真实 `Goldeneyes://` 基址加行号；导出副本只能写本地路径。

## 易错点

- 多用户、多 Profile（`Default`、`Profile 1`、`Guest Profile`）要分别检查；只看一个 Profile 会漏。
- `History`、`Login Data` 可能带 `-wal`/`-shm`，`ges copy` 会一并复制，查询前让 SQLite 正常打开。
- 保存的口令可能是密文；没有 DPAPI 主密钥/用户密码时不能把密文当明文答案。知识条目中一律写 `<已脱敏>`。
- 默认浏览器可能被改过多次，注册表当前值只代表最后一次设置；结合 `Preferences` 的 `last_used` 与历史时间线。
