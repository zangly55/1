---
name: ges-original-evidence-hash
description: 只有用户明确请求对原始检材执行 MD5、SHA1、SHA256 校验或明确要求哈希任务时使用；不因一般案件分析、导入或批处理而自动创建哈希任务。
metadata:
  requires:
    bins: ["ges"]
  cliHelp: "ges --help"
allowed-tools: Bash(ges*)
---

# 原始检材哈希任务

本 skill 仅响应用户明确提出的原始检材 MD5、SHA1、SHA256 或哈希任务请求。先用 `ges status --json` 固定案件，再对每个目标 `eid` 执行 `ges task ls --eid <eid> --keyword hash --json`；已有、排队、处理中或已完成的 hash 任务一律不得重复创建。

确认目标检材尚无任务后，唯一可创建的真实命令是 `ges task create hash --eid <eid> --json`。该任务固定计算 MD5、SHA1 和 SHA256，原始检材保持只读。完成后从当前检材动态路径下的 `检材信息/data.csv` 执行 `ges read` 核验实际返回值；任务成功不等于可以猜测或伪造哈希。

状态判定、失败重试、记录字段和报告规则见同目录 `USAGE.md`。
