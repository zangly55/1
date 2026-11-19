# systemd journal：时间语义与 JSON 导出完整性

- 整理/检索：2026-11-19，Codex。适用：已有 Linux journal 或其导出文件的离线取证。
- 来源作者：systemd 项目。固定阅读 v255 文档，不声称这是最新版本，也未核实本机安装版本；两页未标明独立发布日期。
- [journal-fields v255](https://www.freedesktop.org/software/systemd/man/255/systemd.journal-fields.html)：阅读 Description、User/Trusted Journal Fields 和 Address Fields。
- [journalctl v255](https://www.freedesktop.org/software/systemd/man/255/journalctl.html)：选读来源选项、boot 过滤、JSON/输出字段/完整输出、游标与 verify 条目，未通读所有命令。
- 状态：官方文档交叉核对；未执行 journalctl、未采集日志、未做合成实验或原始检材复验。

## 字段语义

`__REALTIME_TIMESTAMP` 是 journal 接收记录时的墙钟时间；`_SOURCE_REALTIME_TIMESTAMP` 是可知且不同于接收时间的最早可信消息时间，单位均为 UTC 纪元微秒。`__MONOTONIC_TIMESTAMP` 应结合 `_BOOT_ID` 使用。双下划线字段属于导出时的地址元数据。`__CURSOR` 是不透明定位值。下划线可信字段由 journal 添加；这种字段来源约束不等于证明整份文件从未被篡改。依据：[字段文档](https://www.freedesktop.org/software/systemd/man/255/systemd.journal-fields.html)。

## JSON 输出陷阱

v255 的 `-o json` 按记录输出 JSON；超过4096字节的字段默认成为 null，可用 `--all` 解除该限制。重复字段表示为数组；不可打印或非 UTF-8 字段可表示为数字字节数组。`--verify` 检查内部一致性；真实性验证还涉及启用 FSS 及匹配验证密钥。依据：[journalctl 文档](https://www.freedesktop.org/software/systemd/man/255/journalctl.html)。

## 后续取证的核查步骤

以下为方法建议，本次未在案件中执行：

1. 登记检材完整路径、原始日志与导出文件的对应关系、systemd/导出工具版本及完整参数。使用工作副本；通过明确的文件或目录参数限定输入，防止混入分析机日志。
2. 保留原始微秒值、源时间、接收时间、boot ID、机器来源及游标。先分主机/启动上下文，再比较单调时间；跨启动的单调数值不能直接排序成全局时间线。墙钟异常须保留冲突，不擅自校正。
3. 用接收时间回答“何时收到记录”，不要自动改写成“用户何时完成操作”。源时间缺失时明确证据缺口；业务行为需关联应用响应、状态或其他独立痕迹。
4. 发现 JSON 的 null，先检查导出限制，不能直接断言原日志为空或已被删除。消费者保留字符串、数组、字节数组和缺失字段的区别，不盲目全部转字符串。
5. 导出范围、过滤条件和条目数需可追溯；必要时在可控副本比较完整输出。保留游标原值，不根据其内部文本格式自创定位规则。仅展示 MESSAGE 的摘录不足以替代完整来源。
6. 一致性检查通过、日志来源可靠、具体业务事实得到证实分别报告；不能以工具成功退出代替真实性结论。

本卡未验证不同发行版补丁、损坏 journal、FSS、时钟回拨或大字段导出行为。后续实际任务先按对应版本重新核对。关联：[Linux Samba 与面板日志](linux-samba-and-panel-logs.md)、[离线字段语义](offline-evidence-semantics.md)。
