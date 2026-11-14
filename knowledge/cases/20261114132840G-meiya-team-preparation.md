# 2026美亚杯团体赛：证据复盘与逐题WP（公开脱敏版）

整理日期：2026-11-14。分析与整理：Codex；题目与检材由用户提供。范围为本次会话实际承担的Q73–291，共219题；Q1–72已由用户取消，不列作未解题。本稿是比赛结束后的证据复盘，不是官方答案，也没有官方判题反馈。

## 状态与来源

本地正式发布快照 `verified.json` revision 26 记录158题；其余19题存在成员完成的独立复现文件，但尚未进入正式发布快照，故列为“成员复现待主复核”；另42题保留待复核或未解状态。本稿没有将成员口头进度、参考答案或截图数量转换为已复核结论。正式发布快照最后更新时间为2026-11-14 08:20:43 UTC。

参考材料为用户转交、作者未标明的 `DOC-01_答案与依据(1).txt`、`COM-02-答案-184-259.md`，以及同学对Q106/Q108/Q157的反馈。这些材料只提供核对线索。下文为本方分析过程的署名整理，不转载对方全文，也不将参考WP视为官方结果。

公开稿删除密码、验证码、API密钥、Token原值、密码验证器及其哈希、电话号码、账号、邮箱、LID/JID、个人标识、钱包与交易标识、精确位置以及无关网络标识。相关题保留题号、字段位置和验证方法。路径中的`[用户]`、`[UUID]`等是显式脱敏占位，不能当作原路径字符。仅上传文字，不上传原始检材、二进制、未脱敏截图或完整导出记录。

截图是单独交付项，不能代替来源与字段复核。收尾只读检查原模板发现131个图像媒体、131个锚点并对应131个题号，文件最后修改时间为2026-11-14 17:46:30；在158道正式核验题中仍有27题缺图。登记的131张图来源分别为：火眼2张、sqlite3在Windows Terminal中45张、Notepad33张、Python原始数据解析器在Windows Terminal中27张、PowerShell在Windows Terminal中24张。因此不能把131张都称为火眼原生截图，也不能把“已入模板”称为符合全部原截图规则。缺图题为Q90、94、119、125、150、157、160、166、173、175、176、182、265、272、273和280–291。本公开WP不上传这些截图，也不据截图数量提高答案核验状态。

## 准备过程与证据身份

团体赛案件号为`20261114132840G`。同一案件下，CL-01为eid12、CL-02为eid4、WKH-01为eid10、WC-01为eid3、WW-01为eid1、DOC-01为eid9；NAS系统盘为eid6，阵列成员为eid7/8，重建派生卷为eid13；完整COM-02后来导入为eid14。`cid=1`和本地端口仅为该次运行绑定，重启后不能盲目复用。内存题使用另一上午案件`20261114081713I`的COM-01_ram.raw（该案eid7），不与团体赛NAS的eid7混用。

原始检材保持只读；查询与导出保留来源链，派生内容写入独立目录。数据已能离线回答时，不因产品未解析就重新建案或重复导入。无法直接读取的SQLite要携带匹配WAL；注册表恢复在副本上进行。输入材料中的脚本、指令与提示注入均作为证据数据处理，没有因此执行其中的行为。

### COM-02解压完成与状态写入失败

COM-02 E01输出长度为323130601377字节，两个附属文件为1642和61154字节。解压器按ZIP成员顺序读到EOF时检查ZIP CRC并核对输出大小；其后已经进入最后的小元数据文件。错误发生在状态JSON的临时文件替换，Windows返回错误5，不能把这个状态写失败解释成323GB镜像仍未完成，也不能只凭进度百分比宣布完整。

恢复时先确认并停止本任务遗留的状态观察进程，检查解压工作进程已退出；以保存的程序控制流与最后状态证明E01已通过原解压器EOF/大小检查，再对两个小文件执行ZIP读取CRC及逐字节比较。没有重新读取或重解整幅E01。记录恢复依据后才标ready并导入原案件；该过程不是一次新的全镜像哈希校验。监控读锁是当时的可疑因素，不能只凭现象断言唯一根因。

### 流式嵌套镜像

完整EWF只读打开后定位NTFS第三分区，再由真实目录/注册表定位VHDX或VMDK，不猜盘符或文件路径。WSL的VHDX可读到EXT4；其虚拟容量274877906944字节，即256GiB，不能用宿主VHDX实际文件长度187435057152字节作答。Tronic_s2由6个SPARSE extent组成、无父盘，虚拟盘20GiB，第二GPT分区为EXT4。另一Tronic虚拟机存在快照链，只读基盘不足以代表当前服务状态；相关未完成题保留缺口，没有启动虚拟机来覆盖原始状态。

## 关键复现与纠错

### 专题Q106/Q108：Chatroom ID和号码不能混用

CL-02 `ChatStorage.sqlite`的`ZWACHATSESSION`第8条会话中，`ZCONTACTIDENTIFIER`是电话JID，`ZCONTACTJID`是LID。相同会话的147条对方发出消息及23条本机发出消息端点都支持LID关联。早期Q106曾误用电话JID，后经数据库与[iLEAPP WhatsApp解析器](https://github.com/abrignoni/iLEAPP/blob/main/scripts/artifacts/whatsApp.py)的Chat ID映射交叉检查修正：Q106和Q108在本题口径下可以相同。公开稿省略实际标识。

这证明的是记录字段与解析映射，而非实际看到了火眼某一聊天列；本案CL-02未生成可用聊天分析表，不能补写成界面已验证。Q96则因题干没有唯一指明群组而保留歧义，不能把上述纠错经验套用为所有Chatroom ID一律等于LID。

### 专题Q125：已加载DLL与直接导入不是同一命题

实际进程名是`msedge.exe`。两个父进程的加载列表均出现ucrtbase.dll、ntdll.dll和version.dll；其中一个进程172条模块名完整可读，另一个192条中12条名字不可读。正式答案ABC依据“已加载模块”口径；不可从缺失页断言所有未见模块一定不存在，也不能把这三个DLL称为Edge专有，或以加载列表证明PE导入表中的直接依赖。

### 专题Q147：Intent Filter不能只看一个域名

`com.google.android.apps.docs.out`中，同一`DriveOpenUrlActivityAlias`的filter同时允许两个候选hostname，另一候选在部分路径也可匹配；它们的VIEW/BROWSABLE和自动验证条件并不能给出唯一答案。另一Launcher过滤器的特殊路径不取消该Alias的正常规则；专门打开文档的Activity也没有提供题目所需的唯一hostname限定。因此保留待复核，不按参考答案反推一项。

### 专题Q149/Q150：零宽字符、位序和校验闭环

从WKH-01的已解密WhatsApp数据库定位看似普通的短消息，保留原始Unicode文本。统计不可见字符后得到8种符号，每符号可承载3bit。还原178字节帧，按题给初态`(nonce << 16) | magic`与xorshift32的左13、右17、左5生成流，结合实际LSB位序进行XOR，提取167字节有效载荷。

最终CRC32校验通过后才比较选项，得到Q150=C；“能读出几个字符”不作为成功判据。没有访问还原的下载地址，也不在公开稿保留该地址。复算脚本定位为原本地工件`P03_WKH_CHAT/decode_q150_final.py`；脚本及输入涉及敏感载荷，不随本稿公开。

### 专题Q157：VIP显示文案与路由名

对同案CL-02导出的两份Tronic.apk读取`assets/index.android.bundle`，依据[Hermes v0.13.0格式源码](https://github.com/facebook/hermes/tree/v0.13.0/include/hermes/BCGen/HBC)确认字节码版本96。自建只读解码器解析9826个函数、206种操作码，未报告解码错误。

AppNavigator函数6931注册Screen名称`ProductShop`；UserDashboard函数9414检查VIP标志后设置onPress闭包；函数9427实际调用navigation.navigate并传入`ProductShop`；函数9446构造购买页面。翻译资源中还出现`Product Shop`、`VIP Market`和`VIP Product Shop`，这些是显示文案，不能替换题目要求的原始路由字符串。WC聊天和图像显示VIP授权前后变化，构成关联证据。COM-02 TSX源码交叉检查当时仍未完成，正式记录保留该边界。

### NAS：缺盘RAID5重建与统计口径

两块有效成员属于同一MD RAID5，role0和role2存在、role1缺失；layout2为left-symmetric，chunk512KiB，data offset18432扇区，事件计数和阵列身份一致。在派生稀疏镜像中按条带/校验位置重建，逻辑长度21455962112字节。11处EXT4 superblock CRC32C通过，独立文件系统导出得到92个文件、61个目录；对图像集合进行目视和OCR复核，确认9张TCoin宣传图片（Q265）。派生镜像标为重建产物，不称原盘。

Q271全范围的成功认证事件是26次；题目选项不含26。独立扫描22185个journal条目与entry数组结果一致，额外一次还有完整session opened、断开和关闭链，不能为匹配25而擅自缩减为某一天。Q275按12个boot_id分组后，前11次raid disk0为sdb，最后一次为sdd；附近容量、UUID和挂载模式相同，不能帮助唯一选定启动组。两题均保持未解冲突。

### COM-02：主配置、Provider文件与计划任务

WSL部分读取OpenClaw主配置、Provider模型配置、cron任务与状态JSON，以及记忆SQLite。区分`Provider ID`与`api`协议名称，区分营业时间每30分钟的结算监控、1分钟自动审批、17时收市结算和日报任务。Q240使用主配置Qwen密钥，Q241按题意使用`agents/main/agent/models.json`中的DeepSeek字段，两处文件不可互换。敏感值均不公开。

Q193租约目标MAC与题面相差一个字节，参考答案实际对应近似MAC，不能记成精确命中。Q205扫描Tronic全部日志后，异常关机启动出现在本地上午；下午启动加载的是`DICT cleanShutdown=TRUE`，运行中再`Setting FALSE`是另一事件含义。没有把题面“下午”忽略掉，也没有把正常运行状态设置当成上次宕机证据。

### COM-02 PostgreSQL：成员离线复现，尚未进入正式快照

成员P03从完整EWF→NTFS→Tronic_s2 VMDK→EXT4只读取得PostgreSQL18数据。以`pg_filenode.map`、`pg_database`、`pg_class`、`pg_attribute`恢复业务库与字段布局：业务库OID16389，结算表OID49278对应实际relfilenode49490。表OID不能直接充当物理文件号。按8192字节页、line pointer、null bitmap、字段对齐和varlena解析tuple；numeric以base10000恢复Decimal。

用`pg_xact`及hint flags判断提交与可见版本。非零xmax若带`HEAP_XMAX_LOCK_ONLY`仅表示锁，不能当作删除。37条有效结算记录中4条在香港时间2026-08-04 09:00–17:00且completed；源码按UTC无时区值写入created_at，因此筛选对应UTC01:00–09:00，不能因集群配置UTC+8再次转换。金额字段带v1前缀，其Fernet令牌逐条认证解密，四笔1000000、580000、12134443、480000，以Decimal得到14194443.00。

订单、商品、客户和活动记录按order_id、customer_id/actor_id、product_id关联，得到两笔有效订单Oil20和Ice5，总金额85000，状态pending；设备为活动记录中的Redmi型号。客户端照片显示的换汇金额不能替代数据库本币金额。口令题只离线比较题给候选的SCRAM-SHA-256 StoredKey与ServerKey，没有网络登录，候选和验证器不公开。18.4版本由服务启动日志及dpkg记录交叉支持。

完整性日志显示`pg_control`及三个`pg_filenode.map`的CRC32C有效，11个关键关系116页的PostgreSQL页校验均有效，所有pageLSN不晚于最后checkpoint。控制文件仍为IN_PRODUCTION，不能称正常关机副本。由REDO点0/BDC2350扫描至0/BDC2458，4条记录CRC与previous链均有效，仅有CHECKPOINT_REDO、RUNNING_XACTS、CHECKPOINT_ONLINE、RUNNING_XACTS；两次运行事务数都是0，之后记录头为零。该范围没有业务表修改或提交记录，成员未启动PG也未执行WAL重放。

这些成员复算报告足以供下一位复核者定位；本稿不新增一次主会话复验的声明。关键本地工件为`P03_COM02_DB/analysis/settlement-result.json`、`scram-result.json`、`vip-orders-result.json`、`pg-integrity.json`、`pg-wal-tail.json`。文件中存在秘密或个人信息，均不随公开稿上传。

### DOC-01：金额、去重与累计停留

邮件与OOXML交易表独立解析，得到406条原记录、405条成功交易和1条失败交易。按交易标识去重、核对工作表标签与实际地址，使用题给Reference Data_Rate换算。全链路涉及26个地址；成功交易费用总计24.84 USD。首次跨链金额只计第一次进入相应币种，不把回流再算一次；转入转出排名排除手续费。累计中转停留最大值6479秒、次大6456秒，不能以某一笔最长停留替代累计。公开稿省略地址和交易标识。

## 逐题记录

下文“正式复核”仅表示本会话本地证据与口径已复核；不表示官方判题正确。“成员复现待主复核”有独立证据工件，但尚未进入正式发布快照。“待复核或未解”不采用参考答案冒充结论。

## CL-01：Windows与OpenClaw

### Q73 计算机名

公开结论：[敏感值不公开]。状态：正式复核。

方法：在恢复副本上读取 SYSTEM 的 ComputerName 键。

证据定位：`CL-01.e01/Operating_System/Windows/System32/config/SYSTEM；/ControlSet001/Control/ComputerName/ComputerName`。

### Q74 Windows时区

公开结论：C（UTC+08:00）。状态：正式复核。

方法：读取 TimeZoneInformation，区分时区配置与显示时间。

证据定位：`CL-01.e01/Operating_System/Windows/System32/config/SYSTEM；/ControlSet001/Control/TimeZoneInformation`。

### Q75 最后登录本机用户

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取 SOFTWARE 的 LogonUI 最近用户值。

证据定位：`CL-01.e01/Operating_System/Windows/System32/config/SOFTWARE；/Microsoft/Windows/CurrentVersion/Authentication/LogonUI`。

### Q76 默认邮件客户端

公开结论：Microsoft Outlook。状态：正式复核。

方法：读取 SOFTWARE\Clients\Mail 默认值。

证据定位：`CL-01.e01/Operating_System/Windows/System32/config/SOFTWARE；/Clients/Mail`。

### Q77 iCloud登录手机型号

公开结论：iPhone 12 Pro Max。状态：正式复核。

方法：将 iCloud 登录邮件与代理会话中的邮件内容交叉核对。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 165；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox`。

### Q78 邮件登录验证码

公开结论：[敏感值不公开]。状态：正式复核。

方法：在 OST Inbox 定位对应服务的验证码邮件，只本地保留原值。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；IPM_SUBTREE/Inbox; message node 2097444`。

### Q79 指定日期Q Coin购买量

公开结论：215740.07870502。状态：正式复核。

方法：按业务日期读取购买记录，核对邮件及会话记录中的数量。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl.reset.2026-08-05T02-17-19.691Z；JSONL line 177；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox`。

### Q80 OpenClaw默认模型

公开结论：C（DeepSeek V4 Flash）。状态：正式复核。

方法：读取 agents.defaults.model.primary。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/openclaw.json；$.agents.defaults.model.primary`。

### Q81 模型授权密钥

公开结论：[敏感值不公开]。状态：正式复核。

方法：定位 auth_profile_store；不公开密钥及密钥哈希。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/agent/openclaw-agent.sqlite；auth_profile_store`。

### Q82 AI助手名称

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取工作区 IDENTITY.md 对应名称字段。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/workspace/IDENTITY.md；line 3`。

### Q83 WhatsApp插件版本

公开结论：C（2026.7.1）。状态：正式复核。

方法：读取 WhatsApp 扩展 package.json 的 version。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/extensions/whatsapp/package.json；$.version`。

### Q84 定时任务内容

公开结论：B（每小时检查邮件）。状态：正式复核。

方法：查询 openclaw.sqlite 的 cron_jobs，区分任务定义与执行结果。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/state/openclaw.sqlite；cron_jobs`。

### Q85 最早Chrome搜索词

公开结论：openclaw。状态：正式复核。

方法：关联 keyword_search_terms、urls、visits，按首次访问顺序排序。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Google/Chrome/User Data/Default/History；keyword_search_terms joined urls and visits; first visit id=1`。

### Q86 默认浏览器程序

公开结论：A（chrome.exe）。状态：正式复核。

方法：关联 http/https UserChoice、注册的处理程序及火眼默认浏览器表。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/NTUSER.DAT；Software/Microsoft/Windows/Shell/Associations/UrlAssociations/http/UserChoice; https/UserChoice；/case/检材分析数据/未指定持有人/12/基本信息/默认浏览器/data.csv`。

### Q87 提示注入发生日期

公开结论：2026-08-06。状态：正式复核。

方法：将邮件时间与会话处理时间对齐，确认恶意指令出现日期。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 16；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox`。

### Q88 恶意内容投递载体

公开结论：A（电子邮件）。状态：正式复核。

方法：核对实际投递邮件及会话输入，区分载体与被攻击的工具。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 16；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox`。

### Q89 图片最初存入方式

公开结论：B（互联网下载）。状态：正式复核。

方法：关联 Chrome downloads 与 downloads_url_chains，确认原始下载记录。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Google/Chrome/User Data/Default/History；downloads id=8 and downloads_url_chains`。

### Q90 Photos最早打开的文件

公开结论：WhatsApp Image 2026-08-03 at 16.54.57 (1).jpeg。状态：正式复核。

方法：解析 Photos JumpList 的 DestList v4，比较现存4条记录。

证据定位：`CL-01.e01/Operating_System/Users/[用户]/AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations/a52b0784bd667468.automaticDestinations-ms；DestList version4; entry_number=1; earliest image entry; all 4 extant records parsed；/case/检材分析数据/未指定持有人/12/用户痕迹/最近访问的项目/data.csv`。

## CL-02：iOS与WhatsApp

### Q91 系统版本

公开结论：26.5。状态：正式复核。

方法：读取 iDevice_info.txt 系统属性并交叉检查版本字段。

证据定位：`CL-02.bin/分区1/iDevice_info.txt；line84 and line49`。

### Q92 IANA时区

公开结论：C。状态：正式复核。

方法：读取设备时区配置，保留 IANA 标识语义。

证据定位：`CL-02.bin/分区1/iDevice_info.txt；line100`。

### Q93 AirDrop标识

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取 com.apple.sharingd.plist 的 AirDropID。

证据定位：`CL-02.bin/分区1/var/mobile/Library/Preferences/com.apple.sharingd.plist；top-level key AirDropID`。

### Q94 头像服饰颜色

公开结论：C。状态：正式复核。

方法：目视原始头像，不以缩略图推断。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Media/Profile/[长编号]-[长编号].jpg；Original WhatsApp own profile photograph`。

### Q95 电子名片联系人

公开结论：[敏感值不公开]。状态：正式复核。

方法：关联电子名片附件与对应聊天上下文。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；Sent contact card to [用户]; Ching Fung / +[长编号]`。

### Q96 群组唯一标识

公开结论：未定。状态：待复核或未解。

方法：存在多个群组；需题意明确或承接前题才可唯一选择。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；Two groups exist; preceding venue/preparation context refers to first [敏感值不公开]`。

边界：题目未指明哪一群组；承接前题可支持候选，但单独题面不足以唯一选择。

### Q97 定时任务失败原因

公开结论：D。状态：正式复核。

方法：读取指定时刻消息与任务失败回复。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 484,485`。

### Q98 询价证券代码

公开结论：7709。状态：正式复核。

方法：从原始对话定位询价代码，保留前导零规则。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 635,636`。

### Q99 邮件草稿拼写处理

公开结论：C。状态：正式复核。

方法：比较原始草稿与代理最终处理回复。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 505,504`。

### Q100 所传APK原名

公开结论：Tronic.apk。状态：正式复核。

方法：关联消息、媒体元数据和导出的APK，保留原名大小写。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=574 with sender group member and saved contact mapping`。

### Q101 筹备场地房间

公开结论：[敏感值不公开]。状态：正式复核。

方法：结合场地筹备连续对话确定房间；公开稿省略具体位置。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 292`。

### Q102 索取二维码用途

公开结论：B。状态：正式复核。

方法：结合索取二维码前后消息判断用途。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 715,716,717,718,733,734,735`。

### Q103 索取二维码次数

公开结论：B。状态：正式复核。

方法：仅统计索取行为对应消息，不重复计发送回应。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；[用户] chat session Z_PK=3`。

### Q104 聊天提及人员

公开结论：[敏感值不公开]。状态：正式复核。

方法：定位原对话列出的人员；公开稿省略身份。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 299,546`。

### Q105 SIM卡ICCID

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取SIM信息并对应设备记录。

证据定位：`CL-02.bin/分区1/iDevice_info.txt；line26 and line50`。

### Q106 桌面端会话Chatroom ID

公开结论：[敏感值不公开]。状态：正式复核。

方法：区分会话ZCONTACTJID与联系号码ZCONTACTIDENTIFIER，并核对消息端点。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8; ZCONTACTIDENTIFIER is phone JID, ZCONTACTJID is LID`。

### Q107 该联系人名称

公开结论：[敏感值不公开]。状态：正式复核。

方法：在相同会话读取联系人显示名，不用电话号码替代。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8`。

### Q108 该联系人LID

公开结论：[敏感值不公开]。状态：正式复核。

方法：从同一会话与消息端点核对LID。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8`。

### Q109 联系人发送消息数

公开结论：147。状态：正式复核。

方法：按相同会话和发送方向统计消息，排除本机发出消息。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE session 8 received text rows`。

### Q110 会话主键

公开结论：8。状态：正式复核。

方法：读取 ZWACHATSESSION.Z_PK。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION primary key`。

### Q111 非原生相机照片

公开结论：IMG_0011.JPG。状态：正式复核。

方法：关联 ZASSET、ZADDITIONALASSETATTRIBUTES 和 ZCLOUDMASTER；包含匹配WAL。

证据定位：`CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.`。

### Q112 拍摄应用

公开结论：C。状态：正式复核。

方法：读取照片来源应用属性，与资源记录对应。

证据定位：`CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.`。

### Q113 照片原始文件名

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取原始文件名字段，不用设备重命名后的名称替代。

证据定位：`CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.`。

### Q114 Cloud Master GUID

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取对应Cloud Master记录的唯一标识字段。

证据定位：`CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.`。

### Q115 iCloud同步时间

公开结论：C。状态：正式复核。

方法：区分创建、修改、导入和云端同步时间，转换UTC+8。

证据定位：`CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.`。

### Q116 原图文件传送群组JID

公开结论：[敏感值不公开]。状态：正式复核。

方法：关联文件型消息与原始图片媒体项，定位群组。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6`。

### Q117 该群组名称

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取同一群组会话的标题。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6`。

### Q118 原图文件传送次数

公开结论：2。状态：正式复核。

方法：按文件类型与图像资源逐条计数。

证据定位：`CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6`。

## 跨检材与COM-01内存

### Q119 跨检材原始照片缺失设备

公开结论：[敏感值不公开]。状态：正式复核。

方法：跨手机比对消息附件、文件清单及实际文件内容；缺失要有完整检索范围。

证据定位：`CM-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q120 内存采集系统时间

公开结论：2026-08-07 15:02:29。状态：正式复核。

方法：读取 windows.info 的 SystemTime，转换UTC+8。

证据定位：`COM-01_ram.raw；读取 windows.info 的 SystemTime，转换UTC+8。`。

### Q121 计算器进程PID

公开结论：18652。状态：正式复核。

方法：从进程列表定位Calculator的真实PID。

证据定位：`COM-01_ram.raw；从进程列表定位Calculator的真实PID。`。

### Q122 explorer子进程总数

公开结论：14。状态：正式复核。

方法：对所有explorer.exe PID求子进程并集，检查父PID语义。

证据定位：`COM-01_ram.raw；对所有explorer.exe PID求子进程并集，检查父PID语义。`。

### Q123 浏览器明文凭据

公开结论：[敏感值不公开]。状态：正式复核。

方法：内存片段与对应浏览器保存凭据记录交叉定位；公开稿不保留秘密值。

证据定位：`COM-01_ram.raw；内存片段与对应浏览器保存凭据记录交叉定位；公开稿不保留秘密值。`。

### Q124 最近退出的远控进程

公开结论：2026-08-07 11:20:54。状态：正式复核。

方法：筛选已终止rustdesk.exe且ExitTime有效的记录，取最大退出时间。

证据定位：`COM-01_ram.raw；筛选已终止rustdesk.exe且ExitTime有效的记录，取最大退出时间。`。

### Q125 Edge已加载DLL

公开结论：ABC（ucrtbase.dll、ntdll.dll、version.dll）。状态：正式复核。

方法：检查实际msedge.exe进程的模块加载列表；仅证明加载，不能证明Edge独有或PE直接导入。

证据定位：`COM-01_ram.raw；检查实际msedge.exe进程的模块加载列表；仅证明加载，不能证明Edge独有或PE直接导入。`。

边界：题面edge.exe按产品简称处理，实际是msedge.exe；已加载不等于产品专有或PE静态直接导入。

### Q126 Hive数量最少的用户

公开结论：[敏感值不公开]。状态：正式复核。

方法：按用户对应Hive路径计数，处理同名或重复映射。

证据定位：`COM-01_ram.raw；按用户对应Hive路径计数，处理同名或重复映射。`。

### Q127 采集时仍登录的用户

公开结论：[敏感值不公开]。状态：正式复核。

方法：结合登录会话与用户映射，不以目录存在推断仍登录。

证据定位：`COM-01_ram.raw；结合登录会话与用户映射，不以目录存在推断仍登录。`。

## WKH-01：Android与消息隐写

### Q128 设备制造商

公开结论：samsung。状态：正式复核。

方法：读取getprop中的制造商属性。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q129 设备型号

公开结论：SM-G9980。状态：正式复核。

方法：读取getprop中的产品型号。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q130 出厂初始API级别

公开结论：C。状态：正式复核。

方法：读取初始API属性，区别当前SDK级别。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q131 安全补丁日期

公开结论：2026-01-01。状态：正式复核。

方法：读取ro.build.version.security_patch。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q132 构建指纹特征

公开结论：B。状态：正式复核。

方法：拆分构建指纹各段并与选项比较。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q133 显示构建版本

公开结论：AP3A.240905.015.A2.G9980ZHSGHZB1。状态：正式复核。

方法：读取面向设置界面显示的完整build ID。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q134 芯片型号

公开结论：SM8350。状态：正式复核。

方法：读取芯片/平台属性。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q135 市场销售代码

公开结论：TGY。状态：正式复核。

方法：读取销售代码/Carrier ID，区别当前SIM运营商。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q136 SIM移动国家代码

公开结论：454。状态：正式复核。

方法：读取SIM1运营商数字码的MCC部分。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q137 出厂语言地区

公开结论：D。状态：正式复核。

方法：读取出厂语言和地区属性。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q138 Verified Boot与Bootloader

公开结论：B。状态：正式复核。

方法：综合verifiedbootstate、锁定状态及引导安全属性。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q139 用户数据加密方式

公开结论：C。状态：正式复核。

方法：读取crypto状态与类型，区分文件级与全盘加密。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q140 完整启动原因

公开结论：B。状态：正式复核。

方法：保留完整bootreason字符串。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q141 ADB运行属性绝对偏移

公开结论：B。状态：正式复核。

方法：将导出属性的字节位置映射回原始镜像绝对偏移，避免把行内偏移当镜像偏移。

证据定位：`local-artifact/WKH-01/WKH-01/WKH-01.bin；原镜像偏移 0x1F8A9A80`。

### Q142 主要CPU架构

公开结论：C。状态：正式复核。

方法：读取主要ABI/CPU架构字段。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q143 固件构建时间

公开结论：A。状态：正式复核。

方法：核对构建日期字符串和时间戳字段。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q144 Bootloader版本

公开结论：G9980ZHSGHZB1。状态：正式复核。

方法：读取bootloader版本，区别显示build ID。

证据定位：`WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out`。

### Q145 Play商店账号

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取Play商店账号关联记录，只本地保留邮箱。

证据定位：`WKH-01.bin/分区1/data_backup/ABR/device_info.json`。

### Q146 云媒体提供程序组件

公开结论：B。状态：正式复核。

方法：检查包的Activity Intent Filter及云媒体设置Action。

证据定位：`WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.apps.photos.out`。

### Q147 Drive域名跳转规则

公开结论：未定。状态：待复核或未解。

方法：核对同一ActivityAlias的全部filter、hostname与路径条件；不能只看某一孤立域名。

证据定位：`WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.apps.docs.out`。

边界：同一DriveOpenUrlActivityAlias匹配多个候选hostname；题目未给组件/路径，不能唯一选。

### Q148 Gmail实际包名

公开结论：B。状态：正式复核。

方法：核对系统实际注册包名。

证据定位：`WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.gm.out`。

### Q149 消息隐写机制

公开结论：A（零宽字符隐写）。状态：正式复核。

方法：检查文本Unicode码点分布，确认不可见字符承载数据。

证据定位：`WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`。

### Q150 隐写有效载荷还原

公开结论：C；完整有效载荷不公开。状态：正式复核。

方法：按8种字符映射、位序、帧结构和xorshift32解码，最后验证CRC32。

证据定位：`WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`。

### Q151 Threads实际包名

公开结论：B。状态：正式复核。

方法：读取Threads包的实际注册名。

证据定位：`WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.instagram.barcelona.out`。

### Q152 联系人底层LID

公开结论：[敏感值不公开]。状态：正式复核。

方法：关联一对一会话和联系人映射，区别手机号与LID。

证据定位：`WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`。

### Q153 场地变更后的房间

公开结论：[敏感值不公开]。状态：正式复核。

方法：按消息顺序区分旧地点与最后变更。

证据定位：`WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`。

### Q154 现场人数

公开结论：D。状态：正式复核。

方法：定位请求清点与随后回复，避免误计聊天参与人数。

证据定位：`WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`。

## WC-01：通信、附件与VIP页面

### Q155 指定通话时长

公开结论：36。状态：正式复核。

方法：筛选指定呼出记录，使用实际duration，区别振铃或失败尝试。

证据定位：`WC-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata`。

### Q156 WhatsApp来电号码

公开结论：[敏感值不公开]。状态：正式复核。

方法：从WhatsApp通话记录读取发起方标识并对应号码。

证据定位：`WC-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata`。

### Q157 VIP购买页面路由

公开结论：ProductShop。状态：正式复核。

方法：反汇编同案APK的Hermes导航逻辑，VIP检查通过后跳转ProductShop。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；local-artifact/team/members/P01_CL02/exports/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/d/3/[UUID].apk`。

边界：WC聊天与同案CL-02导出APK已独立核验；COM-02相应TSX源码交叉检查尚未完成。

### Q158 指定批次附件类型

公开结论：D。状态：正式复核。

方法：按同一批消息的媒体类型枚举，不以文件扩展名替代消息类型。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q159 照片发送附件类型

公开结论：C。状态：正式复核。

方法：读取媒体消息类型及附件元数据。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q160 订单照片中的商品

公开结论：C。状态：正式复核。

方法：目视原始订单照片的商品内容，区别页面路由名称。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q161 指定文字的消息ID

公开结论：[敏感值不公开]。状态：正式复核。

方法：从指定文字消息读取稳定消息ID。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q162 实体取货位置

公开结论：[敏感值不公开]。状态：正式复核。

方法：结合连续聊天定位取货地点，公开稿不公开精确位置。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q163 Safari搜索词

公开结论：yahoo finance。状态：正式复核。

方法：解析Safari历史URL中的检索参数并保留空格和大小写。

证据定位：`WC-01.bin/分区1/var/mobile/Library/Safari/History.db`。

### Q164 Signal包标识

公开结论：org.whispersystems.signal。状态：正式复核。

方法：读取应用注册Bundle Identifier。

证据定位：`WC-01.bin/分区1/var/Manifest.plist`。

### Q165 图片实际存储路径

公开结论：B。状态：正式复核。

方法：以消息的media路径关联实际图像文件，不能根据缩略图路径推断。

证据定位：`WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q166 HEIC原始GPS

公开结论：[敏感值不公开]。状态：正式复核。

方法：直接读取原始HEIC的EXIF GPS；数据库副本存在尾数差异时按题目原文件口径。

证据定位：`WC-01.bin/分区1/var/mobile/Media/DCIM/100APPLE/IMG_0010.HEIC；WC-01.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite`。

## WW-01：iOS、媒体与群组

### Q167 系统版本

公开结论：26.6。状态：正式复核。

方法：读取iDevice_info.txt系统版本。

证据定位：`WW-01.bin/分区1/iDevice_info.txt；line 83`。

### Q168 设备序列号

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取设备序列号，公开稿脱敏。

证据定位：`WW-01.bin/分区1/iDevice_info.txt；line 91`。

### Q169 主要认证邮箱

公开结论：[敏感值不公开]。状态：正式复核。

方法：核对设备认证账号记录，公开稿脱敏。

证据定位：`WW-01.bin/分区1/iDevice_info.txt；line 300`。

### Q170 服务绑定电话

公开结论：[敏感值不公开]。状态：正式复核。

方法：核对服务账号与号码绑定记录，公开稿脱敏。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Library/Preferences/group.net.whatsapp.WhatsApp.shared.plist；FullUserName, OwnJabberID, LastOwnJabberID`。

### Q171 来电所用应用

公开结论：C。状态：正式复核。

方法：从CallHistory应用来源标识确定服务。

证据定位：`WW-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata；ZCALLRECORD Z_PK=5`。

### Q172 Signal注册验证码

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取sms.db中对应注册短信，公开稿不保留验证码。

证据定位：`WW-01.bin/分区1/var/mobile/Library/SMS/sms.db`。

### Q173 储物柜图片路径

公开结论：C。状态：正式复核。

方法：从聊天媒体元数据定位储物柜原图。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；original file plus ChatStorage.sqlite ZWAMESSAGE Z_PK=295 / ZWAMEDIAITEM Z_PK=277`。

### Q174 图片原始字节数

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取同一原图实际文件长度，不使用缩略图或压缩后大小。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；entire original file byte count; ZWAMEDIAITEM Z_PK=277 ZFILESIZE`。

### Q175 交接地点

公开结论：[敏感值不公开]。状态：正式复核。

方法：图像内容与聊天语境交叉核对，公开稿不列精确地点。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；second JPEG stream beginning at byte 76934`。

### Q176 收款钱包

公开结论：[敏感值不公开]。状态：正式复核。

方法：识别图片/消息中的收款钱包，公开稿省略地址。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；second JPEG stream beginning at byte 76934`。

### Q177 发送图片主文件名

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取发送附件原始文件名，并按题意去扩展名。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q178 转账交易哈希

公开结论：[敏感值不公开]。状态：正式复核。

方法：检查JPEG EOI后的追加ASCII内容；区分交易哈希与文件哈希。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/3/f/[UUID].jpg；ASCII appended after JPEG EOI`。

### Q179 群组创建时间

公开结论：2026-07-30 17:11:36。状态：正式复核。

方法：使用群组创建系统事件，转换UTC+8。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q180 群组原始名称

公开结论：[敏感值不公开]。状态：正式复核。

方法：追踪创建时标题及后续改名事件。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q181 指定房间

公开结论：[敏感值不公开]。状态：正式复核。

方法：依据指定消息确定房间，公开稿不列精确位置。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

### Q182 二维码用途

公开结论：D。状态：正式复核。

方法：结合二维码发送前后消息判断用途。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/9/3/[UUID].jpg；QR decoded offline via OpenCV QRCodeDetector.detectAndDecode`。

### Q183 申请VIP的注册账号

公开结论：[敏感值不公开]。状态：正式复核。

方法：从申请VIP的原消息读取账号名，公开稿脱敏。

证据定位：`WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`。

## COM-02：宿主、应用、数据库与邮件

### Q184 Graph token文件大小

公开结论：未定。状态：待复核或未解。

方法：目标是宿主共享项目中的Graph token；先区分Windows与VM中同名副本。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q185 Graph token文件名与SHA256

公开结论：未定。状态：待复核或未解。

方法：对上一题同一文件确认文件名和SHA256；未独立完成前不能照抄参考哈希。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q186 Qwen工具调用解析器

公开结论：hermes。状态：正式复核。

方法：只读启动脚本的--tool-call-parser，不执行脚本。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/start_qwen_8000.sh；vLLM launch arguments --tool-call-parser`。

### Q187 移动访问令牌有效小时

公开结论：未定。状态：待复核或未解。

方法：需读取当前服务配置中的访问令牌默认有效期。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q188 默认Session Secret

公开结论：未定。状态：待复核或未解。

方法：需读取会话密钥默认配置，公开稿不列秘密值。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q189 二维码请求客户端版本

公开结论：未定。状态：待复核或未解。

方法：需过滤UTC换算后的时间、二维码端点和设备元数据。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q190 二维码请求端点

公开结论：未定。状态：待复核或未解。

方法：需在访问日志核对实际请求路径，不能由APK静态字符串替代。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q191 管理员二维码页面源码

公开结论：未定。状态：待复核或未解。

方法：需定位前端源代码页面及路由导入关系。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q192 币价刷新秒数

公开结论：未定。状态：待复核或未解。

方法：需定位币价刷新配置及其时间单位。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q193 DHCP精确MAC对应主机

公开结论：未定。状态：待复核或未解。

方法：精确比较租约MAC；相近MAC不是同一标识的证据。

证据定位：`COM-02宿主 ProgramData/VMware 的DHCP租约及备份；Tronic_s2轮转vmware日志。`。

边界：题面MAC一字节为fc，实际租约及另一VM日志为6c；相近标识仅是候选，不能声称精确命中。

### Q194 结算关联表外键目标

公开结论：A（transactions）。状态：成员复现待主复核。

方法：检查setup.sql中transaction_id外键定义。

证据定位：`Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql`。

### Q195 数据库IP与端口

公开结论：[敏感值不公开]。状态：成员复现待主复核。

方法：读取连接配置并确认是否被运行环境覆盖；当前仅共享项目默认配置完成。

证据定位：`Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/config.py`。

边界：共享项目默认配置已复现，当前VM运行配置覆盖关系尚待核对。

### Q196 营业时段已完成结算批次

公开结论：4。状态：成员复现待主复核。

方法：先由catalog定位实际relfilenode，再按提交可见性、时段和completed筛选。

证据定位：`/var/lib/postgresql/18/main/base/16389/49490`。

### Q197 金额字段加密格式

公开结论：fernet。状态：成员复现待主复核。

方法：用加解密源码及已认证令牌验证Fernet，不能仅凭前缀猜格式。

证据定位：`Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/tronic_amount_crypto.py；Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql；/var/lib/postgresql/18/main/base/16389/49490`。

### Q198 已完成结算金额合计

公开结论：14194443.00。状态：成员复现待主复核。

方法：对同一筛选集合逐条认证解密并以Decimal求和。

证据定位：`/var/lib/postgresql/18/main/base/16389/49490`。

### Q199 三类邮件状态字段

公开结论：A（email_status、bank_email_status、otc_email_status）。状态：成员复现待主复核。

方法：读取数据库模型中的三类邮件状态字段。

证据定位：`Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql；Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/models.py`。

### Q200 数据库口令候选核验

公开结论：[敏感值不公开]。状态：成员复现待主复核。

方法：只对题目给定候选离线校验SCRAM StoredKey和ServerKey，不做网络登录。

证据定位：`/var/lib/postgresql/18/main/global/1260`。

### Q201 数据库连接用户

公开结论：[敏感值不公开]。状态：成员复现待主复核。

方法：读取连接配置用户名；运行环境覆盖值待交叉检查。

证据定位：`Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/config.py`。

边界：共享项目默认配置已复现，当前VM运行配置覆盖关系尚待核对。

### Q202 Tronic操作系统与内存

公开结论：B（Ubuntu 64-bit、4096MiB）。状态：成员复现待主复核。

方法：读取Tronic.vmx的guestOS和memsize。

证据定位：`local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/Tronic.vmx；guestOS; memsize`。

### Q203 第一块网卡硬件型号

公开结论：e1000。状态：成员复现待主复核。

方法：读取ethernet0.virtualDev，不以宿主网卡型号替代。

证据定位：`local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/Tronic.vmx；ethernet0.virtualDev`。

### Q204 独立数据库虚拟机名

公开结论：Tronic_s2。状态：成员复现待主复核。

方法：关联VMware配置、虚拟机目录及角色证据。

证据定位：`local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic_s2/Tronic_s2.vmx；displayName`。

### Q205 下午首次异常关机后启动

公开结论：未定。状态：待复核或未解。

方法：区分启动时读入的DICT cleanShutdown值与运行时Setting FALSE。

证据定位：`COM-02宿主 Tronic虚拟机目录全部vmware*.log、mksSandbox日志及VMware宿主日志。`。

边界：已检日志中的两次异常关机启动均在本地上午；下午启动读入cleanShutdown=TRUE。运行中的Setting FALSE不表示上次异常退出，题证冲突未解。

### Q206 工作区加载另一虚拟机的时间

公开结论：B（04:07:48 UTC）。状态：成员复现待主复核。

方法：定位vmware.log中含另一台vmx路径的Workspace Session记录。

证据定位：`local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/vmware.log；line 270`。

### Q207 首次虚拟磁盘锁定错误

公开结论：A（2026-08-03 11:52:03 UTC+8）。状态：成员复现待主复核。

方法：对全部轮转日志按时间排序，寻找第一次磁盘锁定错误。

证据定位：`local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/vmware-2.log；line 673`。

### Q208 指定价格请求源IP

公开结论：未定。状态：待复核或未解。

方法：需在指定分钟核对/api/price与实际/api/prices路径差异。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q209 代理转发后端节点

公开结论：未定。状态：待复核或未解。

方法：需用同一请求的代理记录关联upstream目标。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q210 生成二维码请求ID

公开结论：未定。状态：待复核或未解。

方法：需同一来源、时段、成功状态及二维码端点共同筛选。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q211 Nginx实际访问日志名

公开结论：未定。状态：待复核或未解。

方法：需读取实际启用的Nginx配置，区别HTTP生效配置与HTTPS模板。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q212 指定价格请求源IP选项

公开结论：未定。状态：待复核或未解。

方法：需确认指定时段第一个成功价格请求，不能仅套用相邻请求来源。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q213 API代理监听端口

公开结论：未定。状态：待复核或未解。

方法：需核对API代理启动绑定端口及运行日志。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q214 二维码请求IP与ID组合

公开结论：未定。状态：待复核或未解。

方法：需同一条成功POST记录同时核对来源和request ID。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q215 登录设备UA与系统版本

公开结论：未定。状态：待复核或未解。

方法：需按日期、时间、设备型号及登录成功状态筛选元数据。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q216 登录设备唯一标识

公开结论：未定。状态：待复核或未解。

方法：需从同一登录记录读取Device ID，公开稿脱敏。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q217 客户端版本与构建号

公开结论：未定。状态：待复核或未解。

方法：需读取对应请求的app_version/app_build，不能用旧APK版本替代。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q218 日报主要收件人

公开结论：未定。状态：待复核或未解。

方法：需读取结算邮件环境配置，公开稿不列邮箱。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q219 Graph客户端标识

公开结论：未定。状态：待复核或未解。

方法：需读取正确项目Token JSON的客户端标识，不公开原值。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q220 token_type与tenant

公开结论：未定。状态：待复核或未解。

方法：需核对同一Token记录中的类型与tenant字段。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q221 Token有效秒数

公开结论：未定。状态：待复核或未解。

方法：需核对该Token记录的有效期字段及单位。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q222 日报与银行邮件路由

公开结论：未定。状态：待复核或未解。

方法：需核对邮件路由实际环境变量及接收类别，公开稿不列邮箱。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q223 OTC邮件地址

公开结论：未定。状态：待复核或未解。

方法：需读取同一环境配置中OTC收件地址，保留大小写于本地。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

## COM-02：WSL与OpenClaw

### Q224 OpenClaw工作目录与Provider

公开结论：C（WSL用户工作目录、Provider vllm）。状态：正式复核。

方法：读取WSL主配置workspace及默认model的Provider前缀，区别API协议名称。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；agents.defaults.workspace; agents.defaults.model.primary`。

### Q225 数据库MCP命令

公开结论：/home/[用户]/.openclaw/bin/postgres-isolated-mcp。状态：正式复核。

方法：读取mcp.servers对应command绝对路径；公开稿将用户目录匿名化。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；mcp.servers.postgres-isolated.command`。

### Q226 DeepSeek Provider ID

公开结论：vllm_gpu1。状态：正式复核。

方法：定位DeepSeek模型条目所属providers键名。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm_gpu1`。

### Q227 Qwen参数规模

公开结论：D（32B）。状态：正式复核。

方法：从模型ID确认32B规模。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.models[0].id`。

### Q228 DeepSeek参数规模

公开结论：C（14B）。状态：正式复核。

方法：从模型ID确认14B规模。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm_gpu1.models[0].id`。

### Q229 17时结算任务名

公开结论：tronic-settlement-monitor-1700-close。状态：正式复核。

方法：按17:00收市结算任务识别name，区别日报和营业监控。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].name`。

### Q230 17时任务ID与cron

公开结论：A（目标任务ID、0 17 * * *；ID不公开）。状态：正式复核。

方法：核对同一任务ID、cron及时区。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].id/schedule`。

### Q231 营业时间监控频率

公开结论：E（30分钟）。状态：正式复核。

方法：解析营业监控cron的分钟列，区别1分钟自动审批任务。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].schedule.expr`。

### Q232 可检索记忆chunks数量

公开结论：C（0条）。状态：正式复核。

方法：只读SQLite并执行quick_check与SELECT COUNT(*) FROM chunks。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/memory/main.sqlite；chunks`。

### Q233 Gateway监听端口

公开结论：18789。状态：正式复核。

方法：读取主配置gateway.port。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；gateway.port`。

### Q234 Qwen服务地址

公开结论：http://127.0.0.1:8000/v1。状态：正式复核。

方法：读取Qwen Provider的baseUrl。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.baseUrl`。

### Q235 定时任务错误原因

公开结论：C（timeout）。状态：正式复核。

方法：读取jobs-state.json中lastErrorReason。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs-state.json；jobs.*.state.lastErrorReason`。

### Q236 WSL发行版版本与UID

公开结论：C（Ubuntu、WSL2、UID 1000）。状态：正式复核。

方法：读取NTUSER.DAT的Lxss发行版键，核对DistributionName、Version及DefaultUid。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/host/partition-3/Users/[用户]/NTUSER.DAT；Software/Microsoft/Windows/CurrentVersion/Lxss/{[UUID]}`。

### Q237 Gateway绑定位置

公开结论：loopback。状态：正式复核。

方法：读取gateway.bind原值。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；gateway.bind`。

### Q238 Qwen上下文容量

公开结论：8192。状态：正式复核。

方法：读取Qwen模型条目的contextWindow。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.models[0].contextWindow`。

### Q239 自动结算美元阈值

公开结论：50000。状态：正式复核。

方法：从监控任务payload及描述核对美元累计阈值。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].payload.message`。

### Q240 Qwen授权密钥

公开结论：[敏感值不公开]。状态：正式复核。

方法：从主配置Qwen Provider读取授权字段，仅本地保存。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.apiKey`。

### Q241 DeepSeek Provider文件密钥

公开结论：[敏感值不公开]。状态：正式复核。

方法：按题目Provider文件读取agents/main/agent/models.json，不能替换成主配置同名值。

证据定位：`local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/agents/main/agent/models.json；providers.vllm_gpu1.apiKey`。

边界：此题以Provider文件models.json为准；其值与主配置同名字段不同。公开稿两处原值均省略。

## COM-02：网站、任务与订单

### Q242 移动项目owner

公开结论：未定。状态：待复核或未解。

方法：需读取移动项目配置的owner，公开稿不列账号名。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q243 HTTPS端口

公开结论：未定。状态：待复核或未解。

方法：需读取HTTPS配置对应listen项。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q244 TLS协议版本

公开结论：未定。状态：待复核或未解。

方法：需读取该HTTPS配置的ssl_protocols。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q245 密码套件顺序参数

公开结论：未定。状态：待复核或未解。

方法：需读取ssl_prefer_server_ciphers实际值。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q246 证书SAN中的IP

公开结论：未定。状态：待复核或未解。

方法：需从证书/生成脚本核对IP SAN，不推断。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q247 证书SAN中的DNS

公开结论：未定。状态：待复核或未解。

方法：需核对DNS SAN，与CN字段区别。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q248 根证书到期时间

公开结论：未定。状态：待复核或未解。

方法：需解析根证书NotAfter并核对时区。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q249 安装WSL及默认WSL2命令

公开结论：未定。状态：待复核或未解。

方法：需检查ConsoleHost_history.txt中实际输入的完整命令。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q250 Windows日报任务完整名称

公开结论：未定。状态：待复核或未解。

方法：需读取Windows计划任务定义中的URI，区别WSL cron同类任务。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q251 PowerShell端口转发目标

公开结论：未定。状态：待复核或未解。

方法：需以PowerShell历史为准还原portproxy目标，区别当前注册表或动态脚本地址。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q252 WSL虚拟磁盘总容量

公开结论：256（GiB口径）。状态：成员复现待主复核。

方法：读取VHDX虚拟容量元数据，区别宿主文件大小和已用空间。

证据定位：`local-artifact/gpt/P01_COM02_WSL/tool-logs/wsl-discovery.json；VHDX metadata VIRTUAL_DISK_SIZE_GUID`。

### Q253 VIP状态修改时间

公开结论：未定。状态：待复核或未解。

方法：需关联设备、管理员端点、目标用户与成功响应。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q254 设备成功管理员登录次数

公开结论：未定。状态：待复核或未解。

方法：需先定义成功状态口径并计所有匹配登录记录，排除失败/刷新请求。

证据定位：`未完成原始检材复验，参考答案仅作线索。`。

边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

### Q255 VIP订单商品及数量

公开结论：A（Oil 20、Ice 5）。状态：成员复现待主复核。

方法：关联有效orders、products和客户记录核对商品及数量。

证据定位：`/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/32873；/var/lib/postgresql/18/main/base/16389/90873`。

### Q256 订单发起设备

公开结论：B（Redmi 23124RA7EO）。状态：成员复现待主复核。

方法：通过同一订单/actor的活动记录核对品牌与型号。

证据定位：`/var/lib/postgresql/18/main/base/16389/90873`。

### Q257 订单交易总额

公开结论：85000。状态：成员复现待主复核。

方法：对同一两笔有效订单金额求和，区别客户端显示的换汇金额。

证据定位：`/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/90873`。

### Q258 当前订单状态

公开结论：D（pending）。状态：成员复现待主复核。

方法：读取两笔当前可见订单的status。

证据定位：`/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/90873`。

### Q259 PostgreSQL完整版本

公开结论：D（18.4）。状态：成员复现待主复核。

方法：以PostgreSQL启动日志和dpkg包版本交叉确定完整小版本。

证据定位：`/var/log/postgresql/postgresql-18-main.log.1；/var/lib/dpkg/status`。

## COM-03-NAS：阵列与系统日志

### Q260 md0阵列UUID

公开结论：C。状态：正式复核。

方法：核对mdadm配置及成员superblock的阵列身份。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/mdadm/mdadm.conf`。

### Q261 Debian与OMV版本及升级前版本

公开结论：B。状态：正式复核。

方法：关联os-release、dpkg status和APT历史，区别当前与升级前版本。

证据定位：`COM03_NAS_DISK0.E01/分区2/usr/lib/os-release；COM03_NAS_DISK0.E01/分区2/var/log/apt/history.log；COM03_NAS_DISK0.E01/分区2/var/lib/dpkg/status`。

### Q262 NAS网络配置

公开结论：[敏感值不公开]。状态：正式复核。

方法：关联网络配置文件和平台配置。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/netplan/20-openmediavault-enp0s3.yaml；COM03_NAS_DISK0.E01/分区2/etc/openmediavault/config.xml`。

### Q263 双配置中的挂载UUID

公开结论：[敏感值不公开]。状态：正式复核。

方法：比较fstab与OpenMediaVault存储配置中的来源UUID。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/fstab；COM03_NAS_DISK0.E01/分区2/etc/openmediavault/config.xml`。

### Q264 指定日期Web错误日志数

公开结论：B。状态：正式复核。

方法：按日期和ERROR等级精确计数，不计普通告警。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/nginx/openmediavault-webgui_error.log.1`。

### Q265 TCoin宣传图片数量

公开结论：9。状态：正式复核。

方法：先可靠重建缺一盘RAID5，再对用户图片枚举、OCR及目视复核。

证据定位：`由两块有效成员重建 md0 派生镜像；EXT4文件枚举、原图目视及OCR交叉复核。`。

### Q266 USERS组人数

公开结论：C。状态：正式复核。

方法：按/etc/group的USERS成员字段计数。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/group`。

### Q267 SMB白名单未包含账号

公开结论：[敏感值不公开]。状态：正式复核。

方法：比较用户集合与Samba允许列表，不把系统账号自动算作允许用户。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/samba/smb.conf`。

### Q268 SSH与普通组交集人数

公开结论：5。状态：正式复核。

方法：取SSH组与普通组显式成员交集。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/group`。

### Q269 Admin组成员

公开结论：[敏感值不公开]。状态：正式复核。

方法：读取管理员组成员配置。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/group`。

### Q270 SSH白名单配置

公开结论：A。状态：正式复核。

方法：核对sshd_config中的AllowUsers/AllowGroups语义及实际配置。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/ssh/sshd_config`。

### Q271 成功SSH认证次数

公开结论：未定。状态：待复核或未解。

方法：按认证事件而非文本行数计数，并保留跨启动/跨日期范围。

证据定位：`NAS / var/log/journal；接受认证事件与后续会话链。`。

边界：全范围得到26次成功认证，选项不含26；只取其中一天得到25但题面未限定，故不强选。

### Q272 可识别SSH会话数

公开结论：D。状态：正式复核。

方法：将Accepted、session opened、断开及关闭关联为会话。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/wtmp.db；COM03_NAS_DISK0.E01/分区2/var/log/wtmp`。

### Q273 成功SSH会话源IP

公开结论：[敏感值不公开]。状态：正式复核。

方法：只统计已确认成功会话的来源，公开稿不列具体地址。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/wtmp.db；COM03_NAS_DISK0.E01/分区2/var/log/wtmp`。

### Q274 失败登录日志大小

公开结论：A。状态：正式复核。

方法：以原日志文件字节长度作答。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/btmp`。

### Q275 同一启动组raid disk 0设备名

公开结论：未定。状态：待复核或未解。

方法：按boot_id关联同一组raid disk 0事件；跨启动设备名发生变化。

证据定位：`NAS / var/log/journal；按 boot_id 分组的 md/EXT4启动记录。`。

边界：12个启动组中前11个raid disk 0为sdb，最后一个为sdd；题面未明确组别，无法唯一确定。

### Q276 md0容量变化字节数

公开结论：21455962112。状态：正式复核。

方法：按日志标准512字节扇区数换算，不用磁盘厂商容量。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/journal/[长标识]/system.journal`。

### Q277 EXT4数据与配额模式

公开结论：A。状态：正式复核。

方法：读取对应EXT4挂载日志的数据和配额模式。

证据定位：`COM03_NAS_DISK0.E01/分区2/var/log/journal/[长标识]/system.journal`。

### Q278 最低SMB协议版本

公开结论：A。状态：正式复核。

方法：读取Samba最低协议配置。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/samba/smb.conf`。

### Q279 文件系统挂载点

公开结论：[敏感值不公开]。状态：正式复核。

方法：从fstab及平台配置核对同一文件系统挂载点。

证据定位：`COM03_NAS_DISK0.E01/分区2/etc/fstab`。

## DOC-01：资金流

### Q280 邮件委托资金总额

公开结论：23010346.36。状态：正式复核。

方法：解析邮件指示和OOXML工作表，统一USD汇率后求和，核对重复与错误标签。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

边界：存在两处工作表标签错误与0.0004 USD的原始口径差异；已显式对齐，不改变两位小数结果。

### Q281 最终资金留存地址数

公开结论：B。状态：正式复核。

方法：仅统计成功交易，计算各地址净流入及仍有余额的终点。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q282 最终停留资金最多的钱包

公开结论：[敏感值不公开]。状态：正式复核。

方法：从无转出终点中比较USD净留存；公开稿省略钱包地址。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q283 黑洞地址用途

公开结论：B（销毁/黑洞地址的常见用途）。状态：正式复核。

方法：解释Burn/Sink地址的一般用途，不能仅凭地址存在证明某笔销毁。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q284 全链路钱包数量

公开结论：26。状态：正式复核。

方法：对完整链路的发送方与接收方取去重并集。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q285 缺少独立工作表的钱包

公开结论：[敏感值不公开]。状态：正式复核。

方法：用链路地址集合减去工作表对应地址集合。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q286 该钱包币种

公开结论：A（Bitcoin）。状态：正式复核。

方法：根据该地址对应交易网络/币种记录确认。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q287 除Q Coin以外币种数

公开结论：3。状态：正式复核。

方法：对实际出现的币种去重，排除Q Coin。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q288 首次跨链资金最多币种

公开结论：C。状态：正式复核。

方法：仅比较各币种首次跨链转换对应USD金额，避免后续回流重复计入。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q289 成功交易手续费USD

公开结论：24.84。状态：正式复核。

方法：筛选成功交易，按Reference Data_Rate将Gas Fee换算USD后求和。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q290 转入转出总额最大钱包

公开结论：[敏感值不公开]。状态：正式复核。

方法：按地址汇总成功转入和转出USD，手续费不入本金。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

### Q291 累计中转停留最长钱包

公开结论：[敏感值不公开]。状态：正式复核。

方法：对每次可匹配的入出区间累计停留秒数，区别单次最长与累计最长。

证据定位：`DOC-01/PyCHK_to_police.xlsx`。

## 可复用的方法约束

1. 将“答案核验”“原生截图保存”“截图入表”“远端归档回读”分开计数。任意一个步骤成功都不替代其余步骤。
2. GUI能截图不代表能输入；激活、点击后必须观察目标变化。拒绝访问或重复无效时保存实际错误并停止相同重试，不擅自改权限、不用生成页面伪装原生截图。
3. 重启后重新发现窗口与案件服务，确认案件号、检材路径及eid，再恢复任务；不复用旧句柄或旧端口当作有效绑定。
4. 大文件处理的完成标记应记录实际EOF/CRC/大小证据，状态写入增加短暂占用重试；恢复必须区分镜像完整性与进度文件可写性。
5. 成员答案写独立目录，正式答案由一个发布者串行更新；WP只消费正式版本或明确标注成员草稿。中断不能把“准备好脚本”变成“已完成分析”。
6. 赛后只整理已完成工作。尚未排除的版本差异、字段歧义、题证冲突保留在WP；不以赛后猜测改写比赛时的证据链。

## 一手格式资料

- [iLEAPP WhatsApp解析器](https://github.com/abrignoni/iLEAPP/blob/main/scripts/artifacts/whatsApp.py)：用于核对Chat ID字段映射，不能替代原数据库。
- [Hermes HBC格式与操作码](https://github.com/facebook/hermes/tree/v0.13.0/include/hermes/BCGen/HBC)：本地APK解码所依据的版本资料。
- [PostgreSQL18 pg_class定义](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/include/catalog/pg_class.h)、[pg_attribute定义](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/include/catalog/pg_attribute.h)：catalog布局与字段映射。
- [PostgreSQL tuple事务标志](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/include/access/htup_details.h)、[页校验算法](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/include/storage/checksum_impl.h)、[WAL记录结构](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/include/access/xlogrecord.h)：成员离线解析与一致性检查所用格式参考。

本页不包含原始附件、产品许可证、解密凭据或未脱敏截图；公开文本保留方法和来源边界，不等价于可独立下载的完整检材复现包。
