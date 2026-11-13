# digital-forensics

数字取证与 CTF 统一技能：按对象、操作和交付物选择案件分析、程序逆向、内存/流量/服务器取证、资金研判或取证文书流程。

## 技能入口

[SKILL.md](skills/digital-forensics/SKILL.md) · [专家联动与依赖](skills/digital-forensics/references/expert-linkage.md) · [环境与安装](skills/digital-forensics/references/environment.md)

本入口替代原来的 `skills/didctf-8p-team-solver` 独立入口；原团队能力已更新为本机现行的 GPT 原生子代理流程，保留在统一技能的 [modules/didctf-8p-team-solver](skills/digital-forensics/modules/didctf-8p-team-solver/SKILL.md) 下，只有整组竞赛或明确团队任务才选择它。

| 分支 | 用途 |
| --- | --- |
| 火眼 GES | 案件准备、数据查询、跨检材关联，以及明确要求的原始检材哈希 |
| APK / EXE | 应用源码、程序逻辑和必要的运行验证 |
| 内存 / 流量 / 服务器 | 按检材类型排查进程、通信、账号、日志和时间线 |
| 资金流水 | 资金去向、账户关联与异常特征研判 |
| 取证文书 | 基于真实记录起草四类取证笔录、生成 Word，或整理已有分析报告 |
| CTF | 单题解答、错题复核；按明确任务选择团队流程 |

## 安装与使用

复制 `skills/digital-forensics/` 整个目录到客户端技能目录，保留 `agents/`、`references/`、`modules/` 结构。只启用统一入口，模块按需读取。升级旧安装前先备份，按客户端支持的方式关闭重复入口；具体步骤见环境与安装说明。

示例请求：

- “用 digital-forensics 分析这个已有抓包中的文件传输。”
- “核查这个 APK 是否实际上传指定数据，并说明证据缺口。”
- “根据这些取证日志起草电子数据提取笔录并导出 Word。”

普通单项任务由 Codex 直接完成；加载专家不等于运行全部流程或启动团队。Kimi 仅在用户明确点名时调用。原始检材只读，事实、推断和待核验事项分开。

本包包含 7 个基础模块、8 个专家包及所需参考资料、模板、脚本与 GES 启动器。火眼、AppAnalyzer、ForensicDesktop、BootMagix、网钜、IDA/x64dbg 及 [reverse-skill 方法库](https://github.com/zhaoxuya520/reverse-skill) 属于外部依赖，使用时按当前环境核实。历史工具验收记录不代表当前机器已就绪。

仓库版将包内引用改为相对路径，将个人电脑上的外部路径改为可配置占位符。DeepSeek 启动器仅作为历史资源保留，不属于当前 GPT 工作流。技能发布不自动上传案件材料或同步后续本地修改。

## 取证知识库

[知识库索引](knowledge/INDEX.md)

knowledge/ 保留本地知识库的 cases/ 案例和 topics/ 方法条目，共 23 份 Markdown 文件（含索引；2026-11-13 新增 3 份精武杯 WP）。公开副本对发现的敏感凭据作脱敏处理；新收录精武杯 WP 的密码、API Key、邮箱授权码、管理入口及密码哈希均已移除，另脱敏邮箱账号。原始附件未修改。文档内指向本机检材、答案、图片或工作区的路径仅作溯源记录，这些附件未上传，GitHub 无法直接打开。本次为手动快照上传，不会自动同步后续本地修改。

## cvalarm 视频告警项目

[项目入口](projects/cvalarm/README.md) · [项目明细与待完成事项](projects/cvalarm/项目明细.md) · [验证记录](projects/cvalarm/docs/验证记录.md)

可迁移的离线告警参考工程，含合成演示、模型服务接口、独立评测与人工复核。当前真实视频、YOLO/VideoJev/Qwen 权重及服务尚未到位；缺失项、优先级和验收条件已逐项记录。

克隆本仓库后进入 `projects/cvalarm`，运行 `python run.py demo --profile v1`。源码默认只用 Python 标准库。
