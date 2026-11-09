# 环境与安装

## 安装结构与分类

将仓库中的 `skills/digital-forensics/` 整个目录复制到当前客户端的用户技能目录，不只复制 SKILL.md。入口、agents、references、modules 之间使用相对链接，移动整个目录后仍能定位包内资源。

本包归类为“数字取证与 CTF”，只把 digital-forensics 作为统一入口。modules 下的 7 个基础模块、8 个专家包及专家内子技能均为按需资料，不要拆开逐个安装。首次使用仅加载入口，按当前对象、操作和交付物读取一个主分支。

如果已有独立安装的旧取证技能，先备份其目录及将修改的客户端配置，再选择本统一入口；通过客户端支持的技能禁用方式关闭重叠的独立入口，保留原文件与产品工具。Codex 可使用以下配置，path 必须替换为待关闭旧入口的实际绝对路径：

```toml
[[skills.config]]
path = "<旧独立技能的绝对路径>/SKILL.md"
enabled = false
```

安装后检查运行时技能列表：统一入口启用；模块没有成为重复的独立入口；其他技能状态保持不变。若运行时仍枚举模块为可独立调用的技能，按实际文件路径禁用它们；统一入口仍可按路径读取资料。插件提供的产品技能和工具按插件支持的方式管理，不修改插件缓存或为归类关闭仍需使用的工具。

## 外部工具与路径

路径占位符是文档约定，不会由脚本自动展开。调用前根据当前工具发现、产品配置或用户提供的路径解析成真实绝对路径，再核验可执行文件及接口；不要直接运行仍含 `{...}` 的示例。只检查当前分支所需依赖，不为加载专家安装全部产品。

| 占位符 | 含义 |
| --- | --- |
| `{GOLDENEYES_HOME}` | 已安装的弘连火眼根目录；附带 GES 启动器支持产品注册表发现和 GOLDENEYES_HOME 环境变量 |
| `{REVERSE_SKILL_ROOT}` | 用户选择的外部 reverse-skill 方法库根目录，包含对应版本路由与脚本 |
| `{REVERSE_COMPAT_ROOT}` | 仅在使用旧版兼容脚本时需要的另一版本根目录；核实参数，不能自动混用 |
| `{FORENSIC_RUNTIME}` | 用户管理的独立取证工具运行环境及 tools.json；运行入口和实测状态以当前文件及实际验证为准 |
| `{KNOWLEDGE_DIR}` | 用户指定的知识库目录；没有指定时使用当前案件工作区的 knowledge-base，独占写入者按团队规则分配 |
| `{APPANALYSIS_HOME}`、`{WIRESHARK_HOME}` | 已安装的相关产品目录，仅对应分支使用 |
| `{PWSH_EXE}`、`{NODE_EXE}` | 当前可用的 PowerShell、Node 可执行文件 |
| `{USER_HOME}` | 当前操作系统用户目录，运行时获取 |
| `{REVERSE_SKILL_SOURCE}`、`{REVERSE_VALIDATION_DIR}` | 历史下载来源与验收产物位置；只用于理解旧记录，不是安装必需目录 |
| `{DSH_EXE}` | 仅历史 DeepSeek 资料涉及的入口，当前 GPT 工作流不使用 |

产品依赖与最低版本来自各专家包声明，不代表发布时已在每台电脑测试。AppAnalyzer、ForensicDesktop、GE-BootMagix、WebMatrix、IDA Pro/x64dbg MCP 均需在使用时核实；缺失时停止依赖该能力的步骤并说明影响。原有方法库的独立工具只能按实际方法使用，不能冒充缺失的产品流程。

## 随包资源与不随包内容

- 包含专家指南、证据规则、报告/笔录模板、Word 生成脚本、头像资源，以及四个 GES 模块的原始启动器。启动器需要已安装的火眼及 pygesclient，本仓库没有包含火眼程序本体。
- 不包含 AppAnalyzer、ForensicDesktop、BootMagix、网钜、IDA、x64dbg、reverse-skill 方法库及独立运行环境的完整安装。
- 不包含当前机器的 config.toml、认证信息、API Key、案件镜像、分析日志或运行检查点。
- 团队模块已采用 GPT 原生子代理流程。run_deepseek*.py、对应测试和 deepseek.md 为历史资源，保留以便追溯，不属于默认执行流程；不读取历史凭据、不自动调用外部模型。Kimi 仍须用户明确点名。
- 历史启动器的知识库路径使用 DIGITAL_FORENSICS_KNOWLEDGE_DIR 环境变量；未指定时落在其显式工作区内的 knowledge-base，不写维护者的个人桌面目录。

## Word 脚本

使用支持脚本语法的 Python（3.10 或更新）及 python-docx。Codex 桌面环境可先用 load_workspace_dependencies 查找文档运行时；其他环境使用用户选择的 Python。实际 import 验证通过后，以脚本和输入输出的绝对路径运行，不修改系统 Python。

```text
python <本包>/modules/electronic-data-forensics-record-drafting/skills/electronic-data-forensics-record-docx/scripts/md_to_gongwen_docx.py <源稿.md> -o <产物.docx>
```

本发行版保留路径/编号下划线与行内字面值修正。内容检查与页面视觉检查分开；未实际检查页面图片时，不宣称版式验收通过。
