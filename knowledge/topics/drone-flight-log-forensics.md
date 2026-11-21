# 无人机赛前取证：日志、媒体与工具选择

整理日期：2026-11-21。面向离线比赛材料，机型未知时先准备 DJI。状态：两份 WP 章节选读＋工具作者文档核对；没有本场无人机检材，没有原始日志复验。本页方法是工作建议，不能直接当作新题答案。

## 先确认对象，再选择解析器

| 实际输入 | 主流程 | 边界 |
| --- | --- | --- |
| DJI 手机/遥控器 TXT | 已有物联网工具初筛，dji-log-parser 解析；CsvView 可辅助查看其支持的格式 | TXT 可能是二进制；记录格式版本。v13+ 帧解密需要适配的 keychain |
| DJI DAT | 先分清机载与移动端、机型及加密，支持时使用 DatCon/CsvView | 扩展名相同不代表格式相同；工具不支持不等于日志损坏 |
| DJI 照片、视频及伴随 SRT | ExifTool、ffprobe、文本查看 | 原媒体、缓存、缩略图、转码副本分别记录；缺字段不等于从未拍摄 |
| ArduPilot 日志 | Mission Planner / MAVExplorer | 飞控 DataFlash 与地面站 Tlog 的来源不同 |
| PX4 ULog | pyulog：ulog_info、ulog2csv | 注意版本、主题、多实例与丢帧；无真实文件暂不准备额外环境 |

DatCon/CsvView 作者列出的加密限制包括 Mavic Air、Mavic 2、Mavic Air 2、Mavic Mini 等机载 DAT；更详细介绍还列出 Mini 2 的移动端 DAT 例外。因此不采用首页较宽泛的“移动端都可解”说法。[支持范围](https://datfile.net/CsvView/intro.html)

dji-log-parser 作者提供 TXT→CSV/KML/GeoJSON，说明 v13+ 获取 keychain 的 API 依赖及缓存后离线使用。作者的兼容性声明不能代替对当前日志成功率的实测。[项目与限制](https://github.com/lvauvillier/dji-log-parser)

## 题意到证据

1. **型号、名称、编号**：分别记录飞机昵称、型号、机身/相机/遥控器/电池编号；不可把昵称当型号或把相机号当机身号。未知型号保留原代码，不猜映射。
2. **时间**：同时保存文件名、日志内部绝对时间、相对飞行秒数和时区。确认内部时间是否 UTC 后才换算；文件结束、断连、电机停转、落地不是同一事件。
3. **地点**：区分飞机 GPS、HomePoint、遥控器/手机位置与媒体坐标；说明经纬顺序、坐标系和定位质量。地图只辅助说明，原值及记录号必须保留。
4. **高度与距离**：先写出字段名、单位、参考面，再计算极值。相对高度与绝对高度、累计路程与离 HomePoint 距离分别统计；不能把配置上限写成实际达到的高度。
5. **次数与时长**：先定义一次飞行的边界，排除同一日志的同步副本、缓存或重导出。录像按实际状态区间计算，不盲信文件头。
6. **来源关联**：按手机/遥控器/机身/卡建立清单，用时间、设备标识和媒体事件关联。支持性字段不足时保留未知。

上述第 2—6 项属于本轮建议的复核步骤，尚未通过本场样本验证。媒体字段名称可对照 [ExifTool 作者 DJI 模块](https://github.com/exiftool/exiftool/blob/master/lib/Image/ExifTool/DJI.pm)：AbsoluteAltitude、RelativeAltitude、云台角度与不同机型字段分别定义，不能把当前版本支持追溯到旧本机版本。

## 最容易误判的“解析成功”

pydjirecord 作者说明 v13+ 无相应解密条件时仍可输出文件头信息；文件头的照片数、录像时间、距离、坐标存在可靠性限制。必须记录是否有解密帧、有效帧数与时间覆盖，不能把“打印摘要”写成“已恢复轨迹”。该项目是 dji-log-parser 的 Python 重写，两者一致也不等于完全独立的算法验证。[作者说明](https://github.com/rembish/pydjirecord)

建议留下：题号、检材路径、文件、日志版本、工具版本、解析模式、行/帧号、原始值、换算方式、结果与未决项。与其他答案冲突时比较对象、时区、字段和覆盖范围；保留有证据的原结论，不能因队员或 WP 不同就自动改答。

## 已读实战与版本

- [2021 美亚杯团体无人机摘记](../cases/2021-meiya-drone-xd-wp-methods.md)：Q50—51、Q77—84 文字选读；手机 TXT、机身 DAT 和手机媒体互补，坐标选项存在作者报告的差异。
- [2026 FIC 初赛 Q20 摘记](../cases/2026-fic-drone-xd-wp-methods.md)：DJI Fly v14 日志摘要与地名反查；仅摘要不证明完整轨迹解密。
- DatCon、CsvView 下载页当日均列 4.3.0（2023-03-19）；两者需要 64 位 Java。[DatCon](https://datfile.net/DatCon/downloads.html)、[CsvView](https://datfile.net/CsvView/downloads.html)
- dji-log-parser Releases/API 当日 latest 为 v0.5.7，发布时间 2025-04-26；Windows 资产名 dji-log-x86_64-pc-windows-msvc.zip。[发布页](https://github.com/lvauvillier/dji-log-parser/releases)
- [ArduPilot 日志来源与工具](https://ardupilot.org/planner/docs/common-logs.html)、[PX4 pyulog](https://github.com/PX4/pyulog)：本轮只读相关日志分类与转换文档，未安装或实测。

## 使用限制与后续

比赛只给镜像/日志时不需要为分析而连接真机；DJI Assistant 2 属于按机型选择的实物导出流程，等实际对象出现再决定。先在允许联网的准备阶段确认工具及离线依赖，比赛是否允许联网以当场规则为准；不擅自把日志上传第三方站点，也不将 API 凭据或 keychain 公开归档。

未完成来源：2023 美亚杯团体赛原页多次正文读取失败，聚合转载仅作发现线索，不记为已读复验；mumuzi 原作者页面只找到目录，正文未读。下轮有相关机型再补，不据此填充答案。
