# Windows PE：地址定位与构建时间戳的解释边界

- 整理/访问：2026-11-21，Codex；适用：已有 EXE/DLL 的离线静态定位及时间线复核。
- 来源作者：Microsoft；[PE Format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format) 更新于2026-09-10，选读 General Concepts、COFF File Header、数据目录、Section Table 和 Debug Type 中 REPRO 说明。
- 交叉来源：[IMAGE_DEBUG_DIRECTORY](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-image_debug_directory) 更新于2024-11-20，读取结构及各成员定义。
- 版本范围：PE/PE32+ 图像文件相关语义；并非所有 COFF 对象、畸形文件、壳或内存转储的通用解析方案。
- 状态：官方文档交叉核对；未运行程序、加载样本、验证签名或复验检材，没有合成测试结果。

## 地址和时间字段

RVA 相对于加载基址，通常不是磁盘偏移。节的 VirtualAddress、PointerToRawData、SizeOfRawData 分别用于虚拟位置、磁盘起点及磁盘数据长度；仅在内存存在的补零部分不能当作原文件字节。Certificate Table 的目录地址是磁盘偏移，是常见 RVA 规则的例外。

时间戳为0或0xFFFFFFFF时没有有效日期含义。存在 IMAGE_DEBUG_TYPE_REPRO 时，相关时间字段可能装入内容计算值，不能据此断言实际构建日期。依据：[PE 格式](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)。

调试目录中 AddressOfRawData 是加载后相对基址的地址，PointerToRawData 是文件位置，SizeOfData 不包含目录本身。不要因字段都表示“地址”而使用同一换算。依据：[调试目录结构](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-image_debug_directory)。

## 后续核查步骤

以下是针对取证定位的建议，未在本轮案件执行：

1. 先登记对象完整路径、文件/内存来源、架构、解析器版本及解析错误。把工具展示的 VA、RVA、文件偏移分别注明，不只记录一串十六进制数。
2. 在已确认目标落入某节且由磁盘数据支持的前提下，计算节内差值 `delta = RVA - VirtualAddress`，再用 `PointerToRawData + delta` 定位。读取长度必须同时满足节的原始数据范围及实际文件边界；重叠节、越界、头部地址或未映射数据另行判断，不强套公式。
3. 根据字段语义单独处理证书表和调试信息。查询证书表前先检查目录实际存在及范围；表存在本身不能代替签名有效性验证。
4. 保留每个 TimeDateStamp 的原始数值、所在结构与字节定位，先检查保留值和 REPRO，再决定是否转换日期。转换成功只说明数值可解释为日期，不证明真实编译/攻击时间。
5. 用独立证据核对时间含义，例如已保全的构建记录、分发记录或主机文件活动；发生冲突时并列来源，不能挑一个看起来合理的日期。没有 REPRO 标记也不能反向证明时间字段真实无改动。
6. 报告区分“格式字段读取”“定位到原始字节”“构建时间推断”“运行行为证实”。静态头部内容不能单独证明文件曾在目标主机运行或具有恶意行为。

缺口：未验证畸形/重叠节、截断文件、运行时重定位、加壳样本、不同编译器产物或可重现构建实例。以上规则须在实际检材上通过原字节和对应工具输出复核。

关联：[离线字段语义](offline-evidence-semantics.md)；既有 [精武杯恶意程序参考 WP](../cases/2026-jingwu-malware-141-150-speedcoding.md) 保持原作者报告状态，本卡不改变其题目答案。
