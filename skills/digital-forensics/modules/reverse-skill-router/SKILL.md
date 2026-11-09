---
name: reverse-skill-router
description: 使用本机 reverse-skill 仓库，为逆向分析、数字取证和 CTF 题选择对应方法及可用工具。配合 didctf-8p-team-solver 时保留其火眼入口、GPT 原生子代理团队和复核流程。
---

# 本机 reverse-skill 路由入口

Windows 独立运行环境在 `{FORENSIC_RUNTIME}`；实际命令和可用性以其中 `tools.json` 为准，完整验收及限制见 `../didctf-8p-team-solver/references/reverse-environment.md`。该包旧版 tool-index 会误把 npx 当 MCP 可用，不能覆盖实测记录。WSL、pwntools、binwalk 等 Linux 依赖按用户要求暂不配置。

当前方法库为用户提供的本地包，完整安装在 `{REVERSE_SKILL_ROOT}`；上游模块和相对资源均从该目录读取。入口是 `skills/MASTER-ROUTING.md`，路由事实源为 `skills/config/routing.json`，工具状态见 `skills/tool-index.json`。下载目录名为 1.0.1，内部 VERSION 为 1.1.0，不据此推断新旧或兼容性。

原 Git 版保留在 `{REVERSE_COMPAT_ROOT}`，仅为当前接入提供已验证的离线 scope 脚本兼容入口；具体边界和调用见解题技能的 `references/reverse-skill.md`。不要混用两版脚本参数，也不要将 Git 更新自动视为当前本地包更新。

处理取证竞赛题组或用户调用 didctf-8p-team-solver 时，先读取 `../didctf-8p-team-solver/SKILL.md` 及其 `references/reverse-skill.md`，按该技能编排。reverse-skill 只补充按题型选取的方法和工具，不新增模型会话或改变交付时限。

独立逆向任务按当前用户目标路由，读取选中的模块，确认真实工具入口后执行。路由提示只包含相关样本类型与意图；不要把整仓库的关键词塞入提示。常用本机 CLI 的实测路径和版本在上述接入参考的“本机工具入口”中。上游未收录的本机工具先验证，再记录到当前工作区。

具体工具选择读取 `../didctf-8p-team-solver/references/reverse-skill.md` 的“已验收工具的调用路由”：覆盖数据库、APK、原生/.NET、流量、压缩包、内存、系统伪影、媒体、密码算法、JS 和 WP 图示。依据 tools.json 的 command/prefix_args 运行，逐项遵守 validation/limitation；输入和条件满足后实际执行并记录证据。Web 扫描与设备动态分析另须具备对应目标范围和运行条件；Trivy 当前仅验收离线 secret 扫描。每个新 shell 使用绝对路径或重新加载 activate.ps1。

使用 `skills/scripts/master-route.ps1` 时显式传入当前任务的 `-ProjectRoot` 和唯一 `-OutDir`，避免产物落入安装目录。对目标执行仓库 ACT 流程前按真实授权和样本范围建立 scope；本地包的 case-init 不支持 offline-sample 参数，使用接入参考中明确指定的兼容入口，不能直接照抄旧示例到本地包。安装本包不代表任意公网目标已授权。用户已授权的确定步骤连续完成。

仅安装、更新或查看仓库时不启动取证团队、目标扫描或样本执行。缺工具按需求和已有授权处理，不默认启动服务或改全局配置。当前本地包不是 Git checkout；用户请求更新时核对实际来源和配置，备份后切换，保留本机工具信息；不要在解题途中更新工作流。
