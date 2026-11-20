# Android FBE：CE/DE 存储范围与“锁屏”的解释边界

- 整理/检索：2026-11-20，Codex；适用：已有 Android 提取结果中的应用数据缺失、路径归属及解密范围解释。
- 来源作者：Android Open Source Project / Android Developers（Google）。
- [File-based encryption](https://source.android.com/docs/security/features/encryption/file-based)，页面更新2026-10-30 UTC；选读概述、Direct Boot、多用户、Storage classes，以及解密依赖的说明，不是全篇实现复验。
- [Support Direct Boot mode](https://developer.android.com/privacy-and-security/direct-boot)，页面更新2026-10-28 UTC；阅读存储语义、组件声明、存储 Context、解锁通知与迁移部分。
- 版本边界：FBE 支持始于 Android 7.0；以 Android 10 及以后版本首发的设备须使用 FBE。不能只凭当前升级版本判断具体设备的初始加密方案。厂商实现、用户类型和采集产品仍须实际核对。
- 状态：两份官方文档核对；未连接设备、运行 adb、采集数据、提取密钥或复验检材。

## 官方资料中的关键区分

CE 是凭据加密存储；DE 是设备加密存储，Direct Boot 期间也可供相应应用访问。DE 仍为加密数据，不表示离线镜像中的明文。各用户/工作资料有各自存储与解锁范围，一个用户解锁不等于全部用户解锁。AOSP 内部存储候选路径如下，具体挂载/导出前缀需由当前检材确定。依据：[AOSP FBE](https://source.android.com/docs/security/features/encryption/file-based)。

| 类型 | 路径线索 |
| --- | --- |
| User CE | `/data/user/<user_id>/` |
| User DE | `/data/user_de/<user_id>/` |
| 用户0别名 | `/data/data` 对应 `/data/user/0` |

官方 Direct Boot 文档说明：成功解锁后再次显示锁屏，CE 存储仍可用，直到设备重启；不能把“屏幕锁着”直接等同于“本次启动后尚未解锁”。组件的 `android:directBootAware` 声明与通过 `createDeviceProtectedStorageContext()` 选择 DE 存储是不同线索；声明本身不证明组件实际执行或全部数据都在 DE。依据：[Direct Boot](https://developer.android.com/privacy-and-security/direct-boot)。

## 后续取证核查方法

以下是由上述语义形成的方法建议，未在本轮案件中执行：

1. 先登记设备/系统版本、用户或工作资料 ID、提取时间、采集方式、工具版本及报告中的解密/错误状态。没有记录的启动后解锁状态写“未知”，不能靠当前锁屏截图补推。
2. 对同一包名分别检查已取得的 CE 与 DE 范围。把“未采集”“无法解密”“解析失败”“在已覆盖范围未发现”分开；数据库搜不到时先查覆盖和路径，不直接判定用户删除了数据。
3. 不默认所有应用都属于用户0。路径含不同 user_id 时分别关联包登记与账号证据；工作资料和个人空间的同包名不能直接合并。
4. 查看 Manifest 声明及代码选择的存储 Context，只作为数据落点和执行条件线索。实际访问/运行仍需相应日志、数据库或其他证据支持。
5. 报告保留“存储类别→用户→实际来源路径→可读/解密状态→查询结果”的链条。即使提取到 DE 内容，也不代表 CE、应用自身加密库或全部用户的数据已取得。
6. 原检材保持只读；本知识卡不提供设备转换、重启或更改加密状态的操作。遇到解密能力缺口按实际产品能力报告，不以厂商文档中的开发测试步骤处理原设备。

边界：文档描述的是平台机制，不能替代具体设备状态。未验证厂商定制、多用户停止/重启、工作资料策略、特殊恢复启动或采集工具处理行为；本轮没有“解密成功”结论。

关联：[Android 应用取证](android-app-forensics-ges.md)、[离线证据语义](offline-evidence-semantics.md)。
