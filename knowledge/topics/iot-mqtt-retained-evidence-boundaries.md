# 物联网 MQTT：留存、重复消息与持久化证据边界

- 建立：2026-11-23；整理：Codex；状态：一手文档核对，未设备/抓包/数据库复验。
- 触发：智能家居或网关收到旧状态，重复消息是否等于重复操作，broker 文件能否证明完整历史。
- 对象：MQTT 5.0 协议及 Mosquitto 内置持久化。设备型号、固件、实际 broker 版本与采集条件：本轮无检材，均未知。不能直接套到 MQTT 3.1.1 或插件数据库。

## 来源与阅读范围

| 来源 | 作者/日期与版本 | 实际选读 |
| --- | --- | --- |
| [MQTT Version 5.0 OASIS Standard](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) | Andrew Banks、Ed Briggs、Ken Borgendale、Rahul Gupta 编辑；2019-03-07 固定标准版 | §3.3.1.1—3.3.1.3，§3.3.2.3.3 |
| [mosquitto.conf 官方手册](https://mosquitto.org/man/mosquitto-conf-5.html) | Roger Light / Eclipse Mosquitto；在线滚动页，未注明发布日及具体软件版本；读取2026-11-23 | persistence、persistence_file、persistence_location、autosave_interval、autosave_on_changes 条目 |

仅选读，不称全文精读；手册 URL 的“-5”是手册节号，不能据此称 Mosquitto 5.0。实际使用前匹配目标安装版本和构建选项。

## 已核对的协议语义

RETAIN=1 的客户端发布可替换同主题留存值；零字节载荷会清除该留存值。新订阅是否收到旧值还受 Retain Handling 控制；已有订阅的转发标志受 Retain As Published 影响。因此订阅侧 RETAIN=1 不能一概解释为新设备事件，留存值也不是完整历史。

DUP 指报文重投尝试，不能证明接收方见过首份；DUP=0 仍可能含重复业务消息。Message Expiry Interval 单位为秒，是寿命而非发生时刻，broker 转发时扣除等待时间。上述依据 [OASIS §3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)，此处仅做协议层解释。

## Mosquitto 参考定位

在线手册说明内置 persistence 默认关闭；启用后连接、订阅及消息状态按保存策略写盘并供重启加载。persistence_file 默认 mosquitto.db，目录由 persistence_location 决定，未设则为当前目录；不要固定猜某个系统路径。autosave_on_changes 可把 autosave_interval 解释成变更计数阈值；否则是时间间隔。文件格式可随版本变化。[官方配置手册](https://mosquitto.org/man/mosquitto-conf-5.html)

取证推论：盘上文件可能落后于内存，缺记录不能直接证明从未发布；状态数据库不自动成为完整审计日志。实际路径应由服务启动参数、配置与挂载关系核对。不要为“补全”证据向原 broker 发信号、重启或升级加载原库。

## 后续案件的可复用核查步骤（未在本轮执行）

1. 登记设备型号/固件、配套 App、broker 构建版本、协议版本与采集时段；分别记录设备、网关、云端和抓包时钟的来源及偏差。
2. 已有抓包中区分客户端→broker 与 broker→订阅者，定位帧号、连接、主题、QoS、DUP、RETAIN、订阅选项、过期字段和载荷中的业务编号。不要仅按载荷相同或 DUP 去重。
3. 已有网关镜像中核对配置及实际持久化文件，再选匹配版本的只读解析方式；记录文件状态与日志覆盖窗口，配置存在不等于已生效。
4. 将 App 操作记录、网关消息与设备状态按业务编号及校准时间关联。抓包接收时刻、载荷自报时刻、物理动作时刻分列；收到命令不等于动作完成。
5. 报告分别给出观测报文数、候选业务事件数及支持依据；身份归属仍需设备/账户证据，主题名或 ClientID 只作关联线索。

## 反例和限制

留存“开”状态可能在稍后订阅时再次送达，不证明此时开过一次；重复消息不自动等于用户按了两次。此为基于文档构造的解释反例，未运行实验。

本轮未部署 broker、连接设备/云账户、采集网络、运行固件或网页代码；无合成测试、真实检材或插件格式验证。公开仅摘要与方法，不含设备标识、位置、账号、密钥或原始数据。后续摄像头、路由器、穿戴等是轮换候选，不是已学型号清单。

相关：[TCP 分析标记](wireshark-tcp-analysis-boundaries.md)；[无人机日志](drone-flight-log-forensics.md)；[学习目录](competition-wp-learning.md)。
