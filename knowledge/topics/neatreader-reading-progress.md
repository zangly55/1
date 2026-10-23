# NeatReader 阅读进度与当前章节定位

- 条目 ID：KB-TOPIC-NEATREADER-001
- 来源：本案 verified Q24、Q25（`answer/Q24.json`、`answer/Q25.json`，P06 分析并经 GPT 复核）。
- 适用条件：Windows 上 NeatReader 的书库/阅读进度取证，需回答“正在读哪本”“读到第几章”。

## 关键路径

```text
%APPDATA%\NeatReader\bookData\<book-guid>\<书名>.txt
%APPDATA%\NeatReader\bookData\<book-guid>\paginationInfo
%APPDATA%\NeatReader\IndexedDB\file__0.indexeddb.leveldb\*.log
```

```powershell
ges.exe glob -p "**/NeatReader/bookData/**" --path /evidence_mounts/eid-1/ --json
ges.exe glob -p "**/NeatReader/**/paginationInfo" --path /evidence_mounts/eid-1/ --json
```

## 判定方法

1. “正在阅读的书”：取 `bookData` 中带小说正文与 `paginationInfo` 的目录，并在 IndexedDB 日志里找该书的 `readProgressUpdateTime`，取全库最新者；声明/封面等短文件排除。
2. “当前章节”：IndexedDB 的 `readProgress` 对象里 `spineIndex` 是 V8 `kInt32` 序列化值，varint 需按 ZigZag 解码（本案 `0x66` → 51）。
3. 用同书 `paginationInfo` 的 `position.spineIndex` + `titles` 做显式映射（本案 `spineIndex=51` → `"第五十一章 "`，52 → 第五十二章），再用小说正文的章标题交叉核对。
4. 书名/章节标题要清洗全角空格、引号、作者后缀；正文常见 GB18030 编码。

## 证据来源

- 本书目录唯一小说《小年小月》，`readProgressUpdateTime=2025-10-23T03:41:55Z` 为全库最新。
- `paginationInfo` 的 `titles` 显式给出 `spineIndex=51 → 第五十一章`。
- 正文 TXT（GB18030）第 51 个章标题为“第五十一章”。

## 易错点

- `paginationInfo` 的 `scrollBarNaviData` 是滚动条采样导航，存在同一章多次采样、跳章，不能当纯章节起点。
- `spineIndex` 不能统一假设 0-based 或 1-based：本书早期 index 0 对应第一章，后期字段与 `titles` 为 1-based；必须用同书 `titles`/正文核对。
- LevelDB 是二进制日志，`grep` 只能定位；要按 V8 序列化格式解析，别把 `0x66` 当十进制 102。
- “书架里有”≠“正在读”；以最新 `readProgressUpdateTime` 为准。
- 初版把 `spineIndex=51` 直接 +1 成第 52 章，后经 `titles` 纠正为第五十一章；+1 假设必须复核。
