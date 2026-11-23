# 数字取证知识点速查

更新于 2026-11-23。按题目找文件、表和字段，再用右列的检查点核对。路径随系统、应用版本和采集方式变化。条目沿用所引案例或专题的核验状态，本次核对了归档文字及 iPhone 备份格式资料，原始检材未重新分析。

## iPhone 和 iOS 应用

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| iPhone 锁屏密码、备份口令与加密状态 | 标准本地备份根目录 `Manifest.plist` → `IsEncrypted`。加密备份里还可见 `BackupKeyBag`，现代格式可见 `ManifestKey` | `IsEncrypted=true` 表示备份加密。备份口令是加密设置时单独设定的。plist 保存加密状态及受保护的密钥相关数据，口令明文不会随标准备份写入该文件。Apple 说明本地加密备份也排除锁屏密码、Face ID 和 Touch ID 数据 | [Apple 加密备份](https://support.apple.com/en-gb/108353) · [Apple 备份密钥包](https://support.apple.com/zh-cn/guide/security/sec6483d5760/web) · [OWASP 字段定位](https://github.com/OWASP/mastg/blob/master/tests/ios/MASVS-STORAGE/MASTG-TEST-0058.md) · [格式实现](https://github.com/jsharkey13/iphone_backup_decrypt/blob/master/src/iphone_backup_decrypt/iphone_backup.py) |
| 备份里某个文件的 `fileID` | 可读的 `Manifest.db` → `Files` → `domain`、`relativePath`、`fileID` | 同时限定数据域和相对路径。区分原件和缩略图，例如 `Photo.jpg` 与 `Photo.thumb` | [美亚个人 Q8](../cases/2026-meiya-individual-evidence-review.md) |
| App 的 Bundle ID | 美亚案例的取证导出中，`/var/Manifest.plist` → 应用登记 → Bundle Identifier | 先核对应用名称对应的登记记录。这个路径来自该取证导出，换检材时先确认清单结构 | [美亚团体 Q164](../cases/20261114132840G-meiya-team-preparation.md) |
| App 的版本号 | 备份 `Info.plist` 内嵌 `iTunesMetadata.bundleVersion`、`Manifest.plist` 中相应应用的 `CFBundleVersion`、展示版本 | 先看题目指哪个来源，记录字段名并保留前导零。三处取值可能不同 | [数证 Q68 纠错](../cases/20261121093215T-shuzheng-preparation.md#q68-后续纠错撤销复核阶段的误改2026-11-21) |
| 短信来源与内容 | 镜像 `/var/mobile/Library/SMS/sms.db` | 同时核对发送方、正文语境和时间，尤其要区分同一服务的不同通知 | [美亚团体 Q172](../cases/20261114132840G-meiya-team-preparation.md) |
| 通话方向、时长和所属 App | 镜像 `/var/mobile/Library/CallHistoryDB/CallHistory.storedata` → 案例中的 `ZCALLRECORD` | 定位同一通话后再读方向、时长和来源。来电方、被叫方、设备机主是不同对象 | [美亚团体 Q155–156、Q171](../cases/20261114132840G-meiya-team-preparation.md) |
| 联系人的号码 | `AddressBook.sqlitedb` → `ABPerson` 关联 `ABMultiValue` | 一个人可能对应多个号码。要确认 WhatsApp 实际账号，再对照 `ContactsV2.sqlite` 中的映射 | [美亚个人 Q13–14](../cases/2026-meiya-individual-evidence-review.md) |
| WhatsApp 群创建者 | `ChatStorage.sqlite` → `ZWACHATSESSION` 关联 `ZWAGROUPINFO` → `ZCREATORJID` | 确认字段对应目标群。群 JID 与创建者 JID 分开记 | [美亚个人 Q6](../cases/2026-meiya-individual-evidence-review.md) |
| WhatsApp 图片原件和大小 | `ChatStorage.sqlite` → `ZWAMESSAGE` 关联 `ZWAMEDIAITEM` → 媒体路径和 `ZFILESIZE` | 先从指定消息追到关联媒体，再按路径找原文件，对照实际字节数 | [美亚团体 Q173–174](../cases/20261114132840G-meiya-team-preparation.md) |
| 照片生成时间、移入垃圾桶时间和历史版本 | `Photos.sqlite` 与同名 `-wal`。同时保全存在的 `-shm` | 核对原始数值、纪元、单位和时区。活动记录与 WAL 恢复记录要标明来源，同一照片的多个历史版本按身份键去重 | [美亚个人 Q9、Q15–19](../cases/2026-meiya-individual-evidence-review.md) · [离线字段语义](offline-evidence-semantics.md) |

## Android

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| 实际安装的 App 和包名 | 系统 `packages.list`、取证工具的已安装应用列表、APK 包元数据 | 用系统登记与应用列表互证。安装包、卸载残留和系统预装分别处理。计数前约定是否排除预装 | [Android 应用取证](android-app-forensics-ges.md) |
| App 首次打开时间 | 部分使用 Firebase Analytics 的 App，可查私有目录 `shared_prefs/com.google.android.gms.measurement.prefs.xml` → `first_open_time` | 案例原值为 Unix 毫秒。核对实际字段及启动日志，安装时间与首次打开时间分别记 | [Android 应用取证 · 首次打开](android-app-forensics-ges.md) |
| App 版本和当前登录账号 | APK 元数据、`shared_prefs` 中的配置、应用账户记录 | 分别保留安装包版本、客户端版本和 OTA 版本。账号 ID、用户名、显示名按原字段记，保留尾点等字符 | [Android 应用取证](android-app-forensics-ges.md) |
| 应用数据库没找到 | `/data/user/<user_id>/`（CE）、`/data/user_de/<user_id>/`（DE），用户 0 的 CE 常可经 `/data/data` 定位 | 核对当前采集覆盖了哪个用户/工作资料、哪类存储和何种解密状态。重启后的首次解锁与之后再次锁屏是两种状态 | [Android FBE](android-fbe-ce-de-evidence-scope.md) |

## Windows

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| 系统构建号 | `SOFTWARE` hive → `Microsoft\Windows NT\CurrentVersion` → `CurrentBuild` / `CurrentBuildNumber` | 核对同一镜像的原字段。产品名、显示版本与构建号按题目分别记录 | [美亚个人 Q20](../cases/2026-meiya-individual-evidence-review.md) |
| 账户对应哪个用户目录 | `SAM` 的 RID 与 `SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList` 的 SID 和 `ProfileImagePath` | 在同一主机内核对完整 SID 与路径。RID 要先确认十六进制/十进制，显示名只作辅助 | [美亚个人 Q25–26](../cases/2026-meiya-individual-evidence-review.md) · [离线字段语义](offline-evidence-semantics.md) |
| 默认浏览器 | 用户 `NTUSER.DAT` → `Software\Microsoft\Windows\Shell\Associations\UrlAssociations` → `http` / `https` 的 `UserChoice\ProgId` | 分别读取 HTTP 和 HTTPS 的关联。该值反映所采集用户配置中的设置，历史变更需要旁证 | [浏览器取证](windows-browser-forensics.md) |
| 浏览过哪些网址 | Chrome/Edge 对应 Profile 的 `History` → `urls`；Firefox 的 `places.sqlite` | 核对用户与浏览器 Profile。Chromium `last_visit_time` 用 1601-01-01 起的微秒解释，比较前统一时区 | [浏览器取证](windows-browser-forensics.md) |
| NAS 映射盘符 | 用户 `NTUSER.DAT` → `Network\<盘符>\RemotePath` | 用同用户的 `MountPoints2`、快捷方式或相应访问记录互证。历史映射和目标时点的映射分别判断 | [NAS 映射盘符](windows-nas-mapped-drive.md) |
| 程序是否运行、是否由 Win+R 启动 | `UserAssist` 查执行线索，`RunMRU` 查运行对话框输入痕迹 | 记录用户、程序完整路径和时间。要证明通过 Win+R 启动，寻找对应 `RunMRU` 或其他直接证据 | [美亚个人 Q41、Q48](../cases/2026-meiya-individual-evidence-review.md) |
| 文件什么时候打开 | `RecentDocs`、LNK、Jump List 和浏览器历史 | 先说清所用字段表示键写入、链接属性、打开记录还是页面重载。要判定首次打开，核对记录覆盖范围 | [美亚个人 Q36–37，候选](../cases/2026-meiya-individual-evidence-review.md) · [离线字段语义](offline-evidence-semantics.md) |
| 文件的时间与改名痕迹 | 同一 `$MFT` 记录的 `$STANDARD_INFORMATION`、`$FILE_NAME`，以及 `$UsnJrnl` 的 `Reason` 和文件引用 | MFT 时间差异是复核线索。改名时按同卷、文件引用及前后旧名/新名记录关联，`Reason` 允许多个标志并存 | [美亚个人 Q42](../cases/2026-meiya-individual-evidence-review.md) · [USN 记录](ntfs-usn-record-boundaries.md) |
| 哪个日志被清空、谁执行 | 案例中的 `System.evtx` → 清除事件 → 目标日志名称与执行者 SID | 先筛目标通道，再按 SID 关联账户。最早记录较晚也可能由日志循环覆盖造成，需找实际清除事件 | [美亚个人 Q29–30](../cases/2026-meiya-individual-evidence-review.md) |

## Linux、虚拟化与应用服务器

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| Samba 允许谁访问共享 | `/etc/samba/smb.conf` 与 `include` 文件 → 目标共享段的 `path` 和 `valid users` | 配置说明允许范围。要确认某账号实际访问，再找有效日志或会话记录 | [Samba 与面板日志](linux-samba-and-panel-logs.md) |
| ESXi 主机安装或初始化时间线索 | 启动分区的 `state.tgz` → `local.tgz` → `etc/vmware/esx.conf` → `/system/inception` | 案例原字段无时区。用明确带时区的 `vmksummary.log`、`hostd.log` 辅助核对，保留无法确认的时区 | [ESXi 安装时间，候选](esxi-install-time.md) |
| systemd 日志里的时间 | journal → `__REALTIME_TIMESTAMP`、`_SOURCE_REALTIME_TIMESTAMP`、`__MONOTONIC_TIMESTAMP` | 前两者分别对应 journal 接收时间与可取得的源时间，单位都是 Unix 微秒。单调时间要在同一 `_BOOT_ID` 内比较 | [journal 时间](systemd-journal-time-export-boundaries.md) |
| Open WebUI 的提问次数 | 当前部署的 `webui.db` → `chat` 表 → 会话 `id`、`created_at` 和 `chat` JSON | 先按本版本的字段结构和时间锁定会话，再数 `role=user` 的消息。区分重试、分支与跨会话统计 | [Open WebUI 会话](openwebui-chat-forensics.md) |
| SQLite 数据库最新记录与历史记录 | 主库、同名 `-wal` 及存在的 `-shm`。在工作副本上看提交边界、页和主键 | 把活动快照、历史版本与异常尾部候选分别记。WAL 要校验 salt、校验和及提交标记，按业务主键判断是否重复 | [SQLite WAL](sqlite-wal-commit-validation.md) |

## 网络与邮件

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| 一次 TCP 会话的两端与时间 | pcap 中相应 `tcp.stream`、原始帧号、两端地址和端口 | 核对抓包点、方向与覆盖时段。stream 编号属于当前文件和解析上下文 | [Wireshark TCP](wireshark-tcp-analysis-boundaries.md) |
| TCP 重传、乱序与业务提交次数 | `tcp.analysis.retransmission`、`tcp.analysis.fast_retransmission`、`tcp.analysis.spurious_retransmission`、`tcp.analysis.out_of_order` | 报文统计按帧取并集，标记可能重叠。业务次数按请求、响应或事务标识另算 | [精武杯网络 WP](../cases/2026-jingwu-network-151-170.md) · [Wireshark TCP](wireshark-tcp-analysis-boundaries.md) |
| 邮件经过哪些中继 | 完整邮件头的 `Received` 顺序、时间偏移及可信接收端的 MTA 日志 | 从可确认的接收端逐跳核对，区分对方自报主机名与接收端记录的连接地址 | [邮件头取证](email-header-trust-boundaries.md) |
| 邮件认证结果能证明什么 | `Authentication-Results` → `authserv-id`、方法、结果与被检查的标识 | 先用接收侧记录确认这个字段的产生者，再解释对应方法的 `pass`。自然人归属另找账号或主机证据 | [邮件头取证](email-header-trust-boundaries.md) |

## 物联网与无人机

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| MQTT 是新事件还是旧状态 | `PUBLISH` 的方向、主题、`RETAIN`、`DUP`、QoS、订阅选项和业务编号 | 对照消息流向和订阅时点。订阅时重发的留存状态、协议重投和设备实际动作分别记录 | [MQTT 留存与重复](iot-mqtt-retained-evidence-boundaries.md) |
| 无人机是否恢复出完整轨迹 | DJI 的 `FlightRecord` TXT 或 DAT，先认移动端/遥控器/机载来源，再读格式版本、有效帧数和时间覆盖 | 文件头摘要与解出的轨迹帧分别记。飞行次数先定义架次边界，并排查同步副本 | [无人机日志](drone-flight-log-forensics.md) · [数证遥控器案例](../cases/20261121135627D-shuzheng-drone-preparation.md) |
| 无人机在哪里、飞多高 | 飞机轨迹的 GPS 字段、`HomePoint`、原始媒体的 EXIF/SRT（如有） | 分开飞机、遥控器和起飞点位置。写明坐标系、高度单位及相对/绝对高度基准，媒体位置要与同一记录关联 | [无人机日志](drone-flight-log-forensics.md) |

## 程序与内存

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| PE 中的地址如何定位到磁盘 | PE 节表的 `VirtualAddress`、`PointerToRawData`、`SizeOfRawData`，再看数据目录语义 | 先区分 VA、RVA 与文件偏移，再确认目标字节存在于节的原始数据范围。证书表目录用文件偏移 | [PE 地址与时间戳](pe-address-timestamp-boundaries.md) |
| PE 时间戳能否用于时间线 | PE `TimeDateStamp` 与调试目录中的 `IMAGE_DEBUG_TYPE_REPRO` | 检查保留值、REPRO 和字段所在结构。有 REPRO 时该值可能来自内容计算。若要确定构建时间，用分发或构建记录互证 | [PE 地址与时间戳](pe-address-timestamp-boundaries.md) |
| HAP 申请了哪些权限 | 安装包内实际的 `module.json` | 清点指定模块的请求权限，记录是否按权限名去重。要证明授予或调用，还需相应设备记录 | [精武杯 HAP Q132，参考 WP](../cases/2026-jingwu-hap-ipa-121-140-speedcoding.md) |
| 内存插件报符号缺失或空结果 | Volatility 3 的错误和符号身份。Windows 查 PDB 名称＋GUID/age，Linux/macOS 查内核 banner | 匹配符号再解释输出。符号缺失时将这段分析记为未完成 | [Volatility 3 符号匹配](volatility3-symbol-matching.md) |

## 资金流水

| 要查什么 | 先看哪里 | 怎么核对 | 来源 |
| --- | --- | --- | --- |
| 截至指定日期还欠多少 | 约定金额、账本、转账凭证、同会话的到账确认 | 逐笔核对项目、币种、状态和截止日。同一付款的截图与聊天记录去重。聊天确认单独标注证据来源 | [数证 Q78、Q80](../cases/20261121093215T-shuzheng-preparation.md) |
| 资金最终留在哪些地址 | 交易标识、执行状态、转入/转出、手续费与期初余额 | 按链和资产核对同一笔交易的记录。留存余额取决于实际成功的转移、费用和统计窗口，地址曾收到资金只是一条流入记录 | [美亚团体 Q280–282](../cases/20261114132840G-meiya-team-preparation.md) |
