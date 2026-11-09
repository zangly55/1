---
name: ges-case-analysis
description: 当用户需要分析已经打开并解析完成的弘连火眼案件数据时使用，包括案件记录、检材文件、手机应用数据、聊天/通话/交易记录、数据库文件、语义检索，以及计算机检材 BitLocker 分区识别与解密流程。
metadata:
  requires:
    bins: ["ges"]
    skills: ["ges-case-management"]
  cliHelp: "ges --help"
allowed-tools: Bash(ges*)
---

# 弘连火眼案件数据分析

用 `ges` 分析已选择且解析完成的单机版或平台版弘连火眼案件数据。不要用本 skill 创建案件、选择案件或导入检材；这些操作使用 `ges-case-management`。如果用户提出新检材路径，只有该路径与当前案件检材路径完全一致时才继续当前上下文。

遇到 `/case/`、`/evidence_mounts/` 等 GES 虚拟路径时，只能用 `ges` 命令访问（`ges ls/read/grep/glob/copy`），不要把它们当作本地文件系统路径处理。

## 开始前

本 skill 仅处理【已打开且所需检材解析完成】的案件。若当前没有有效案件上下文——`ges status` 失败、报连接拒绝（如 `127.0.0.1:<port>`），或返回上下文为空——**第一步必须切到 `ges-case-management`**：执行 `ges case ls` 列案 → 与用户确认 → `ges case open <case_number>`（单机版会为案件启动后台服务）→ 返回本 skill 重新执行 `ges status`。禁止自行猜测案件、反复重试 `status`、或把启动火眼应用当作恢复案件上下文的手段。

仅当已有有效案件上下文时，读取当前状态：

```bash
ges status
```

如果成功，记录 `status` 返回的当前 `cid`、`GES URL` 和可用路由，再按实际路由继续分析，不要猜测挂载路径。`ges status` 等价于旧命令 `ges context`。

以下是仅有的合法快捷路径：

```bash
# 上游已提供 cid 和 ges_url，或来自 ges case ls 的 ges_url
ges init --cid <cid> --ges-url <ges_url>
ges status

# 用户已提供 cid 或完整案件编号，且明确要求在 analysis 内打开
ges case open <cid|case_number>
ges status
```

仅当上游已明确提供 `cid` 且提供 `ges_url`（或该 URL 来自 `ges case ls`）时，才可执行 `ges init` 后以 `ges status` 校验。仅当用户已提供 `cid` 或完整案件编号且明确要求在本 skill 内打开时，才可执行 `ges case open`，成功后仍须返回 `ges status` 校验。凡需要先查看有哪些案件或让用户选择的场景，一律切到 `ges-case-management`。

`ges status` 报 `127.0.0.1:<port>` 连接拒绝，通常不是火眼应用未启动，而是**没有已打开的案件后台服务**。直接执行 `ges case ls` 查看本机案件（含未打开状态），经用户确认后执行 `ges case open` 启动；单机版案件的 GES 端口由 `case open` 分配或发现，不能靠启动 GoldenEyes 主程序获得。

单机版 `ges case open <case_number>` 会先复用已打开的同编号案件；未打开时才启动案件并自动初始化。平台版会精确选择远程案件并写入用户级上下文，名称重名时必须使用 `cid` 或完整案件编号。平台只提供 URL/token 而没有案件参数时，也必须切到 `ges-case-management` 执行 `ges case ls` 并询问用户，绝不能默认选择第一个案件。不要因为 `status` 失败就重复导入检材；也不要因为案件名、检材名或路径相似就复用旧检材，必须完整路径一致。

## BitLocker 分区识别与解密

`ges task bitlocker` 使用相同的 GES HTTP API，在弘连火眼单机版和平台版中均可执行。

分析计算机检材时，必须先对目标检材执行：

```bash
ges evidence partitions --eid <eid> --json
```

读取输出中每个分区的 `state`，并严格按以下规则处理：

- 只有分区的 `state=encrypted`，且用户明确提供了 BitLocker 恢复密钥时，才尝试解密。`--partition` 必须使用上述分区查询返回的实际分区名或完整路径：

  ```bash
  ges task bitlocker --eid <eid> --partition <实际分区名或完整路径> --password <密钥>
  ```

- 不得根据分区名称、文件系统、盘符或原始 `Encrypted` 数字猜测加密状态；`normal`、`decrypted`、`unknown` 都不得当作待解密分区。
- 用户没有提供恢复密钥时，必须向用户索取；不得猜测或生成密钥。

解密任务提交后，必须复核任务和分区状态：

```bash
ges task ls --eid <eid> --keyword bitlockanalyzer --json
ges evidence partitions --eid <eid> --json
```

先检查 `bitlockanalyzer` 任务，再确认目标分区已经变为 `state=decrypted`。仅单机版会在本地刷新并发现解密卷；确认解密后，单机版再用 `ges ls /evidence_mounts/eid-<eid>/` 获取实际解密卷路径，不得猜测卷名或路径。

## 常用命令

### 查看目录

```bash
ges ls /
ges ls /case/
ges ls /evidence_mounts/
```

### 读取文件

```bash
ges read /case/path/to/data.csv --offset 0 --limit 100
ges read /evidence_mounts/eid-1/path/to/file.txt --offset 0 --limit 100
```

先用较小的 `--limit`，避免输出过大。

读 `/case/` 下可溯源的 `data.csv` / `chat.txt` 时，输出最顶部会多出一行 `〔本文件溯源基址 Goldeneyes://<case_number>/<node_id>〕`。引用记录时只需在该基址后追加 `#<正文行号>`，见下方「溯源引用」。基址行不占行号，正文仍从第 1 行算起。

如果顶部仍是旧格式 `〔本文件溯源句柄 nXXXX〕`，说明 CLI 未能从当前 GES 服务确认案件编号；可以继续分析，但禁止自行补写案件编号或生成溯源链接，也不要为补链接额外执行 `case ls` 或 `evidence ls`。

### 搜索文本

```bash
ges grep "关键词" --path /case/
ges grep "关键词" --path /case/ --start-time "2025-01-01" --end-time "2025-01-31"
ges grep "关键词A|关键词B" --syntax keyword --path /case/
ges grep "1[3-9][0-9]{9}" --syntax regex --path /case/path/from/ls --glob "*.csv"
ges grep --pattern-file ./pattern.txt --syntax regex --path /case/path/from/ls --glob "*.csv"
```

`grep` 默认使用 `--syntax keyword`：在 `/case/` 普通解析数据中按关键词搜索，单个 pattern 内的 `|` 表示 OR。Windows 必须使用 `ges.exe`；遗留的 `ges.cmd` 只兼容普通参数，不支持含 `|`、`&`、`>`、`<` 等元字符的 pattern。`ges.exe` 不会二次解析 argv，但调用它的 shell 仍会先解析命令行，因此 pattern 必须作为一个参数整体引用；包含复杂 shell 字符或多行的 pattern 应写入 UTF-8 文件并通过 `--pattern-file` 原样读取。`/evidence_mounts/` 不支持 keyword，只支持显式的 `--syntax regex`；regex 仅支持 `/case/` 和 `/evidence_mounts/`，应先用 `ls` 或 `glob` 定位到有界路径。`--start-time`/`--end-time` 仅适用于 `/case/` 下的 keyword 搜索。仅 `index_state=current` 且 `index_coverage=covered` 可支撑 keyword 否定性结论；其他状态应按 `coverage_hint` 运行文本索引或改用有界 regex/明确文件物化搜索复核。

普通 `/case/` 索引 keyword 搜索默认每页 50 条、单页最多 200 条。`--offset` 是整个命中集合的全局偏移，可以超过 200；按 JSON 返回的 `next_offset` 继续即可读取后续页。该模式下 `--limit 0` 表示使用单页最大值 200，不表示无限返回。regex、API 虚拟 CSV keyword 和 workspace grep 仍受各自的物化/后端预算约束。

### 构建索引

弘连火眼单机版的 keyword 结果返回 `index_state=not_created` 或 `stale` 时，先查看原始状态并按提示构建：

```bash
ges index status --json
ges index build --wait
ges index build --documents --wait
```

`ges index build` 默认创建或更新 `/case/` 基础搜索索引；需要检索 PDF、Word 等文档内容时加 `--documents`，命令会为 `needRunEids` 创建 `documentindexV2` 任务。`isCreated=true` 是文本索引任务完成后的结果，不是创建任务的前置条件。只处理指定待运行检材时可重复传 `--eid <eid>`，但 `--eid` 必须与 `--documents` 同用，不能限制案件级基础索引。`index_state=building` 时等待已有任务，不要重复创建。构建完成后再次执行 `ges index status --json`，确认状态收敛，再重试 keyword grep。平台版尚未验证这些索引创建接口，不得绕过 CLI 限制直接调用。

### 查找文件

```bash
ges glob -p "**/*.db" --path /evidence_mounts/
ges glob -p "**/*.csv" --path /case/
```

必须传 `-p`/`--pattern`，并尽量用 `--path` 缩小范围。模式相对 `--path` 匹配：`*.db` 只匹配当前目录的直接子文件，`**/*.db` 才会递归匹配任意层级。

### ls、grep、glob 的 JSON 返回契约

成功和空结果都使用分页 envelope。集合键固定为：`ls` 使用 `entries`，`grep` 和 `glob` 使用 `matches`；`glob` **不返回 `files`**。三者共有 `offset`、`limit`、`returned`、`total`、`next_offset`、`source_complete`、`truncation_reason`。

`ls --json` 最小成功结果：

```json
{
  "entries": [{"path": "/case/检材/", "is_dir": true}],
  "offset": 0,
  "limit": 100,
  "returned": 1,
  "total": 1,
  "next_offset": null,
  "source_complete": true,
  "truncation_reason": null
}
```

`glob --json` 最小成功结果：

```json
{
  "matches": [{"path": "/case/检材/应用/data.csv", "is_dir": false}],
  "offset": 0,
  "limit": 100,
  "returned": 1,
  "total": 1,
  "next_offset": null,
  "source_complete": true,
  "truncation_reason": null
}
```

`grep --json` 最小成功结果：

```json
{
  "matches": [{"path": "/case/检材/应用/data.csv", "line": 2, "text": "命中内容", "handle": "n4821"}],
  "offset": 0,
  "limit": 50,
  "returned": 1,
  "total": 1,
  "next_offset": null,
  "source_complete": true,
  "truncation_reason": null,
  "engine": "ges-indexsearch",
  "index_coverage": "covered",
  "index_state": "current",
  "index_status": 5,
  "index_is_created": true,
  "index_pending_eids": null
}
```

空结果仍保留集合键和分页字段，例如 `glob --json`：

```json
{
  "matches": [],
  "offset": 0,
  "limit": 100,
  "returned": 0,
  "total": 0,
  "next_offset": null,
  "source_complete": true,
  "truncation_reason": null
}
```

`ls` 空结果同样返回 `entries: []`；`grep` 空结果返回 `matches: []`。keyword grep 还会返回 `engine`、`index_coverage`、`index_state` 及可用的原始索引状态字段；非 current 时带 `coverage_hint`，不得把这种 0 命中解释为确定不存在。

错误时退出码非零，返回独立错误 envelope，不含 `entries`、`matches` 或分页字段：

```json
{
  "code": "not_found",
  "operation": "glob",
  "message": "Path not found",
  "recovery": "请用 ls 或 glob 核对路径后重试。"
}
```

`operation` 对应 `ls`、`grep` 或 `glob`。目录/文件条目的必有字段是 `path`、`is_dir`，后端已知大小时还会有 `size`；grep 命中的标准字段是 `path`、`line`、`text`，普通 `/case/` 叶子可定位时还会有 `handle`。`total` 在来源完整时是总数，无法证明总数时为 `null`；只有 `next_offset` 为 `null` 且 `source_complete` 为 `true` 才表示当前范围完整。

### 复制到本地分析

```bash
ges copy /case/path/to/data.csv
ges copy /evidence_mounts/eid-1/path/to/app.db
ges copy /evidence_mounts/eid-1/path/to/databases/ --recursive
ges copy "/evidence_mounts/eid-1/分区4(恢复的文件)/" --recursive --glob "**/*.xls" --glob "**/*.xlsx" --dest ./recovered --max-files 1000 --skip-existing --manifest ./recovered-copy.jsonl --async
ges job status <job-id> --json
```

需要用 pandas、sqlite3 或其他本地工具分析时，先 `ges copy`。复制 SQLite 数据库时，同名 `-wal`、`-shm` 会一并复制。

目录复制规则：

- 路径包含中文、空格、括号或其他 shell 特殊字符时，必须用引号包住完整路径。
- 复制目录必须传 `--recursive`；只复制部分文件时重复传 `--glob`。`--include` 是完全等价的兼容别名。
- 递归筛选推荐使用 `**/*.xlsx` 这类明确模式。不含 `/` 的模式会匹配任意层级的文件名，含 `/` 的模式匹配相对源目录的路径，匹配不区分大小写。
- 文件数超过默认 200 时，根据已确认的目录规模显式提高 `--max-files`；总大小超过默认 256 MiB 时再提高 `--max-total-bytes`。
- 批量复制应使用一条 `ges copy ... --recursive`，不要先列出文件再逐个循环调用 `ges copy`。
- 长时间批量复制必须加 `--async`，命令会立即返回 `job_id`；之后用 `ges job status <job-id> --json` 轮询，不要重复提交同一个复制命令。
- `queued/running/cancelling` 表示尚未结束；`completed` 且 `result_current` 不是 `false` 后再处理目标目录；`result_current=false` 表示目标后来被其他复制覆盖，旧结果不可再信任；`failed/cancelled/interrupted` 时读取 `error`，不要把部分文件当作完整结果。
- 相同参数的活动任务会返回同一 `job_id`；同一目标目录或其父子目录已被其他任务锁定时，应继续轮询原任务或更换目标，不能绕过锁并发写入。
- 相同参数已完成的任务也会返回原 `job_id`，避免响应丢失导致重复复制；只有用户明确要求重新执行时才加 `--force-new-job`。
- 长时间批量复制应指定 `--manifest <path>.jsonl`。中断后用相同 `--dest` 加 `--skip-existing` 重新提交；`--skip-existing` 与 `--overwrite` 不能同时使用。
- 用户要求停止时运行 `ges job cancel <job-id> --json`，再轮询到 `cancelled`。取消在当前文件下载返回后生效。
- 命令失败时 `ges` 返回非零退出码并把错误写入 stderr；不要把失败当作空结果继续处理。

### 语义搜索

```bash
ges search "转账记录" --max-results 10
ges search "potato 聊天" --timerange 2025-05 --max-results 10
```

返回路径是当前可用的 `/case/...` 路径。需要展开结果时再 `ges read` 或 `ges copy`。

## 路径规则

- `/case/`：已解析案件记录，例如聊天、通话、账号、交易、应用提取结果；检材节点下可能有 `图片分类/{分类名}/data.csv`、`实体分类/{分类名}/data.csv` 和 `检材信息/data.csv`，分别用于查看图片分析、实体聚合结果，以及检材元数据和任务写回的 hash 结果。
- `/evidence_mounts/`：原始检材挂载文件系统，用于查找 `/case/` 未覆盖的数据库、缓存、应用目录和文件。
- `/case/` 不是本地物理目录；`/evidence_mounts/` 也不要绕过 `ges` 直接猜路径。

## 溯源引用

回答里凡是引用 `/case/` 记录的地方，都要在该处紧跟一个角标，让用户能跳回原始记录：

```text
[[N]](Goldeneyes://<case_number>/<node_id>#<行号>)
```

`N` 从 1 递增，像论文引用。必须使用双层方括号的 Markdown 源格式 `[[N]](.)`，使渲染后的可点击链接文字仍显示为 `[N]`；不要写成 `[N](.)`，否则渲染后只会显示 `N`。正文里【只出现带方括号的可点击角标 `[N]`】，不要写 `/case/` 路径、不要写句柄。

### 溯源基址和行号从哪来

溯源基址和行号都来自 `ges read`：

```text
$ ges read <某个 /case/ 下的 data.csv 或 chat.txt>
〔本文件溯源基址 Goldeneyes://20260805123456A/4821〕
     1  字段,值               ← 表头行，不要引用
     2  真实姓名,张三          ← 行号 2
```

回答：

```text
该检材持有人姓名是张三[[1]](Goldeneyes://20260805123456A/4821#2)。
```

直接复制 `read` 顶部的完整基址，再追加 `#2`。不要拆分、改写、猜测其中的案件编号或节点编号；行号使用 `read` 输出左侧那一列。

> ⚠️ **本节所有示例里的路径、案件编号（20260805123456A）、句柄数字（4821 / 6307）、姓名、行号全部是占位符，只用来示意格式，不是真实值。**
> 案件的目录结构因检材、应用、账号而异，**没有固定路径**——实际路径必须用 `ges ls` / `ges glob` / `ges search` 逐层看出来，
> 实际溯源基址必须来自你自己 `read` 时顶部的真实值。**绝不能照搬示例里的路径、案件编号或数字。**

### 铁律

1. **必须使用 `read` 返回的完整溯源基址。** 没 `read` 过不许标；顶部没有 `Goldeneyes://<case_number>/<node_id>` 基址也不许标。绝不能凭 `ls` / `grep` / `search` 的路径、旧 `nXXXX` 句柄或记忆补造基址。
2. **只对 `/case/` 打角标。** `/evidence_mounts/` 的原始检材文件、`ges copy` 到本地的文件都没有句柄，标了会悬空。
3. **只指向具体记录行。** 不要标 `data.csv` 的表头行（第 1 行），不要标 `chat.txt` 的 `[摘要]` 行（有摘要时正文从第 2 行起）。
4. **一段连续记录只标首行、只给一个角标。** 正文用一句话概括整段，绝不逐行逐笔标。
5. **一个溯源基址只对应一个案件中的一个文件。** 换文件或切换案件后必须重新 `read`，使用新输出的基址。

### 正例与反例

```text
✅ 他从 2025-11-21 到 2026-01-13 共 78 笔彩票投注，每日约 4 元[[1]](Goldeneyes://20260805123456A/6307#2)
   （78 笔连续记录概括成一句话，只标首行一个角标）

❌ 他有投注记录[1](Goldeneyes://20260805123456A/6307#2)
   （只用一层方括号，渲染后只显示 `1`，没有可见的 `[1]`）
❌ 投注[[1]](Goldeneyes://20260805123456A/6307#2)、[[2]](Goldeneyes://20260805123456A/6307#3)……[[78]](Goldeneyes://20260805123456A/6307#79)
   （逐笔标，正文被角标刷屏）
❌ 姓名是张三[[1]](Goldeneyes://6307#2)                         （缺 case_number）
❌ 姓名是张三[[1]](Goldeneyes://40/6307#2)                      （用内部 cid 代替了 case_number）
❌ 姓名是张三[[1]](Goldeneyes://20260805123456A/6307)           （缺 #行号）
❌ 姓名是张三[[1]](Goldeneyes://20260805123456A/6307#1)         （标到了 data.csv 的表头行）
❌ 姓名是张三[[1]](/case/…/data.csv#2)                          （正文写路径，不是案件级句柄）
```

## 工作流

```bash
ges status
ges ls /case/
ges grep "关键词" --path /case/
ges read /case/path/from/result/data.csv --offset 0 --limit 100
ges copy /case/path/from/result/data.csv
```

`grep` 只能定位到文件和记录行。要引用命中的记录，仍需对该文件 `read` 一次，复制顶部完整溯源基址并追加命中记录的正文行号。

如果 `ges status` 显示没有可用数据，或用户要求新增检材，切换到 `ges-case-management`。

## 排障

- 缺少上下文：有案件编号就 `ges case open <case_number>`；有 `cid/ges_url` 就 `ges init --cid <cid> --ges-url <ges_url>`；都没有时切到 `ges-case-management`。
- 缺少完整溯源基址：可以继续分析但不要生成角标；不要用 `case ls`、`evidence ls`、`cid` 或旧 `nXXXX` 句柄手工拼接。先确认 `ges status` 正常；上下文失效时切到 `ges-case-management` 重新打开或初始化案件。
- 输出过大：使用 `--path`、`--glob`、`--timerange`、`--limit`、`--max-results` 缩小范围。
- `/evidence_mounts/` 为空：查看 `ges status` 中被跳过的挂载项。
- 不确定语法：运行 `ges --help` 或 `ges <command> --help`。
