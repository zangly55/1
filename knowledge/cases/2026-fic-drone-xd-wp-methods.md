# 2026 FIC 初赛 Q20：无人机轨迹定位方法摘记

- 来源：[XD Forensics Wiki 2026 FIC 初赛 Q20](https://forensics.xidian.edu.cn/writeups/FIC2026Preliminary/)。
- 署名：XD Forensics Wiki 编写团队；本轮所读章节未见单独作者，发布日期未知。检索日期 2026-11-21。
- 阅读范围：Q20 无人机章节文字、命令与输出；未读完整题库、未逐张核验图片、未下载原检材。
- 状态：作者报告；解析模式另与工具作者文档核对，未做原始日志复验。

作者从手机 `storage/emulated/0/Android/data/dji.go.v5/files/FlightRecord/` 找到两份 TXT，使用 pydjirecord 查看摘要，再通过坐标反查行政区。示例显示日志 v14、DJI Fly、Mini 3 Pro。这里可迁移的是“手机应用目录→日志→坐标→地名”的定位路径，具体设备编号、坐标和答案不归档。

复核边界：[pydjirecord 作者说明](https://github.com/rembish/pydjirecord)区分 v13+ 的文件头读取与取得 keychain 后的帧解密。WP 展示摘要和起点反查，不能据此宣称完成整段轨迹解密。其输出中的录像时长明显超过飞行时长，应作为待查异常；不能仅凭页面输出断言原因或纠正具体数值。

迁移到“在哪个县飞行”题时：起点只证明一个位置，是否跨界需结合有效轨迹点；反向地理编码返回的邻近对象位置不能替代无人机原坐标。若只有文件头，明确记录覆盖不足。详细检查见[方法卡](../topics/drone-flight-log-forensics.md)。
