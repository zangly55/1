# Wireshark TCP 分析标记：抓包可见性与业务计数

- 整理/访问：2026-11-17，Codex；适用：解释 TCP 分析标记及防止把网络包数直接当作业务次数。
- 来源/作者：Wireshark 官方，[TCP Analysis](https://www.wireshark.org/docs/wsug_html_chunked/ChAdvTCPAnalysis.html)（整节）与 [TCP Display Filter Reference](https://www.wireshark.org/docs/dfref/t/tcp.html)（tcp.analysis 相关字段）。
- 日期/版本：页面发布日期未注明；字段页列出字段的适用版本范围，不代表本机已安装该版本。本次未运行 Wireshark/TShark，后续任务须登记实际版本与分析偏好设置。
- 状态：两份官方文档交叉核对；未生成或分析 pcap，未对真实网络事件复验。

## 官方字段含义

TCP 分析依赖已捕获包的状态与处理顺序，并受“Analyze TCP sequence numbers”偏好设置控制。`tcp.analysis.retransmission`、`fast_retransmission`、`out_of_order` 属于分析判断；不同标记有适用条件和优先关系。`tcp.analysis.lost_segment` 表示前面的段未被捕获，抓包开始时即可出现。因此这些标记不能单独证明链路实际丢包、发送端故障或应用重复提交。规则细节和版本范围见上述官方页。

## 可复用核查步骤

1. 先确定抓包点、接口、捕获时间范围及是否从连接中途开始；保留原文件和原帧号。合并文件需另建输入到输出的定位映射。
2. 使用 `tcp.stream == N` 限定当前文件中的会话，再查看两个方向的序号、确认号、负载长度及原始时间；N 只在当前解析上下文有意义。
3. 将 `tcp.analysis.retransmission || tcp.analysis.fast_retransmission || tcp.analysis.out_of_order || tcp.analysis.lost_segment` 用作复核入口。这个显示过滤表达式本次只据字段文档整理，未在本机执行；命中的帧不能直接用于最终业务计数。
4. 计数交易或提交时，另行定义应用层记录单位，并关联端点、请求/响应、事务标识与实际载荷。结合重组结果检查相同字节的传输重复和独立的应用请求。
5. 若仅有部分流量或无法解密，记录缺口；报告可以说“此帧被当前版本标记为疑似重传”，不能据此填写“用户又提交一次”或“网络丢包次数”。

建议在未来任务用可控抓包分别检查重传、乱序、重复捕获和应用重试；这是待执行验证，不计为本轮成果。关联：[离线字段语义](offline-evidence-semantics.md)。
