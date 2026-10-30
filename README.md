# didctf-8p-team-solver

数字取证与 CTF 题组解答技能：DeepSeek 八个独立会话（六名解题手、一名 WP 编写者、一名知识库整理者），GPT 同步准备火眼案件、复核答案，并接续未完成题目。

## 技能入口

[SKILL.md](skills/didctf-8p-team-solver/SKILL.md)

- 首轮共享最多 45 分钟墙钟预算，可靠答案优先交付。
- 火眼 GES CLI 负责检材访问、解析与导出。
- [reverse-skill 接入说明](skills/didctf-8p-team-solver/references/reverse-skill.md)提供按题型选择方法与本机工具的流程。
- scripts/ 包含 DeepSeek 启动器、八会话编排器与离线测试；references/ 包含工作手册、模板与复核规范。

## 使用前配置

这是当前 Windows 本机版本，文档中保留实际工具和知识库路径。换机使用前，请按实际环境调整技能路径、火眼目录、DeepSeek Harness 路径、reverse-skill 根目录和知识库位置，并核验工具可用性。

将 skills/didctf-8p-team-solver 整个目录安装到客户端技能目录，读取 SKILL.md 后按需配置依赖。DeepSeek 凭据由本地配置或进程环境提供，不随本仓库分发。

外部方法库：[zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill)，需单独安装；本仓库只包含接入说明。工具二进制、原始案件检材、完整答案目录与运行日志不包含在本仓库中。

## 取证知识库

[知识库索引](knowledge/INDEX.md)

knowledge/ 保留本地知识库的 cases/ 案例和 topics/ 方法条目，共 20 份 Markdown 文件。公开副本对发现的明文登录密码作脱敏处理，本地原文件未修改。文档内指向本机检材、答案、图片或工作区的路径仅作溯源记录，这些附件未上传，GitHub 无法直接打开。本次为手动快照上传，不会自动同步后续本地修改。

## cvalarm 视频告警项目

[项目入口](projects/cvalarm/README.md) · [项目明细与待完成事项](projects/cvalarm/项目明细.md) · [验证记录](projects/cvalarm/docs/验证记录.md)

可迁移的离线告警参考工程，含合成演示、模型服务接口、独立评测与人工复核。当前真实视频、YOLO/VideoJev/Qwen 权重及服务尚未到位；缺失项、优先级和验收条件已逐项记录。

克隆本仓库后进入 `projects/cvalarm`，运行 `python run.py demo --profile v1`。源码默认只用 Python 标准库。
