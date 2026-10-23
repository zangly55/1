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

外部方法库：[zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill)，需单独安装；本仓库只包含接入说明。工具二进制、案件检材、答案、运行日志与用户知识库不包含在本次发布中。
