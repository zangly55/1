# 2026 西电长安杯：选读方法摘要

- 来源：[官方题解](https://forensics.xidian.edu.cn/writeups/ChanganCup2026/)；出题人 NoahTie，题解作者 NoahTie、BlackBird、Track @ XD-Forensics。原页声明 CC BY-NC-SA 4.0。
- 赛事年份：2026；发布日期未确认；检索日期：2026-11-16。
- 范围：手机 Q02、云服务器 Q10—13；仅选读上述文字，不是整份题解或逐图核验。
- 状态：官方题解报告；本次未取得检材、未复验答案。

## 提炼的参考路径

- 手机 Q02：原文从 Wi-Fi 解析记录回到 WifiConfigStore.xml，按 SSID 查 RandomizedMacAddress。使用时先确认真实 Android 路径和该网络配置，不能把随机地址当物理网卡地址。
- 服务器 Q10—13：原文结合 Shell 历史、Vim 临时文件与服务日志定位配置变更；旧端口从历史监听记录寻找。

## 本次复用约束

临时文件是待核线索，不能单独证明崩溃；配置值也不能单独证明实际监听。核对原始时间、事件语义和版本后才应用。公开页省略具体答案、凭据、设备标识与样本下载信息。
