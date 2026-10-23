# ESXi 主机安装时间取证

- 条目 ID：KB-TOPIC-ESXI-001
- 适用条件：检材为 ESXi 主机系统盘/整机镜像（E01），已由队长在火眼打开并解析；需回答 ESXi 安装时间。按虚拟机数据存储内的 ISO/VMX 回答镜像题的思路见车辆/虚拟化类条目，ISO 大小需另行确认字节口径。
- 来源：[案件Q01当前记录](C:/Users/35124/Documents/取证/ESXi-20261021/answer/Q01.json)，2026-10-21复核，revision 3，状态needs_review；无实际判题反馈。
- 复核方法：原始 `esx.conf`、解析字段、字段时区语义与有明确时区的事件记录交叉核对；证据数量不替代字段语义。

## 一、定位安装记录

```powershell
ges.exe --cid <cid> --ges-url <url> status --json
ges.exe --cid <cid> --ges-url <url> ls /evidence_mounts/ --json
ges.exe --cid <cid> --ges-url <url> ls "/evidence_mounts/eid-<eid>/" --json
```

- 找 `BOOTBANK1/`（或 `BOOTBANK2/`）与 VMFS 数据存储分区；不要按分区号猜。
- 导出引导分区状态包：

```powershell
ges.exe --cid <cid> --ges-url <url> copy "/evidence_mounts/eid-<eid>/<检材>/BOOTBANK1/state.tgz" --dest "<output>\exports"
tar -xzf state.tgz
tar -xzf local.tgz
Select-String -Path "state\local\etc\vmware\esx.conf" -Pattern '^/system/'
```

- 关键字段：`/system/inception = "YYYY-MM-DDTHH:MM:SS"`，表示主机安装/初始配置时间，**原始值不带时区**。
- 同时记录 `/system/uuid`，用于证明 `/case/` 解析记录与原始主机是同一台。

## 二、交叉核对时区与北京时间候选

按实际可用记录交叉检查时间线，说明各记录是否独立：

```text
state/local/etc/vmware/.backup.counter   # CREATED: ... UTC 2025
/var/log/vmksummary.log                  # 首行 bootstop: Host has booted（带 Z）
/var/log/hostd.log                       # 首条启动时间（带 Z）
VMFS 创建/写盘时间
```

- `.backup.counter` 的 `CREATED` 与 `state.tgz` 的 mtime、首启日志能串成连续时间线；`Z`/`UTC` 明确者作为时区基准。
- 若 `inception` 与这些 UTC 时刻只差几分钟，时间线支持按UTC解释的推断，但相邻并不自动证明该字段时区。先记录字段语义及冲突；仅在按UTC解释的条件下，北京时间 = UTC + 8 小时。

## 三、本案实测值

```text
/system/uuid      = 68f5d65a-90b0-41f0-3925-000c29d8f032
/system/inception = 2025-10-20T06:28:08        (原值无时区)
.backup.counter   = Mon Oct 20 06:34:23 UTC 2025
vmksummary.log    = 2025-10-20T06:34:33Z bootstop: Host has booted
VMFS              = 2025-10-20 06:33:07Z
→ 按UTC解释的北京时间候选：20251020-142808
```

## 证据来源要求

本案GES解析值为 `2025-10-20 06:28:08 +0800 CST`，用户提供WP文字采用 `20251020-062808`；相关服务器截图未成功取得。当前保留两个候选，缺少更直接的字段时区语义或安装记录，不能声称已证明解析器实现错误。旧条目由“时间相邻”直接断言UTC的推论已撤回。

- `esx.conf` 原始 `/system/inception` 行 + 文件路径；
- 明确带时区的旁证及其事件语义（`.backup.counter`、`vmksummary.log`/`hostd.log`、VMFS）；相邻时间本身不能解决字段时区歧义；
- `/case/` 的 `ESXI配置/data.csv` 只作 UUID 交叉印证，其附加时区标注不能覆盖原始文件。

## 易错点

- GES `/case/` 的时区标注与原值需分开记录；本案两种解释相差8小时，不能直接照抄解析值，也不能未经证明直接认定它错了。
- `state.tgz` 是两层压缩（`state.tgz` → `local.tgz`），只解一层拿不到 `esx.conf`。
- 两个 BOOTBANK 的配置可能不同；以实际安装/启动的 bootbank 为准。
- 只看首启日志会得到“首次启动时间”，不是安装写入时间；两者可差数分钟，题目问安装时间应取 `inception` 并用首启做旁证。
- 时间格式必须严格按题干 `YYYYMMDD-HHMMSS`，不要带时区后缀。


