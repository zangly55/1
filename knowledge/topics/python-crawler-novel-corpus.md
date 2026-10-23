# Python 爬虫与小说语料取证检查点

- 条目 ID：KB-TOPIC-CRAWLER-001
- 状态：通用方法（本案实例待 `verified.json` 确认后补入）
- 适用条件：需要从 Windows 镜像中定位爬虫代码、目标站点、小说数据库，统计缺失章节、汉字数量与文本替换情况。

## 一、定位爬虫代码与站点

```powershell
ges.exe glob -p "**/*.py" --path "/evidence_mounts/eid-<eid>/Users/" --json
ges.exe grep "requests|BeautifulSoup|scrapy|urlopen|base_url|novel_id" --syntax regex --path "/evidence_mounts/eid-<eid>/Users/" --glob "*.py" --json
```

- 先找 `novel_id` 常量/字典，再顺藤摸到该 id 对应的 `base_url`/`domain`。
- 站点答案按题目格式补协议与路径（如 `https://www.example.com`），不要把 `www` 或协议丢掉。

## 二、数据库章节完整性

```powershell
ges.exe glob -p "**/*.db" --path "/evidence_mounts/eid-<eid>/Users/" --json
ges.exe copy "/evidence_mounts/eid-<eid>/.../novel.db" --dest "<成员output>\exports"
```

```sql
SELECT name FROM sqlite_master WHERE type='table';
SELECT novel_id, COUNT(*) FROM chapters GROUP BY novel_id;
SELECT chapter_no FROM chapters WHERE novel_id=? ORDER BY chapter_no;
```

“缺失章节”定义要在题内统一，常见两种口径：

1. 以目录/文件应有章节数与数据库实际行数之差；
2. 以章节号序列的断号计数（`max - count` 或逐号比对）。

两种口径结果可能不同，必须用文件清单与数据库双向核对，并在证据里写明采用的口径。

## 三、汉字计数

```python
import re
text = open(path, encoding='utf-8', errors='ignore').read()
n = len(re.findall(r'[\u4e00-\u9fff]', text))
```

- 只统计 CJK 统一表意文字基本区；标点、数字、拉丁字母、空白不计。
- 编码可能是 UTF-8/GBK/UTF-8-BOM；先探测编码，避免整篇按乱码统计。
- 多文件合计时先逐文件计数再求和，避免一次性拼接导致边界/编码问题。

## 四、文本替换比对

```python
orig = open(orig_path, encoding='utf-8').read()
curr = open(curr_path, encoding='utf-8').read()
replaced = [(a, b) for a, b in zip(orig, curr) if a != b and re.match(r'[\u4e00-\u9fff]', a)]
distinct = {a for a, _ in replaced}
```

- 题目问“被替换的不同汉字”按替换前的原字去重；问“数量最多”按文件分别计数后排序。
- “完全没有汉字被替换”即该文件替换对集合为空（允许非汉字差异，如标点/空格，需按题口径）。
- 先对齐文本（等长、同章节），再逐字比较；插入/删除会导致错位，需用序列比对（difflib）而不是简单 zip。

## 证据来源要求

- 爬虫代码：源码文件路径 + `novel_id=3` 附近行号/常量。
- 章节：数据库表、SQL 查询结果、章节文件清单三者互证。
- 汉字/替换：统计脚本、输入文件清单、输出计数；脚本与结果都写入证据。

## 易错点

- 把“字节数”当“汉字数”；UTF-8 一个汉字 3 字节。
- 数据库有 `-wal` 未合并，直接读主库会少最新章节；`ges copy` 会带 `-wal`/`-shm`。
- 章节文件有重复/番外/卷首语，不能只按文件个数算章节。
- 替换统计把标点、字母也算进去，导致“不同汉字”偏大。
- 站点域名在配置/数据库/代码三处可能不一致，以 `novel_id` 对应记录为准并交叉验证。
