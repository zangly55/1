# 2025 美亚杯个人赛：选读方法摘要

- 来源：[原作者题解](https://forensics.xidian.edu.cn/writeups/MeiyaCup2025Individual/)；NoahTie @ tratra 什么都会。
- 赛事年份：2025；发布日期未确认；检索日期：2026-11-16。
- 范围：Q43—46、Q48 的文字分析；未逐图或整篇复验。
- 状态：原作者报告，不作为官方答案；未获取检材。

## 提炼的参考路径

- Q43—46：Poe 的 apollo_db.sqlite 中，作者用 Message: 定位交互，再关联消息 JSON 的时间、机器人和用户；PoeMessageShare: 被解释为推荐分享内容，需与本人会话区分。作者保留用户昵称/全名的题意疑问。
- Q48：视频号缓存与关注数量分开；作者在 finder_main.db 的 finderContactTable3 中使用 followState 筛选关注状态。

## 本次复用约束

这些字段是原文对应版本的候选定位，不能套用所有新版数据库。先检查实际 schema、账户关联和字段含义，再计数；不能把缓存条数、推荐内容当本人活动。公开页不保存真实账号、消息原文、密码或完整答案。
