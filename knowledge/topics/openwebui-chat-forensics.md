# 本地 AI WebUI（Open WebUI）会话、Token 与头像取证

- 条目 ID：KB-TOPIC-AIWEBUI-001
- 适用条件：Linux 服务器/虚拟机部署 Open WebUI 等本地 AI 前端，需统计某时间点会话提问次数、某轮 Token 消耗、首个管理员头像数字。
- 来源：案件 20261021162519O 的 `answer/Q06.json`、`Q07.json`、`Q08.json`（`verified.json` revision 1）。
- 复核方法：数据库文件哈希 + 会话 epoch 换算 + messages 角色序列 + 头像解码看图。

## 一、定位数据库

典型位置（以实际 `ges glob` 为准，不照抄）：

```text
/www/<project>/<app>/openwebui_data/webui.db
/root/.openwebui/webui.db
/var/lib/docker/volumes/<volume>/_data/webui.db
```

```powershell
ges.exe glob -p "**/webui.db" --path "/evidence_mounts/eid-<eid>/" --json
ges.exe copy "/evidence_mounts/eid-<eid>/.../openwebui_data/webui.db" --dest "<output>\exports"
```

- 检查同目录的 `-wal`/`-shm` 是否存在，分别导出并记录；不能假设单文件 copy 会自动复制伴随文件。只在工作副本处理 WAL。
- 记录 `webui.db` 的 SHA256、字节数和复制命令，作为 coverage 证据。

## 二、按题干时间锁定会话

`chat` 表关键列：`id`、`created_at`（Unix 秒）、`chat`（JSON 文本）、`user_id`。

```sql
SELECT id, created_at, datetime(created_at,'unixepoch','+8 hours') AS bj
FROM chat ORDER BY created_at;
```

- 题干是北京时间；`created_at` 是 UTC epoch，`+8 hours` 后比对，秒级相等才锁定。
- 不要用“同一天/同一用户”代替精确时间；同一用户次日另有会话时尤其不能合并。

## 三、提问次数与第二轮 Token

```python
import json, sqlite3
db = sqlite3.connect('webui.db')
chat = json.loads(db.execute("select chat from chat where id=?", (cid,)).fetchone()[0])
msgs = chat['messages']
print('user_questions =', sum(1 for m in msgs if m['role'] == 'user'))
assistants = [m for m in msgs if m['role'] == 'assistant']
print(json.dumps(assistants[1]['usage'], ensure_ascii=False, indent=2))
```

- 本案按题干时间对应会话统计 role=user；其他题目若明确问用户全部历史，则需跨会话统计。
- “第二轮 Token”= 第 2 个 assistant 的 `usage.total_tokens`，常见等于 `prompt_tokens + completion_tokens`；Ollama 后端可能是 `prompt_eval_count + eval_count`。
- 先打印完整 usage JSON 再取字段，兼容不同版本字段名。

## 四、管理员头像数字

```sql
SELECT id,name,role,created_at,length(profile_image_url)
FROM user ORDER BY created_at LIMIT 10;
```

- “创建时注册的管理员”= 按 `created_at` 升序的第一个 `role=admin` 账号；不是当前登录用户或最后修改者。
- `profile_image_url` 常为 `data:image/jpeg;base64,...`；解码保存后**实际打开图片**读取数字/图案。
- 记录图像尺寸、字节数、SHA256，便于复核同一图片。

## 证据来源要求

- 数据库路径 + SHA256 + 复制命令；
- 会话 `id`、`created_at` 原始 epoch 与 +8h 换算结果；
- 完整 messages 的角色/时间戳或统计脚本输出；
- 头像解码文件路径 + 尺寸/哈希 + 目视读数（不能只写“看起来是”）。

## 易错点

- 把 UTC epoch 当北京时间，时间对不上就换会话，结论必错。
- 把同一用户所有会话的提问数相加；题干时间戳只指向一个会话。
- Token 只取 `completion_tokens` 漏 prompt，或把首轮 usage 当第二轮。
- 头像数字是图像内容，不能从文件名、URL、账号 ID 推断；必须解码看图。
- `user` 表可能有多个 admin，必须结合 `created_at` 和“首个注册”语义。

