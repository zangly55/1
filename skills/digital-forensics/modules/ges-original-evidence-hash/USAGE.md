# 原始检材哈希 Skill 使用说明

本文档面向外部 agent。只有用户明确要求原始检材的 MD5、SHA1、SHA256，或明确要求创建哈希任务时，才执行本流程。一般案件分析、检材导入、批量复制、去重或“检查完整性”的泛化描述都不能自动触发任务；意图不明确时先询问。

当前 CLI 已稳定提供 `ges task ls` 和 `ges task create hash`，且已有测试覆盖。`hash` 任务固定请求 MD5、SHA1、SHA256，不能通过 CLI 只选择其中一种算法。

## 1. 固定案件与目标检材

第一条命令：

```bash
ges status --json
```

记录当前 `cid` 和 GES URL。用当前案件的检材清单确认目标 `eid` 和原始检材完整路径：

```bash
ges evidence ls --offset 0 --limit 0 --json
```

用户按路径指定检材时，必须完整匹配；按 `eid` 指定时仍记录其路径。一次请求可包含多个 `eid`，但每个检材单独查重、创建和跟踪。执行期间若 `ges status --json` 的 `cid` 或 GES URL 改变，立即停止，不能把其他案件的状态或哈希写入本批次。

## 2. 创建前必须查现有任务

对每个目标检材先执行：

```bash
ges task ls --eid <eid> --keyword hash --offset 0 --limit 0 --json
```

读取 `tasks[]` 中 `function` 精确为 `hash` 的行，并记录 `status`、`task_id`、`backend_status` 和 `progress`：

- `queued` 或 `processing`：任务已经存在，只轮询，不创建。
- `completed`：任务已经完成，不创建；转到“读取真实结果”。
- `undo` 且 `task_id` 为空：该检材支持 hash，但尚无历史任务，才允许创建。
- `undo` 且 `task_id` 非空、`backend_status` 为 `failed` 或 `cancel`：这是失败或取消过的历史任务，不是“从未创建”。按失败规则处理，禁止立即重复创建。
- `unknown`：记录原始 `backend_status` 并停止自动操作，交人工确认。
- `tasks` 中没有 `function=hash`：当前检材平台不提供该功能，记录为不支持，不得尝试创建其他功能名。

`--status undo` 会同时包含未创建功能和失败/取消历史，不能单独用它判断是否可创建；必须同时检查 `task_id` 与 `backend_status`。

## 3. 创建与轮询

只有创建前查询确认 `task_id` 为空时才执行：

```bash
ges task create hash --eid <eid> --json
```

成功响应应包含 `task`；记录任务 ID、`eid` 和后端状态。随后只轮询：

```bash
ges task ls --eid <eid> --keyword hash --offset 0 --limit 0 --json
```

不要因响应超时、网络断开或输出不确定而再次创建。先重复 `task ls`：若出现非空 `task_id`，说明创建已生效，继续跟踪该任务。只有再次查询仍显示 `task_id` 为空，才可把首次创建记录为未生效，并在用户请求范围内重试一次。

## 4. 失败与重试

- CLI 非零退出、JSON 解析失败或服务不可用都记为失败，不得当作“无任务”或“无哈希”。恢复连接后先 `ges status --json` 核对案件，再 `task ls` 查重。
- `backend_status=failed` 或 `cancel` 时，记录已有任务 ID、检材 `eid`、完整路径、固定算法集、状态和可见进度。当前 `task ls` 不提供详细失败原因，不得补造错误原因。
- 失败后不自动创建第二个任务。只有用户明确要求重试，并且最新一次 `task ls` 仍确认旧任务为失败/取消，才执行一次新的 `ges task create hash --eid <eid> --json`；创建前后的任务 ID 都要保留。
- 重试响应不确定时仍按“先查现有任务、禁止重复创建”的规则处理。持续失败时停止并报告阻塞，不循环创建。

## 5. 只读原始检材与读取结果

hash 任务参数由 CLI 固定为原始检材类型和三个算法：MD5、SHA1、SHA256。不得写入、重命名、移动或修改 `/evidence_mounts/` 中的任何内容，也不得用本地副本的哈希冒充原始检材哈希。

任务状态为 `completed` 后，动态发现目标 `eid` 对应的检材信息文件：

```bash
ges glob --pattern "**/检材信息/data.csv" --path /case/ --offset 0 --limit 100 --json
ges read <matched_case_evidence_info_path> --offset 0 --limit <line_count>
```

路径必须来自当前案件的实际输出，并与目标 `eid` 对应；不要照搬示例层级。若 glob 的 `next_offset` 非空则继续分页；`source_complete=false` 时缩小到目标检材目录重查。检材信息视图会刷新任务写回的 MD5、SHA1、SHA256 字段。

`completed` 只说明任务完成，不等于三个值都已成功写回。仅报告 `ges read` 实际显示且算法名称对应明确的值。字段缺失、空值、格式异常或读取失败时，写“哈希结果未取得/待复核”，不得从任务 ID、文件名、其他检材或本地计算结果推断。

## 6. 作业记录与报告

每个检材至少记录：

```text
cid, eid, original_evidence_path, requested_algorithms,
task_id, cli_status, backend_status, progress,
create_attempted, retry_of_task_id, result_virtual_path,
md5, sha1, sha256, command_exit_status, limitation
```

`requested_algorithms` 记录用户明确请求的算法；同时注明 CLI hash 任务实际固定执行 MD5/SHA1/SHA256。哈希值保持原样，不改变大小写、不截断。报告必须区分“任务已创建”“任务已完成”和“已从检材信息读取到哈希值”三个事实层级；没有读取到的值不得填写占位哈希或示例值。
