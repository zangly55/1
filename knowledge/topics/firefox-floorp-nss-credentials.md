# Firefox / Floorp 保存密码（NSS SDR）解密

- 条目 ID：KB-TOPIC-NSS-001
- 来源：本案 verified Q19（`answer/Q19.json`，P05 解密并经 GPT 复核）；通用算法为 Mozilla NSS SDR 格式。
- 适用条件：Firefox 或 Floorp 等 Gecko 系浏览器，`logins.json` 中 `encryptedUsername`/`encryptedPassword` 为密文，配置目录同时有 `key4.db`，且未设置主密码。

## 工具命令

```powershell
ges.exe copy "/evidence_mounts/eid-1/.../Profiles/<profile>/logins.json" --dest "<成员output>\exports\floorp"
ges.exe copy "/evidence_mounts/eid-1/.../Profiles/<profile>/logins-backup.json" --dest "<成员output>\exports\floorp"
ges.exe copy "/evidence_mounts/eid-1/.../Profiles/<profile>/key4.db" --dest "<成员output>\exports\floorp"
ges.exe copy "/evidence_mounts/eid-1/.../Profiles/<profile>/formhistory.sqlite" --dest "<成员output>\exports\floorp"
```

本地用 Python `sqlite3` + `hashlib` + `cryptography`/`pycryptodome`：

1. `key4.db` 的 `metadata` 表取 `item1`（globalSalt）、`item2`（加密的 password-check）。
2. `SHA1(globalSalt)` 作为 PBE 口令；`PBKDF2-HMAC-SHA256(salt=item2 的 PBKDF2 salt, iter=1, dkLen=32)` 派生密钥。
3. 按 NSS 的 DER 头 `0x04 + 长度 + 14 字节` 组成 16 字节 IV，`AES-256-CBC` 解 `item2`，应得到 `password-check\x02\x02`（校验解密链正确、无主密码）。
4. 同法解 `nssPrivate.a11` 得 32 字节 SDR key。
5. 用 SDR key 对 `logins.json` 的 `encryptedPassword` 做 `AES-256-CBC`（前 16 字节为 IV）解密，得到明文口令。

## 证据来源

- 本案 `logins.json` 第 1 条 `hostname=http://192.168.188.211:18480`，与 AI 网站端口一致。
- `logins-backup.json` 同址记录用同一 SDR key 解出相同密码，两份密文互证。
- `formhistory.sqlite` 的 `moz_formhistory` 用户名与 `logins.json` 解密出的用户名一致。

## 易错点

- Firefox/Floorp 不是 Chromium：不能套 `Login Data` + DPAPI 流程；`logins.json` 是 NSS SDR 密文。
- `key4.db` 的 `item2` 解密结果是校验串 `password-check\x02\x02`，不是密码本身；解不出它说明主密码/算法有误。
- IV 构造容易错：不是固定全零，也不是直接取密文前 16 字节；按 NSS DER 头规则解析。
- `logins-backup.json` 的 username 可能与当前 `logins.json` 不同（历史账号），但同一 host 的密码可互证。
- 密码区分大小写；知识库/通用条目一律写 `<已脱敏>`，原值只保留题解。
