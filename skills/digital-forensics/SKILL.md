---
name: digital-forensics
description: "数字取证与 CTF 统一入口：火眼案件与跨检材分析、APK/EXE 逆向、内存/抓包/服务器取证、涉案资金流水、取证笔录与报告，以及明确要求的检材哈希。按对象、操作和交付物选择专项流程。"
metadata:
  consolidation: "2026-10-31"
  expert-integration: "2026-11-09"
---

# 数字取证与 CTF

仓库发行版把依赖资料收纳在 `modules/`，安装时复制本目录整体。首次执行涉及外部工具或知识库的任务，按 [环境与安装](references/environment.md) 核实实际路径；文档中的历史环境记录不能证明当前机器已就绪。

先识别用户的操作（咨询、分析、复核、写报告或写笔录）、对象（案件、程序、镜像、抓包、服务器或流水）和交付物，再选一个主分支。本入口只负责路由，不默认执行全部专家流程。普通财务表格、一般 Word 排版和软件功能开发使用对应技能，不因出现“资金”“文档”或“程序”就进入取证流程。

保留检材完整路径、适用的案件 cid/URL/eid、程序版本及证据出处，不能混用案件、样本或解析状态。已有信息足以确定任务时直接推进，不重复询问授权。进入其他分支仅用于当前问题的必要补证或用户明确要求的多个交付。

## 原有案件与竞赛分支

- 选案、导入、等待解析、恢复案件上下文：ges-case-management。
- 已打开且所需数据解析完成后的查询、导出、BitLocker：ges-case-analysis。
- 同一已解析案件跨检材的关联、聚合、批量导出：ges-case-batch-processing。
- 只有用户或交付题目明确要求 MD5/SHA1/SHA256 才读取 ges-original-evidence-hash 并创建任务，先查已有结果。
- 少量竞赛题、答案提取与错题复核：forensic-quiz。
- 逆向/CTF 方法咨询、本机工具选择或专家所需工具的可用性检查：reverse-skill-router。具体 EXE/APK 分析再按下表选主流程；方法咨询不自动运行样本、建案或调试。
- 用户要求整组检材竞赛解答或点名八人团队：didctf-8p-team-solver；读取其实际编排要求，并根据可用槽位运行。不能因入口包含团队模块而把单题查询升级为团队解题。

## 专项专家分支

选择下表的一个分支时，先读 [专家联动与依赖](references/expert-linkage.md) 中的公共加载规则和该分支条目，再读对应原始指南。首次读取专家不等于执行其所有快捷任务或启动子代理。

| 当前目标 | 主流程资料 | 范围与相邻分支 |
| --- | --- | --- |
| 火眼综合研判、溯源复核或火眼报告 | [火眼专家](modules/goldeneyes-forensics/EXPERT.md) | 复用上述 GES 模块；单项查询直接走原模块；仅写报告时读取报告子技能，不重开案件或补采 |
| Windows EXE/DLL 功能、算法或行为分析 | [EXE 专家](modules/exe-reversing/EXPERT.md) | 先静态定位；需要验证实际运行行为时才进入动态调试；工具不可用时说明缺口 |
| 安卓 APK 身份、源码、隐私行为或通信 | [APK 专家](modules/apk-analysis-expert/EXPERT.md) | 身份/权限问题停在静态；实际行为问题按原指南补运行证据；Frida 仅用于明确参数缺口 |
| 已有 Windows 内存镜像、已有 LSASS 转储 | [内存专家](modules/memory-forensics/EXPERT.md) | 依输入格式选分支；不启动现场采集；普通初筛不自动提取凭据 |
| 已有 pcap/pcapng 的会话、文件或异常通信 | [流量专家](modules/traffic-forensics/EXPERT.md) | 不自动实时抓包；解密依赖匹配材料；只有必要时与 APK/服务器分支交接 |
| 服务器日志、镜像、服务或异常登录 | [服务器专家](modules/server-forensics-expert/EXPERT.md) | 区分离线分析、镜像仿真与 SSH 接入；离线日志或报告任务不启动虚拟机或连接服务器 |
| 案件资金流水、资金链路和异常交易 | [资金专家](modules/wmx-bill-analysis-expert/EXPERT.md) | 依网钜能力与实际参数分析；规则命中不等于违法事实；一般账表统计不强制调用网钜 |
| 起草、核对或导出电子数据取证笔录 | [笔录专家](modules/electronic-data-forensics-record-drafting/EXPERT.md) | 从已有过程记录选择四类笔录；核对任务只给问题与依据，生成/导出请求才写文件 |

## 联动与交付边界

- 跨分支交接当前问题、对象/版本、来源路径或原文定位、实际方法与状态、事实/推断/冲突、关键缺口及派生产物。已有证据先复用，不能把建议步骤记成已执行。
- 分析报告整理已核查的发现；取证笔录记录实际人员、操作与结果。分析推断不能自动转为笔录事实。只要求报告或笔录时直接选择相应子技能，缺少必要事实则列缺口，不擅自采集。
- 报告格式与输入前提保留各模块约定，用户指定格式优先；简单问题直接回答。Word 排版可结合当前可用的文档技能验证，不把格式检查当作事实复核。
- 专家包引用产品技能不代表产品已安装或接口已连接。先核实当前分支的依赖；缺失则停止依赖该能力的操作，说明影响，不猜命令或伪造结果。安装产品、连接新服务不是加载专家的默认动作。

Codex 默认直接工作。专家角色包不隐含多代理执行；团队仍按上面的显式任务分支选择。用户未明确点名 Kimi 时，不调用或委派 Kimi；若明确要求，报告注明“此结果由 Kimi 提供”。旧描述中的模型名不能覆盖这条用户规则。
原始检材保持只读，派生结果写入工作目录。可靠答案及时交付，并附定位路径、查询方式或证据片段；没有证据的推测不能冒充答案。

## 资料加载约定

下表模块随本目录一起分发，只读取当前任务选中的条目。`modules/` 是按需参考资料，不单独安装或启用为平行入口；需要合并已有独立安装时，按环境与安装说明备份配置并关闭对应独立入口。八个专家保留 EXPERT.md，不额外创建重复 SKILL.md 包装入口。新增子技能及依赖映射见 [专家联动与依赖](references/expert-linkage.md)。

模块内部的相对链接、scripts/、references/ 和“skill 目录”以被读取文档所在目录解析；EXPERT.md 中以专家包目录解析。原 EXE 子技能中未带 ../../ 的 references/ 文本简写指向 EXE 包根目录的 references/，按联动表中的完整路径定位。跨模块旧名称按本入口和联动表读取，不依赖旧斜杠命令。
用户当前要求和已授权范围优先；原模块的全局性触发语句仅适用于已选分支。不要为了本入口预加载所有模块或顺带启动其他工作流。

| 模块 | 资料 |
| --- | --- |
| forensic-quiz | [原始指南](modules/forensic-quiz/SKILL.md) |
| ges-case-management | [原始指南](modules/ges-case-management/SKILL.md) |
| ges-case-analysis | [原始指南](modules/ges-case-analysis/SKILL.md) |
| ges-case-batch-processing | [原始指南](modules/ges-case-batch-processing/SKILL.md) |
| ges-original-evidence-hash | [原始指南](modules/ges-original-evidence-hash/SKILL.md) |
| reverse-skill-router | [原始指南](modules/reverse-skill-router/SKILL.md) |
| didctf-8p-team-solver | [原始指南](modules/didctf-8p-team-solver/SKILL.md) |

