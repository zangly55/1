# x64dbg 工具索引

本索引保留原技能工具表的方法名，按调试目标选择候选方法。它不是当前服务端的完整能力声明，也不固定参数、默认值或工具数量；首次调用前以运行时实际工具描述确认名称、参数、状态前提和返回语义。名称可能带 MCP 前缀。

需要某项能力时只查对应分类；若运行时未直接展示候选方法，先通过可用的发现入口查询。只有工具不可用被确认后才记录缺口，不凭索引是否收录判断可用性。调试状态与静态/动态证据边界遵循 `re-x64dbg-dynamic-debug`。

## 会话与事件

| 目标 | 候选方法与用途 |
| --- | --- |
| 查询状态与定位目标 | `GetDebugState` 查询调试状态；`GetCurrentAddress` 查询当前位置 |
| 加载或附加 | `LoadBinary` 加载目标；`AttachProcess` 附加进程 |
| 执行与暂停 | `run` 恢复执行；`PauseDebug` 请求暂停；`WaitForPause` 等待暂停 |
| 重启或结束 | `RestartDebug` 重启会话；`StopDebug` 结束调试，使用前核对对目标进程的影响 |
| 发现工具与检查连接 | `ListCommandsByCategory` 查询工具分类；`Echo` 检查调用连通性 |
| 等待或回看事件 | `WaitForEvent` 等待事件；`GetEventLog` 读取事件日志；`ClearEventLog` 清空日志，仅在相关证据已保留且任务需要时使用 |

## 执行控制与断点

| 目标 | 候选方法与用途 |
| --- | --- |
| 单步与定点运行 | `StepInto` 步入；`StepOver` 步过；`StepOut` 执行至返回；`RunToAddress` 执行至指定地址 |
| 有限轨迹 | `TraceInto` 跟踪并进入调用；`TraceOver` 跟踪并跨过调用 |
| 选择断点类型 | `SetBreakpoint` 普通断点；`SetHardwareBreakpoint` 硬件断点；`SetConditionalBreakpoint` 条件断点；`SetMemoryBreakpoint` 内存断点 |
| 特定异常处理 | `SetExceptionBreakpoint` 配置异常断点；`DeleteExceptionBreakpoint` 删除对应异常断点配置 |
| 核对与启停断点 | `ListBreakpoints` 列出断点；`EnableBreakpoint` 启用；`DisableBreakpoint` 禁用；`ToggleBreakpoint` 切换启停状态 |
| 清理与计数 | `DeleteBreakpoint` 删除指定断点；`DeleteAllBreakpoints` 删除全部断点；`ResetHitCount` 重置命中计数。优先处理本任务创建的断点，保留仍需复核的设置及命中证据 |
| 命中后执行或继续 | `SetBreakpointCommand` 配置命中命令；`SetBreakpointFastResume` 配置快速恢复；启用前确认不会跳过所需的暂停取证 |

## 代码、模块与符号

| 目标 | 候选方法与用途 |
| --- | --- |
| 阅读代码与引用 | `Disassemble` 反汇编；`DisassembleFunction` 读取已分析函数；`GetFunctions` 枚举函数；`GetReferences` 查找引用 |
| 分析结构 | `AnalyzeModule` 分析模块结构；`AnalyzeCode` 分析代码；`DetectOEP` 寻找原始入口候选，结果仍需执行验证 |
| 模块与导入导出 | `ListModules` 核对模块及加载基址；`GetImports` 读取导入；`GetExports` 读取导出 |
| 符号与字符串 | `SearchSymbols` 搜索符号；`ListSymbols` 列出模块符号；`GetStrings` 提取模块内存字符串；`SearchForStrings` 在进程内存中搜索文本 |
| 调试器表达式与命令 | `EvalExpression` 求值；`ExecuteDebuggerCommand` 执行 x64dbg 命令，不能将 MCP 工具名当作命令传入 |

## 寄存器、内存与线程

| 目标 | 候选方法与用途 |
| --- | --- |
| 参数与调用上下文 | `GetAllRegisters` 读取寄存器；`GetArguments` 读取参数；`GetCallStack` 读取调用栈 |
| 指针与表达式观察 | `WatchExpressions` 计算一组表达式；`FollowPointer` 沿指针链读取 |
| 内存范围与内容 | `GetMemoryMap` 查询内存区域；`GetDumpableRegions` 查询可导出区域；`ReadMemory` 读取字节；`FindPattern` 搜索字节签名并核对匹配候选 |
| 进程与异常上下文 | `GetPEB` 读取进程环境块；`GetSEHChain` 读取适用架构的异常处理链 |
| 线程上下文 | `GetThreads` 列出线程；`SwitchThread` 切换当前线程，切换后重新核对寄存器与调用栈所属线程 |
| 线程执行控制 | `SuspendThread` 挂起线程；`ResumeThread` 恢复线程，记录范围及对执行时序的影响 |

## 修改、派生文件与分析记录

修改前保存相关原始值并核对任务边界；修改后的观察与原始运行证据分开记录。导出文件和调试数据库写入工作区，不覆盖原样本。

| 目标 | 候选方法与用途 |
| --- | --- |
| 修改执行上下文 | `SetRegister` 设置寄存器；`WriteMemToAddress` 写内存字节；`Assemble` 在指定地址汇编指令，修改后重新读取验证 |
| 临时内存 | `AllocateMemory` 分配内存；`FreeMemory` 释放内存，仅释放本任务分配且已不再使用的区域 |
| 补丁记录与恢复 | `GetPatches` 查看补丁；`RestorePatches` 恢复补丁，调用前确认恢复范围不会覆盖其他仍需保留的修改 |
| 导出派生样本 | `DumpMemory` 导出内存区域；`DumpModule` 导出模块，记录地址、范围与触发时机 |
| 标签与书签 | `CommentOrLabelAtAddress` 设置注释或标签；`SetBookmark` 添加书签；`ListBookmarks` 列出书签；`DeleteBookmark` 删除指定书签 |
| 保存分析记录 | `SaveDatabase` 保存 x64dbg 分析数据库，先核对保存位置和覆盖行为 |
