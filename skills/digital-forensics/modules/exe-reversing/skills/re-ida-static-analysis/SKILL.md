---
name: re-ida-static-analysis
description: 供〖EXE 逆向分析专家〗SOP 使用的 IDA Pro 静态分析技能；独立调用时产出不含该专家的报告规范与红线约束
---

# IDA Pro 静态分析（自带技能）

通过 IDA Pro MCP 对目标执行静态逆向。工具名以运行时可见为准（可能带 `ida_pro_mcp__` 前缀），本文档用裸名。

## 前置
- **先以命令行加载目标，省去人工开箱**：IDA Pro MCP 只有在 IDA 载入目标后才启用。因此第一步应通过命令行启动 IDA 并传入目标路径，让 IDA 直接打开目标并完成初始分析，避免操作者手动打开 IDA、再在文件对话框里选文件。
  先确认当前安装的 IDA 可执行文件路径及适用架构，再以实际路径启动；若可执行文件为 `ida.exe`，命令形式为 `ida.exe -A "<目标 EXE 路径>"`（`-A` 自动接受加载对话框）。用 `server_health` 确认 MCP 已就绪后再分析。
- 第一件事调 `survey_binary` 取全貌：架构/位数/段布局/入口点/字符串/函数与导入分类——它一次返回三阶段信息，后续地址都以此库为基准。

## 标准流程
1. **符号枚举**：`imports`（导入表）/ `list_funcs` / `list_globals`；字符串用 `entity_query`(kind=strings) 或 `find_regex`。
   关注高危 API：`CreateFile`/`WriteFile`/`RegSetValue`（文件/注册表）、`VirtualAlloc`/`VirtualProtect`（内存/自修改）、
   `LoadLibrary`/`GetProcAddress`（动态加载）、网络收发与进程/线程注入类。
2. **入口与调用链**：从 `survey_binary` 的 entry points 出发，用 `xrefs_to`（单跳）+ `trace_data_flow`（多跳数据流）
   沿调用链找 `main`/`WinMain`/`DllMain`；有壳先记录「疑似有壳/入口异常」，不强解花指令。
3. **函数级精读**：`analyze_function`（一次返回伪代码+字符串+常量+caller/callee+xrefs+基本块）优先；细看用
   `decompile` / `disasm`；结构用 `basic_blocks` / `callgraph` / `stack_frame` 辅助。
4. **数据与常量**：`get_global_value` 读全局变量；`get_string` / `get_bytes` 读内存；`find` / `find_bytes` / `find_regex` 定位。
5. **沉淀命名与类型**：`rename`（func/data/local/stack 批量）、`set_comments` / `append_comments` 注释、
   `set_type` / `infer_types` / `make_data` 建符号与类型，形成可读的「功能→地址」映射。

## 与 x64dbg 的联动（交接协议）
静态与动态是同一分析循环的两端，靠「共享交接清单」贯通——字段见 references/联动交接清单模板.md。

**地址对齐（ASLR/重定位，联动第一步）：**
- 地址对齐按 references/联动交接清单模板.md：记录同一模块的 IDA 基址、运行时加载基址和 RVA。用 `make_signature_for_function` 生成待验证函数的字节签名，交动态端通过运行时已确认的 `FindPattern` 搜索并核对候选；解包或自修改后的内存布局需要重新确认。

**静态 → 动态（你交付）：**
- 「待验证清单」：地址/函数 + 静态假设 + 断点建议 + 预期观察（间接调用、`GetProcAddress` 取址、分支走向、自解密内容）。
- 「符号映射」：`rename` 后的「地址 ↔ 名称」交动态用 `CommentOrLabelAtAddress` 设置标签（`type=label`），调用前核对运行时工具描述和参数，保证两端同一套语义名。

**动态 → 静态（你接收并回填）：**
- 「运行时发现」：每项裁决（证实/证伪/存疑）+ 依据（断点/快照）。
- 「回填建议」：x64dbg 回报的真实 API 地址/解密数据/实际分支 → 用 `rename` / `set_comments` / `make_data`
  回填命名与注释；证伪项更正注释，存疑项在清单标记下一轮动作。

**循环收敛**：每轮结束检查「待验证/存疑」项；仍有可执行的补证动作时继续，否则记录阻塞、局限和人工复核路径后写报告，不把阻塞项划为已验证。

## 判读要点
- 间接调用（`call [reg+off]`、导入表动态解析）静态难以确认目标，标记「待动态验证」。
- 混淆/花指令（垃圾代码块、`jmp` 链、`push/ret` 跳转）属常见现象，记录而不强行展开。
- 字符串高熵（疑似加密/压缩）、`VirtualAlloc`+写入+执行组合（疑似自解密/注入）→ 标记高危。

## 输出
每次分析产出：元数据摘要、关键符号清单、可疑点清单、已命名符号表，以及给动态端的关键函数字节签名
（`make_signature_for_function`）；并同步更新交接清单的「待验证清单」「符号映射」与「回填结果」。
