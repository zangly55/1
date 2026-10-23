# 电子书阅读痕迹与创作/函件取证检查点

- 条目 ID：KB-TOPIC-READER-001
- 状态：通用方法（本案实例待 `verified.json` 确认后补入）
- 适用条件：需要确认嫌疑人正在阅读的小说/章节、自己创作小说的章节标题，或侵权赔偿/致歉期限等函件内容。

## 一、阅读器“当前阅读”痕迹

重点找阅读器的最近文件、阅读进度、书签与配置（不同阅读器字段名不同）：

```text
%APPDATA%\<阅读器>\config.json / recent.json / bookshelf.json
%LOCALAPPDATA%\<阅读器>\Cache / Local Storage / IndexedDB
HKCU\Software\<阅读器>\RecentFiles / MRU
```

```powershell
ges.exe glob -p "**/*.json" --path "/evidence_mounts/eid-<eid>/Users/<user>/AppData/Roaming/" --json
ges.exe grep "lastChapter|chapterIndex|readingProgress|bookName|novelName" --syntax regex --path "/evidence_mounts/eid-<eid>/Users/<user>/AppData/" --glob "*.json" --json
```

- “正在阅读”优先取最近一次打开/最后写入的进度字段，而不是书架里排第一的书。
- 章节常见 0 基/1 基索引，题目要求“第几章”时确认换算（`index=0` → 第一章）。

## 二、创作小说章节标题

```powershell
ges.exe glob -p "**/*.docx" --path "/evidence_mounts/eid-<eid>/Users/<user>/Documents/" --json
ges.exe glob -p "**/*.txt" --path "/evidence_mounts/eid-<eid>/Users/<user>/Documents/" --json
```

- `.docx` 解压后读 `word/document.xml`；标题可能是 Heading 样式或独立段落。
- 多个版本时按修改时间与内容完整度取最终稿，并保留版本差异说明。

## 三、赔偿金额与致歉期限

```powershell
ges.exe grep "赔偿|致歉|道歉|万元|限期" --path /case/ --json
ges.exe glob -p "**/*.eml" --path "/evidence_mounts/eid-<eid>/Users/" --json
ges.exe glob -p "**/*.pdf" --path "/evidence_mounts/eid-<eid>/Users/<user>/Documents/" --json
```

- 金额只取“万元”前的数字；注意“人民币 12 万元”“赔偿 120,000 元”的换算。
- 期限题按函件原文日期写“X月X日”，不要按收件时间或当前时间推算。
- 邮件/聊天/文档多源冲突时，以正式函件原文为准，并注明来源文件与行号。

## 证据来源要求

- 阅读进度：阅读器配置/数据库 + 文件最近访问时间或书签，两条互证。
- 章节标题：文档正文 + 文档属性/版本记录。
- 函件：原文文件 + 邮件头/聊天记录（如有）。

## 易错点

- 把“书架中的书”当“正在阅读”；要看进度/最后打开时间。
- 阅读器把章节存成 0 基索引，直接照抄会差一章。
- 小说正文里的“赔偿/致歉”是剧情内容，不是现实函件；要区分小说文本与真实邮件/文档。
- `.docx`/`.pdf` 的正文可能被拆成多段，`grep` 命中后仍需 `read` 或解包确认上下文。
