# 弘连火眼案件批处理 Skill 使用说明

本文档是外部 agent 可执行的 `ges` CLI 契约。该 skill 只处理同一已选择且所需检材解析完成的案件，适合跨多个检材和动态 GES 路径进行发现、复制、关联、聚合、去重及派生分析。选择案件、导入检材和等待解析使用 `ges-case-management`；单文件或少量交互分析使用 `ges-case-analysis`。

## 1. 固定单案件边界

第一条命令必须是：

```bash
ges status --json
```

记录返回的 `cid`、`ges_url`、`evidence_mounts[].eid`、`evidence_mounts[].route` 和 `skipped_evidence_mounts`。再检查检材解析状态：

```bash
ges evidence ls --offset 0 --limit 0 --json
```

- 批次 manifest 只能有一个 `cid`；每条候选必须能映射到该案件中的一个 `eid`。
- 路径来自本次 `status`、`ls`、`glob` 或 `grep` 输出，不固定写死检材名和层级。原始检材路由使用实际的 `/evidence_mounts/eid-<eid>/`；`/case/` 下同样按实际目录发现。
- `skipped_evidence_mounts`、未完成解析或状态不明的检材不进入“完整批次”。可以排除后继续，但必须在批次 manifest 记录未覆盖范围。
- 批处理期间不得执行 `ges case open` 或 `ges init`。长批次的每个复制阶段前再次执行 `ges status --json`；若 `cid` 或 GES URL 与批次快照不一致，立即停止，不能混合两案结果。

## 2. JSON 发现与分页

只用真实 CLI 命令发现候选：

```bash
ges ls <virtual_directory> --offset <offset> --limit <page_size> --json
ges glob --pattern <glob_pattern> --path <virtual_directory> --offset <offset> --limit <page_size> --json
ges grep <pattern> --syntax keyword --path <virtual_directory> --glob <file_glob> --offset <offset> --limit <page_size> --json
ges grep <regex> --syntax regex --path <bounded_virtual_directory> --glob <file_glob> --offset <offset> --limit <page_size> --json
ges grep --pattern-file <utf8_file> --syntax regex --path <bounded_virtual_directory> --glob <file_glob> --offset <offset> --limit <page_size> --json
```

`--syntax keyword` 是关键词模式：在 `/case/` 普通解析数据中，单个 pattern 内的 `|` 表示 OR。Windows 必须使用 `ges.exe`；遗留的 `ges.cmd` 只兼容普通参数，不支持含 `|`、`&`、`>`、`<` 等元字符的 pattern。`ges.exe` 不会二次解析 argv，但调用它的 shell 仍会先解析命令行，因此 pattern 必须作为一个参数整体引用；复杂 shell 字符或多行 pattern 可写入 UTF-8 文件并通过 `--pattern-file` 原样读取。`/evidence_mounts/` 不支持 keyword，会返回 `evidence_keyword_unsupported`。`--syntax regex` 才解释为正则，只支持 `/case/` 和 `/evidence_mounts/`，应先用具体路径和 glob 收敛范围。`--start-time`/`--end-time` 仅适用于 `/case/` 的 keyword 搜索。

`ls` JSON 的数组键是 `entries`；`glob`/`grep` 是 `matches`。三者都有 `offset`、`limit`、`returned`、`total`、`next_offset`、`source_complete` 和 `truncation_reason`。分页规则：

1. 从 `offset=0` 开始，保留完全相同的命令参数。
2. `next_offset` 非空时，把它原样用于下一页；不要用本地猜测的页码替代。
3. 只有 `next_offset=null` 且 `source_complete=true` 才能把当前范围视为枚举完成。
4. `source_complete=false` 表示达到后端预算、物化上限或超时，即使已有匹配也只是部分结果。缩小 `--path`、`--glob`、关键词或时间范围后从 `offset=0` 重查，并在 manifest 保留被截断范围。
5. 命令非零退出或 JSON 含 `error` 是失败，不是零候选；不得据此写“未发现”。

普通 `/case/` 索引 keyword 搜索默认每页 50 条、单页最多 200 条，`offset` 可以超过 200；此模式下 `--limit 0` 表示单页最大值 200。其他 grep 模式的 `--limit 0` 可请求全部已经生成的结果，但不会把 `source_complete=false` 变成完整结果。大范围仍应分页和分区查询。

## 3. 批次 manifest

在复制或派生前，由调用方维护一个独立的批次 manifest（JSON 或 JSONL）。这是审计工件，不是新的 `ges` 命令。每条来源至少记录：

```text
batch_id, cid, eid, source_virtual_path, source_record_or_line,
discovery_command, discovery_page_offset, source_complete,
selection_reason, copy_job_id, copy_manifest_path, copy_status,
result_current, derived_output, error
```

`source_record_or_line` 对记录型来源保存 `ges grep` 命中行或随后 `ges read` 核实的正文行；对只有文件级坐标的来源明确写 `file`，不得伪造行号。命令参数中的认证信息必须脱敏。

`ges copy --manifest <path>` 生成的是逐文件复制 JSONL，字段包括 `source_path`、`destination_path`、`size`、`status`、`error`。它不能替代上述包含 `batch_id/cid/eid` 的批次 manifest；批次 manifest 应引用它的路径和对应作业 ID。

## 4. 批量复制

复制单文件：

```bash
ges copy <source_virtual_path> --dest <local_target>
```

复制目录和筛选后的文件集：

```bash
ges copy <source_virtual_directory> --recursive --glob <include_pattern> --glob <include_pattern> --dest <local_target_directory> --max-files <confirmed_file_limit> --max-total-bytes <confirmed_byte_limit> --manifest <copy_manifest.jsonl> --async
```

- 目录必须加 `--recursive`；`--glob` 可重复，`--include` 是别名。复制筛选中，不含 `/` 的模式（如 `*.db`）匹配任意层级的文件名；含 `/` 的模式（如 `**/*.db`）匹配相对源目录的路径。单独执行 `ges glob` 做发现时，只有 `**/` 才递归进入子目录。
- 同一来源范围使用一条递归 copy，不要在循环中逐文件调用。不同 `eid` 或不同来源根分别提交，并在批次 manifest 建立关联。
- 文件数默认上限是 200，总大小默认上限是 256 MiB。只有在发现阶段确认规模后才提高 `--max-files` 或 `--max-total-bytes`。
- 长任务使用 `--async`。同参数活动任务和已完成任务会复用原 `job_id`；只有明确要求重跑时才加 `--force-new-job`。
- 中断续传使用相同 `--dest` 和 `--skip-existing`，并保留原 copy manifest；`--skip-existing` 与 `--overwrite` 互斥。
- SQLite 数据库的同名 `-wal`、`-shm` 会随单库复制处理；批量筛选时仍应核对 copy manifest 中实际复制的文件。

## 5. 作业、目标锁与结果有效性

异步提交返回 JSON，其中包含 `job_id`、`deduplicated`、`poll_command` 和 `cancel_command`。只使用返回的 ID：

```bash
ges job status <job_id> --json
ges job cancel <job_id> --json
```

- `queued`、`running`、`cancelling` 不是终态，继续轮询同一 ID。
- 只有 `completed` 且 `result_current` 不为 `false`，并且 copy manifest 没有失败记录时，才能消费目标目录。
- `failed`、`cancelled`、`interrupted` 必须记录 `error` 和已处理范围；部分文件不能冒充完整结果。
- `result_current=false` 表示该目标后来被其他复制覆盖，旧结果不可用于本批次，应重新发现目标所有者或使用新的独立目标。
- 同一目标目录及其父子目录受目标锁保护。锁冲突时轮询原作业或改用不重叠的目标目录，不得绕过锁并发写入。
- 用户要求停止时先 `job cancel`，再轮询 `job status` 到终态；取消可能要等当前文件下载返回。

任何 `ges` 命令非零退出都必须作为失败进入批次 manifest，不得转成空数组继续聚合。

## 6. 关联、聚合、去重与派生结果

本地处理只针对 `ges copy` 产生的副本，原始 `/evidence_mounts/` 始终只读。派生表的每一行必须保留：

```text
cid
eid
source_virtual_path
source_record_or_line
```

一条派生行由多个来源合并时，以上字段保存为来源列表，不能只保留一个代表值。除此之外记录批次 ID、处理规则或脚本版本、关联键、聚合口径、去重键、保留/丢弃原因和缺失值处理。跨检材相同内容默认只是“候选重复”；除非业务键、时间和内容均满足已声明规则，不得把同名文件、同账号或相似文本直接合并为同一事实。

派生结果本身没有弘连火眼角标，也不能作为新的 `Goldeneyes://` 来源。失败、截断、未解析检材、缺失挂载或未完成复制必须进入覆盖范围说明；不得以部分数据形成全案否定结论。

## 7. 回到原记录生成角标

对最终结论引用的每个来源，按批次 manifest 中的 `source_virtual_path` 回到 `/case/` 原文件：

```bash
ges read <case_source_virtual_path> --offset <line_window_start> --limit <line_window_size>
```

核对正文与上下文，从该次输出顶部原样复制完整 `Goldeneyes://<case_number>/<node_id>` 基址，再追加输出左侧的真实正文行号：

```text
[[N]](Goldeneyes://<case_number>/<node_id>#<source_record_or_line>)
```

不得从批次 manifest、派生表、`cid`、路径、`ls`、`glob`、`grep` 或旧句柄拼造基址。`/evidence_mounts/` 文件和本地副本没有弘连火眼角标；若来源只能落到这些文件，清楚标明复核依据和局限性，不伪造链接。
