# NTFS USN：变长记录、原因位与日志实例边界

- 整理/检索日期：2026-11-18；整理者：Codex；主题：Windows 文件变更线索与解析防错。
- 来源作者：Microsoft。阅读 [USN_RECORD_V2](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-usn_record_v2) 的结构、Members、Remarks（页面更新2023-03-13），及 [Using the Change Journal Identifier](https://learn.microsoft.com/en-us/windows/win32/fileio/using-the-change-journal-identifier) 正文（更新2021-01-07）。
- 适用范围：本卡结构解析仅针对 V2；不是 V3/V4 通用解析器，不以 Windows 大版本推定记录版本。没有比赛题号或案件检材。
- 状态：官方文档核对＋手工字节样例验证；未读取本机卷日志、未采集或复验原始检材。

## 文档核对要点

V2 是变长记录：按 RecordLength 前进；文件名按 FileNameOffset 和以字节计的 FileNameLength 读取，不能依赖末尾零。先识别版本。Reason 为累计原因位，CLOSE 可与其他原因并存；改名关联旧名与新名记录。TimeStamp 表达记录的 UTC FILETIME。来源：[V2 文档](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-usn_record_v2)。

日志标识用于区分日志实例。删除重建与只更换标识对 USN 的影响不同；关联读取需要同时考虑标识和 USN。不能把不同实例的相近 USN 当成同一历史位置。来源：[日志标识文档](https://learn.microsoft.com/en-us/windows/win32/fileio/using-the-change-journal-identifier)。

## 可复用核查路径

1. 记录当前检材、卷、日志来源/提取方式与解析器版本。只有原材料支持时登记日志实例标识；缺失就写未知，不能由单条 V2 记录臆造该值。
2. 保存每条记录的来源字节偏移、RecordLength、版本、文件/父目录引用、USN、原始时间及 Reason 数值。边界检查失败单列异常，避免错误步长影响后续记录。
3. 原因位用按位判断；例如检查 RENAME_NEW_NAME 时，同时具有 CLOSE 的记录也应命中，不能只用整个数值相等判断。
4. 改名关系先按同卷、文件引用及时间/USN 上下文关联，检查父目录变化。只有旧名或新名一侧时标注缺口；同名或紧邻记录不足以单独配对。
5. 从父目录引用重建路径时保留依据与时间范围，不把当前目录状态直接当作历史路径。身份归因和实际用户行为仍需其他证据；不将记录数量直接写成用户操作次数。
6. 记录来源不完整时，结论限定于已取得范围；未见记录不能单独证明从未改名或日志被人为清理。

以上为将官方语义用于取证的核查建议，未在案件中执行。

## 本机纯解析验证

在独立学习目录使用 Python 3.14.6 手工构造两个 V2 字节数组，没有调用 Windows 日志接口或运行来源代码。首条含中文文件名且无零终止符；第二条人为将文件名偏移设为64，以检查解析器确实读取偏移字段。这是合成边界测试，不证明真实系统会输出该布局。

六组断言通过：

| 输入 | 实际结果 |
| --- | --- |
| 两条合成记录；组合原因值0x80002000 | 记录起点0、72；两个文件名正确；新名位与关闭位均识别 |
| 末尾截断一字节 | 拒绝：记录边界错误 |
| RecordLength 置零 | 拒绝：记录边界错误 |
| MajorVersion 改为3 | 拒绝：不支持版本 |
| 文件名长度设为奇数 | 拒绝：文件名边界错误 |
| 文件名偏移指向记录末尾 | 拒绝：文件名越界 |

脚本与结果仅留本地20261118学习目录：`usn_probe.py`、`usn_probe_results.json`。测试只覆盖手工 V2.0 帧边界与位掩码，没有验证真实 NTFS 生成行为、时间转换、日志实例变化、改名配对、路径恢复、稀疏区域或损坏记录雕刻。探针不应直接用作案件恢复工具。

关联：[离线字段语义与交叉核验](offline-evidence-semantics.md)。
