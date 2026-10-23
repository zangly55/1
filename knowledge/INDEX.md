# 数字取证知识库

## 2026-10-21 EXSi 服务器镜像取证

[案件20261021162519O：EXSi Server.E01（已确认18题，另有参考冲突）](cases/20261021162519O-esxi-server.md)

案件页已由 GPT 接续更新；已确认、待复核及未解严格分列。敏感密钥已脱敏，详见案件答案。

- [本次解题复盘与skill改进](C:/Users/35124/Documents/取证/ESXi-20261021/wp/本次解题复盘与skill改进.md)（2026-10-21）
- [服务器取证：范围、存储归属与恢复验收](topics/server-forensics-scope-storage-recovery.md)（2026-10-21）

- [ESXi 主机安装时间取证](topics/esxi-install-time.md)（2026-10-21）
- [Linux Samba 与面板日志取证](topics/linux-samba-and-panel-logs.md)（2026-10-21）
- [本地 AI WebUI 会话、Token 与头像取证](topics/openwebui-chat-forensics.md)（2026-10-21）
- [Jellyfin 媒体系统 API 密钥与管理员最后登录](topics/jellyfin-media-api-and-login.md)（2026-10-21）
- [DedeCMS 小说站数据库取证](topics/dedecms-novel-site.md)（2026-10-21）

## 2026-10-21 Windows小说取证

[案件20261014203107C：Q11—25复核（Q13已纠正，Q22起算有保留）](cases/20261014203107C-windows-novel.md)

方法条目见 topics/。本次由DeepSeek起草、GPT复核归档；不得复用局部120章统计为全库结论。

- [参考WP复核与错因：名称、日期、字符范围、缺答](topics/forensic-wp-review-pitfalls.md)（2026-10-21）

- 完整版WP更新：Q13=2946354、Q17=Floorp、Q22参考=10月30日；详见复核错因条目。

- HTML全解复核：14题一致；Q22的29/30日参考冲突，保留31日条件推算，状态待确认。见复核错因条目。

## 2026-10-22 Android 手机镜像取证

[案件20261022195255R：黄志远、方俊郎手机（已确认12题，另Q04/Q10待复核）](cases/20261022195255R-android-phones.md)

两部手机 E01（黄志远 eid=1、方俊郎 eid=2）经火眼解析；案件页只收录 `verified.json` 已确认条目，未复核题不写入结论。已确认：Q01 短视频应用 4 款、Q02 “龙虾”包名、Q03 首启时间、Q05 Discord 控制 PC agent、Q06 版本、Q07 登录用户名（含末尾点 `test901234.`）、Q08 配对码（已脱敏）、Q09 可见实际扫描目标 1 个（原3已纠正）、Q11 登录密码（已脱敏，双重 SHA-256 复算）、Q12 向“军师”发送文件 2 个、Q13 理财应用 4 款、Q14 优质客户判定应用包名；应用清单以应用列表、APK 列表、packages.list 三源互证，Discord 身份与控制链以 APK/账户信息/消息库互证，内部通联以 SQLCipher 库只读复核。

- [Android 应用取证（GES）：清单、版本、账号与聊天数据](topics/android-app-forensics-ges.md)（2026-10-22）


- 2026-10-22：[手机14题WP对照](cases/20261022195255R-wp-review.md)：Q09改1；Q06/Q07保留原始字段差异；Q04/Q10仍待复核。
