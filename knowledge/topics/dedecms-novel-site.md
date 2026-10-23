# DedeCMS 小说站数据库取证（章节、采集、评论、支付）

- 条目 ID：KB-TOPIC-DEDECMS-001
- 适用条件：Linux/宝塔服务器上的 DedeCMS（织梦）小说站，需回答某书第 N 章标题、后台采集来源、某条评论所属小说、第三方支付商户密钥。
- 来源：案件 20261021162519O 的 `answer/Q20.json`—`Q23.json`（`verified.json` revision 4）。
- 复核方法：MyISAM 数据文件导出后用同版本 MySQL 只读查询；跨表 ID 语义先确认再 JOIN。

## 一、定位数据库

```text
/www/server/data/<dbname>/dede_archives.MYD
/www/server/data/<dbname>/dede_arctype.MYD
/www/server/data/<dbname>/dede_comment.MYD
/www/server/data/<dbname>/dede_co_note.MYD
/www/server/data/<dbname>/dede_payment.MYD
```

```powershell
ges.exe glob -p "**/dede_archives.MYD" --path "/evidence_mounts/eid-<eid>/" --json
ges.exe copy "/evidence_mounts/eid-<eid>/.../www/server/data/<dbname>/" --recursive --dest "<output>\exports"
```

- MyISAM 表由 `.frm`/`.MYD`/`.MYI` 三件套组成，必须整组复制。
- 本地起同版本 `mysqld --datadir=<copy> --port=<free> --skip-grant-tables` 只读查询；或使用只读 MyISAM 解析器。不要对原检材起服务。

## 二、某书第 N 章标题

```sql
SELECT id,typename,typedir FROM dede_arctype WHERE typename='<书名>';
SELECT id,typeid,title FROM dede_archives
WHERE typeid=<栏目id> ORDER BY id LIMIT 60;
```

- `dede_archives.typeid` → `dede_arctype.id`（书籍栏目）。
- 先按标题中的明确章节号定位，再核对栏目和站内排序；只有确认编号连续、没有卷首或缺章时，才可用第 N 条辅助判断。
- 标题常为“第47章 这波赚嗨了”；题目要章节名时只取空格后的名称，保留原始汉字。

## 三、后台采集来源

```sql
SELECT nid,notename,listconfig FROM dede_co_note;
```

- `listconfig` 里找 `regxurl="http://<host>/<bookid>/"`；同一站点的多个节点（章节/封面）主机应一致。
- 采集规则目录 `cj/Rules/<host>.txt` 可作第二证据。
- 题目要域名时去掉协议与路径，只留主机名（如 `www.example.com`）。

## 四、评论所属小说

```sql
SELECT cid,id,name,comment FROM dede_comment WHERE comment LIKE '%关键词%';
SELECT id,typename FROM dede_arctype WHERE id=<comment.id>;
```

- **`dede_comment.id` 指向 `dede_arctype.id`（书籍栏目），不是 `dede_archives.id`（章节）**；直接按 archives 关联会查错书。
- 评论正文可能带句号/多余空格，按 `LIKE` 命中后核对完整值。

## 五、第三方支付商户密钥

```sql
SELECT code,name,config FROM dede_payment;
```

- `config` 是序列化/文本配置，找 `yp_account`（商户号）、`yp_key`（商户密钥）等字段；密钥可能大小写混合，按原值输出。
- 先按 `name`/`code` 确认是“小说站对接的第三方支付接口”，不要把其他通道的 appid/appsecret 当商户密钥。
- 通用条目只写字段名，不写实际密钥；原值仅保留在题解。

## 证据来源要求

- 数据文件路径 + 复制命令 + 表名 + SQL + 结果行；
- 章节：栏目 id、书名的 `typename/typedir`、章节总数与第 N 条；
- 评论：评论行与 `arctype` 关联行；
- 支付：`dede_payment` 的 code/name 与 config 字段（题解可含密钥，通用条目脱敏）。

## 易错点

- 把 `dede_comment.id` 当章节 id 去 JOIN `dede_archives`，得到错误书名。
- 章节标题带“第47章 ”前缀，答案却要求仅章节名；按题干格式裁剪。
- 采集 `regxurl` 是完整 URL，题目要域名；或反之漏协议。
- 只复制 `.MYD` 漏 `.MYI`/`.frm`，MySQL 无法识表。
- 用 GBK 数据按 UTF-8 读，标题/评论乱码；先确认表字符集。
- 把支付 `yp_account`（商户号）当 `yp_key`（密钥），或把其他通道配置混入。

