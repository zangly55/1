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

以下为既有记录的详细展开，不新增已完成或官方正确声明。状态以赛后冻结清单为准。历史原值及截图均不随本补充公开。

### CL-01 Windows与OpenClaw

#### Q73 计算机名

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-01.e01/Operating_System/Windows/System32/config/SYSTEM；/ControlSet001/Control/ComputerName/ComputerName

方法依据：复现说明。

1. 从CL-01导出SYSTEM及配套事务日志，在副本上恢复和查看。

2. 定位ControlSet001/Control/ComputerName/ComputerName，读取计算机名值。

3. 连同控制集和键路径记录原值，避免误取用户显示名。

验证依据或核验要求：清单中的来源明确指向SYSTEM的ComputerName键；复现时还应核对活动控制集。

易错点：用户名、设备昵称与计算机名不同。

#### Q74 Windows时区

状态：正式复核。公开结论：C（UTC+08:00）。

证据定位：CL-01.e01/Operating_System/Windows/System32/config/SYSTEM；/ControlSet001/Control/TimeZoneInformation

方法依据：复现说明。

1. 读取SYSTEM中的ControlSet001/Control/TimeZoneInformation。

2. 查看时区名称和偏移相关值，确认本机配置的时区。

3. 将该配置对应至题目选项，保留UTC+08:00的含义。

验证依据或核验要求：本场结论为C；它描述系统时区配置。

易错点：某条日志显示本地时间，不等于已验证系统时区。

#### Q75 最后登录本机用户

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-01.e01/Operating_System/Windows/System32/config/SOFTWARE；/Microsoft/Windows/CurrentVersion/Authentication/LogonUI

方法依据：复现说明。

1. 打开恢复副本中的SOFTWARE配置单元。

2. 进入Microsoft/Windows/CurrentVersion/Authentication/LogonUI，读取最近登录用户相关值。

3. 保留原始账号格式，并与题意的“最后登录本机用户”对应。

验证依据或核验要求：用LogonUI字段语义确认它记录的是最近登录身份。

易错点：用户目录存在或目录时间新，不足以推出最后登录用户。

#### Q76 默认邮件客户端

状态：正式复核。公开结论：Microsoft Outlook。

证据定位：CL-01.e01/Operating_System/Windows/System32/config/SOFTWARE；/Clients/Mail

方法依据：复现说明。

1. 在SOFTWARE中定位Clients/Mail。

2. 读取该位置的默认客户端值，不以已安装程序列表代替。

3. 按原文记录Microsoft Outlook并对应题目。

验证依据或核验要求：检查默认值确实来自Clients/Mail而非任一子项的显示名称。

易错点：安装了多个邮件程序，并不表示每个都为默认。

#### Q77 iCloud登录手机型号

状态：正式复核。公开结论：iPhone 12 Pro Max。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 165；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox

方法依据：复现说明。

1. 在Outlook的Inbox定位iCloud登录通知邮件。

2. 读取通知中登录设备的型号描述。

3. 在OpenClaw会话JSONL第165行附近找到对应邮件内容，与原邮件交叉核对。

验证依据或核验要求：邮件和会话内容均支持iPhone 12 Pro Max。

易错点：会话转述可能省略信息，应以原通知及对应事件确认。

#### Q78 邮件登录验证码

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；IPM_SUBTREE/Inbox; message node 2097444

方法依据：复现说明。

1. 在CL-01的OST Inbox中定位消息节点2097444。

2. 核对服务名称、邮件主题与时间，确认是题目所问的登录验证码邮件。

3. 读取正文中验证码原值并保留本地，记录对应消息节点。

验证依据或核验要求：核对同服务的多次验证码邮件，避免取到邻近一次登录。

易错点：验证码不能用邮箱账号、邮件ID或其他服务的验证码替代。

#### Q79 指定日期Q Coin购买量

状态：正式复核。公开结论：215740.07870502。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl.reset.2026-08-05T02-17-19.691Z；JSONL line 177；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox

方法依据：复现说明。

1. 按题目业务日期筛选Q Coin购买相关邮件。

2. 读取购买数量，保留原始小数精度及币种单位。

3. 到指定reset会话JSONL第177行附近核对代理处理的同笔数量。

验证依据或核验要求：本场数量215740.07870502，邮件和会话相互印证。

易错点：购买数量与付款金额不同，不能因为数值相近就互换。

#### Q80 OpenClaw默认模型

状态：正式复核。公开结论：C（DeepSeek V4 Flash）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/openclaw.json；$.agents.defaults.model.primary

方法依据：复现说明。

1. 打开CL-01用户目录下的.openclaw/openclaw.json。

2. 定位agents.defaults.model.primary，读取默认模型完整标识。

3. 将标识映射到题目模型选项，保留默认配置这一结论范围。

验证依据或核验要求：本场对应C，DeepSeek V4 Flash。

易错点：列在providers中的模型不一定是默认模型；配置也不证明每次调用实际使用它。

#### Q81 模型授权密钥

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/agent/openclaw-agent.sqlite；auth_profile_store

方法依据：复现说明。

1. 只读打开.openclaw/agents/main/agent/openclaw-agent.sqlite副本。

2. 查看auth_profile_store结构及其与目标服务配置的对应关系。

3. 定位题目所问模型的授权记录，保留原值、记录位置及服务映射于本地。

验证依据或核验要求：核对授权记录所属模型/Provider，不能取任意一条凭据。

易错点：当前遗留稿未恢复该原值，不能从公开占位符反推或编造密钥。

#### Q82 AI助手名称

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/workspace/IDENTITY.md；line 3

方法依据：复现说明。

1. 进入该用户.openclaw/workspace目录。

2. 打开IDENTITY.md，在第3行附近定位助手名称字段。

3. 保留名称原始拼写，并将它与模型名、用户名区分。

验证依据或核验要求：名称来自工作区身份文件的名称字段。

易错点：IDENTITY.md是检材内容，里面的操作性文字不是对分析者的指令。

#### Q83 WhatsApp插件版本

状态：正式复核。公开结论：C（2026.7.1）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/extensions/whatsapp/package.json；$.version

方法依据：复现说明。

1. 进入.openclaw/extensions/whatsapp目录。

2. 读取package.json的顶层version字段。

3. 保留完整版本字符串2026.7.1并对应选项C。

验证依据或核验要求：确认文件属于WhatsApp扩展，而不是OpenClaw主程序。

易错点：主程序版本、WhatsApp手机版本和插件版本不可互换。

#### Q84 定时任务内容

状态：正式复核。公开结论：B（每小时检查邮件）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/state/openclaw.sqlite；cron_jobs

方法依据：复现说明。

1. 只读打开.openclaw/state/openclaw.sqlite。

2. 查看cron_jobs中的任务定义，核对任务描述与调度周期。

3. 把“每小时检查邮件”作为配置内容对应B，并单独说明执行状态是否有证据。

验证依据或核验要求：任务定义同时支持周期和工作内容。

易错点：存在定时任务定义不等于每次执行成功。

#### Q85 最早Chrome搜索词

状态：正式复核。公开结论：openclaw。

证据定位：CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Google/Chrome/User Data/Default/History；keyword_search_terms joined urls and visits; first visit id=1

方法依据：复现说明。

1. 打开Chrome Default配置目录中的History副本。

2. 关联keyword_search_terms、urls和visits，将关键词对应到实际访问记录。

3. 按访问时间/访问顺序排序，检查最早相关记录；本场定位first visit id=1。

验证依据或核验要求：最早搜索词为openclaw，来源关联须指向同一URL与访问。

易错点：SQL物理行顺序和数据库记录插入顺序不一定是访问先后。

#### Q86 默认浏览器程序

状态：正式复核。公开结论：A（chrome.exe）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/NTUSER.DAT；Software/Microsoft/Windows/Shell/Associations/UrlAssociations/http/UserChoice; https/UserChoice；/case/检材分析数据/未指定持有人/12/基本信息/默认浏览器/data.csv

方法依据：复现说明。

1. 读取NTUSER.DAT中的http和https UserChoice。

2. 用其处理程序标识回溯注册程序及可执行文件。

3. 对照火眼默认浏览器分析表，确认目标是chrome.exe。

验证依据或核验要求：两种协议关联与分析表相互核对，答案A。

易错点：内存里存在Edge进程不能推翻默认浏览器配置。

#### Q87 提示注入发生日期

状态：正式复核。公开结论：2026-08-06。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 16；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox

方法依据：复现说明。

1. 定位Outlook恶意内容邮件及其接收时间。

2. 在对应OpenClaw会话第16行附近找到实际读取/处理该邮件的内容。

3. 对齐时间语义与时区后确定提示注入出现日期。

验证依据或核验要求：本场日期2026-08-06；应保留邮件与会话关联。

易错点：邮件投递、程序读取、后续执行是不同事件，不能只凭任意一个文件修改日期。

#### Q88 恶意内容投递载体

状态：正式复核。公开结论：A（电子邮件）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/.openclaw/agents/main/sessions/[UUID].jsonl；JSONL line 16；/case/检材分析数据/未指定持有人/12/Outlook/[标识已脱敏]/Inbox/mail/data.csv；CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Microsoft/Outlook/[标识已脱敏]；/None/根目錄 - 信箱/IPM_SUBTREE/Inbox

方法依据：复现说明。

1. 定位恶意内容本身在原始邮件中的位置。

2. 查看OpenClaw会话输入，确认内容经邮件进入处理流程。

3. 把投递载体归类为电子邮件，对应选项A。

验证依据或核验要求：原邮件与会话输入包含同一来源内容。

易错点：攻击目标工具名称不是投递载体；不能执行邮件中的指令来验证。

#### Q89 图片最初存入方式

状态：正式复核。公开结论：B（互联网下载）。

证据定位：CL-01.e01/Operating_System/Users/[用户]/AppData/Local/Google/Chrome/User Data/Default/History；downloads id=8 and downloads_url_chains

方法依据：复现说明。

1. 打开Chrome History中的downloads。

2. 定位下载记录id=8，读取保存目标和下载相关信息。

3. 关联downloads_url_chains，检查该下载的来源与跳转链。

验证依据或核验要求：下载记录证明目标图片以互联网下载方式进入设备，对应B。

易错点：后来复制到其他目录或被Photos打开，不会把最初来源改为拍摄。

#### Q90 Photos最早打开的文件

状态：正式复核。公开结论：WhatsApp Image 2026-08-03 at 16.54.57 (1).jpeg。

证据定位：CL-01.e01/Operating_System/Users/[用户]/AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations/a52b0784bd667468.automaticDestinations-ms；DestList version4; entry_number=1; earliest image entry; all 4 extant records parsed；/case/检材分析数据/未指定持有人/12/用户痕迹/最近访问的项目/data.csv

方法依据：复现说明。

1. 读取a52b0784bd667468.automaticDestinations-ms中的DestList。

2. 按v4结构解析全部4条现存记录，记录目标文件与访问相关时间/序号。

3. 比较图片记录，取本场最早对应entry_number=1的文件。

验证依据或核验要求：与最近访问项目分析表交叉核对，得到该WhatsApp图片名。

易错点：这是现存JumpList范围内的结论，不是证明设备历史上从未打开过其他图片。

### CL-02 WhatsApp与照片

#### Q91 系统版本

状态：正式复核。公开结论：26.5。

证据定位：CL-02.bin/分区1/iDevice_info.txt；line84 and line49

方法依据：复现说明。

1. 打开CL-02分区1的iDevice_info.txt。

2. 读取系统版本字段，核对第84行和第49行相关版本信息。

3. 记录26.5，不把构建号或应用版本当系统版本。

验证依据或核验要求：两处设备属性对照一致。

易错点：不同设备的同名信息文件不可混用。

#### Q92 IANA时区

状态：正式复核。公开结论：C。

证据定位：CL-02.bin/分区1/iDevice_info.txt；line100

方法依据：复现说明。

1. 在CL-02的iDevice_info.txt第100行附近定位时区字段。

2. 读取IANA时区标识，而非只取当前UTC偏移。

3. 按标识语义对应选项C。

验证依据或核验要求：原始时区配置字段提供依据。

易错点：多个IANA时区可能有相同偏移，不能仅凭UTC+8判断唯一地区。

#### Q93 AirDrop标识

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Library/Preferences/com.apple.sharingd.plist；top-level key AirDropID

方法依据：复现说明。

1. 读取com.apple.sharingd.plist，按实际格式解析plist。

2. 定位顶层AirDropID。

3. 保留字符串原值并记录键路径。

验证依据或核验要求：核对来源是sharingd偏好文件的AirDropID。

易错点：设备名称、蓝牙地址、Apple账号与AirDropID不是同一字段。

#### Q94 头像服饰颜色

状态：正式复核。公开结论：C。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Media/Profile/[长编号]-[长编号].jpg；Original WhatsApp own profile photograph

方法依据：复现说明。

1. 在WhatsApp Media/Profile目录定位本机原始头像。

2. 打开完整原图，确认所观察人物及衣着部位。

3. 按可见服饰颜色对应题目选项C。

验证依据或核验要求：以原图目视结果作答，保留图像来源。

易错点：缩略图、压缩色偏或聊天内其他人的头像可能导致误判。

#### Q95 电子名片联系人

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；Sent contact card to [用户]; Ching Fung / +[长编号]

方法依据：复现说明。

1. 在ChatStorage.sqlite定位发送电子名片的消息。

2. 关联名片附件，读取联系人姓名与号码等名片内容。

3. 核对接收方及前后对话，确认题目所问的名片。

验证依据或核验要求：消息、附件和上下文指向同一次名片发送。

易错点：发送者、接收者和名片里的人可能是三个人。

#### Q96 群组唯一标识

状态：待复核或未解。公开结论：未定。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；Two groups exist; preceding venue/preparation context refers to first Tronic Working Group

方法依据：未解后续步骤。

1. 列出ChatStorage.sqlite中候选群组及其会话标识。

2. 追踪题目前后涉及筹备场地的对话，检查是否能唯一承接某一群组。

3. 若题干仍不能排除第二群组，保留两个候选及各自上下文，不强行选一个。

验证依据或核验要求：已有记录确认存在多个群组，单独题面不能唯一定位。

易错点：承接上下文的合理候选不能自动升级为无歧义答案。

结论边界：题目未指明哪一群组；承接前题可支持候选，但单独题面不足以唯一选择。

#### Q97 定时任务失败原因

状态：正式复核。公开结论：D。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 484,485

方法依据：复现说明。

1. 定位ZWAMESSAGE的Z_PK 484和485。

2. 按时间顺序读请求及任务失败回复，确认它们属于同一任务交互。

3. 从回复提取失败原因并对应选项D。

验证依据或核验要求：原因来自实际失败回复而不是对调度配置的猜测。

易错点：任务未执行、执行出错、结果发送失败是不同原因。

#### Q98 询价证券代码

状态：正式复核。公开结论：7709。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 635,636

方法依据：复现说明。

1. 定位ZWAMESSAGE的Z_PK 635和636。

2. 对照询价请求与回应，识别证券代码而非数量或价格。

3. 按题目格式保留代码7709。

验证依据或核验要求：两条相邻消息的语境共同确定代码含义。

易错点：代码应作为字符串处理，不能无条件去掉前导零。

#### Q99 邮件草稿拼写处理

状态：正式复核。公开结论：C。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 505,504

方法依据：复现说明。

1. 读取ZWAMESSAGE第504和505条记录。

2. 比较用户原始邮件草稿与代理关于处理方式的回复。

3. 检查拼写错误被保留还是改正，再对应选项C。

验证依据或核验要求：以原草稿和明确处理回复对照，不能只看润色后的摘录。

易错点：“发现错字”不等于“已经修改错字”。

#### Q100 所传APK原名

状态：正式复核。公开结论：Tronic.apk。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=574 with sender group member and saved contact mapping

方法依据：复现说明。

1. 定位ZWAMESSAGE Z_PK=574及其媒体记录。

2. 核对群组成员发送方与联系人映射，确认题目指向的附件。

3. 将消息附件原名与实际导出APK对应，记录Tronic.apk。

验证依据或核验要求：消息、媒体类型和导出文件相互匹配。

易错点：导出工具生成的UUID文件名不一定是聊天中发送的原始名称。

#### Q101 筹备场地房间

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 292

方法依据：复现说明。

1. 读取ZWAMESSAGE Z_PK=292并向前后扩展查看。

2. 辨别筹备地点的房间号、邻近地点和后续变更是否分别出现。

3. 按本题指定的筹备阶段记录房间。

验证依据或核验要求：结论必须由该阶段的连续对话支持。

易错点：“near某房间”与“就是该房间”语义不同，不能只截取数字。

#### Q102 索取二维码用途

状态：正式复核。公开结论：B。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 715,716,717,718,733,734,735

方法依据：复现说明。

1. 读取Z_PK 715—718及733—735相关记录。

2. 把索取二维码的文字、回应和随后图片按时间配对。

3. 从索取理由确定用途，对应选项B。

验证依据或核验要求：用途由请求语句和前后事件支持。

易错点：二维码图样本身通常不能说明索取人要做什么。

#### Q103 索取二维码次数

状态：正式复核。公开结论：B。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；[用户] chat session Z_PK=3

方法依据：复现说明。

1. 限定题目对象所在会话Z_PK=3。

2. 筛选明确发出索取二维码请求的消息，并按一次请求事件核对。

3. 排除对方发送二维码、确认回复等回应消息后计数。

验证依据或核验要求：计数对象是索取行为，而非图片总数或所有含QR的文字行。

易错点：一次请求可能伴随多条回复，不能逐行累加成多次请求。

#### Q104 聊天提及人员

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK 299,546

方法依据：复现说明。

1. 读取ZWAMESSAGE Z_PK=299和546。

2. 结合前后对话，区分被提及的人员和当前聊天双方。

3. 按题目要求摘录人员名称，保留称呼对应关系。

验证依据或核验要求：人名应由原句中的语法角色和上下文共同定位。

易错点：群成员名单不能替代聊天实际提及人员。

#### Q105 SIM卡ICCID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/iDevice_info.txt；line26 and line50

方法依据：复现说明。

1. 打开CL-02的iDevice_info.txt。

2. 在第26与50行附近核对SIM信息与ICCID字段。

3. 按字符串完整抄录，保留可能的前导零。

验证依据或核验要求：两处SIM相关记录与同一设备对应。

易错点：ICCID、IMSI、IMEI和电话号码不是同一个编号。

#### Q106 桌面端会话Chatroom ID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8; ZCONTACTIDENTIFIER is phone JID, ZCONTACTJID is LID

方法依据：复现说明。

1. 在ChatStorage.sqlite查询ZWACHATSESSION Z_PK=8。

2. 比较ZCONTACTJID和ZCONTACTIDENTIFIER，识别本条记录中的LID与电话JID。

3. 用该会话147条对方文本及23条本机消息的端点核对对应关系。

4. 对照iLEAPP Chat ID取ZCONTACTJID的映射，修正早期误取电话号码字段。

验证依据或核验要求：会话字段、消息端点和独立解析器映射支持相同LID。

易错点：该结论不是火眼聊天表现场验证；单个消息ID前缀也不能泛化为所有版本的客户端定律。

#### Q107 该联系人名称

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8

方法依据：复现说明。

1. 定位与Q106相同的ZWACHATSESSION Z_PK=8。

2. 读取该条的联系人显示名字段。

3. 用会话标识保持对象一致，再抄录名称。

验证依据或核验要求：名称、会话主键和LID位于同一目标会话。

易错点：昵称可变化，不能凭名字相同就认定两条会话为同一人。

#### Q108 该联系人LID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION Z_PK=8

方法依据：复现说明。

1. 保持目标会话Z_PK=8不变。

2. 读取ZCONTACTJID中的LID，而不是ZCONTACTIDENTIFIER中的电话JID。

3. 核对同会话收发消息端点，保留完整后缀。

验证依据或核验要求：本题与Q106最终指向同一个内部LID，符合原字段关系。

易错点：“两题答案相同”不是错误证据，关键是每题都回到正确字段。

#### Q109 联系人发送消息数

状态：正式复核。公开结论：147。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE session 8 received text rows

方法依据：复现说明。

1. 在ZWAMESSAGE限定ZCHATSESSION=8。

2. 按发送方向选出对方发来的文本消息，排除本机发送和系统事件。

3. 计数并检查稳定消息标识是否重复。

验证依据或核验要求：原记录为147条接收文本，去重消息数同样支持147。

易错点：148条含系统事件的接收记录与147条接收文本不是同一口径。

#### Q110 会话主键

状态：正式复核。公开结论：8。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWACHATSESSION primary key

方法依据：复现说明。

1. 由目标消息关联到ZWACHATSESSION。

2. 在目标会话读取Z_PK。

3. 确认值8是数据库本地会话主键，并与Q106对象一致。

验证依据或核验要求：会话关联与主键列一致。

易错点：Z_PK不是JID、LID或全球唯一账号标识。

#### Q111 非原生相机照片

状态：正式复核。公开结论：IMG_0011.JPG。

证据定位：CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.

方法依据：复现说明。

1. 连同匹配WAL打开Photos.sqlite副本。

2. 围绕ZASSET Z_PK=11，关联ZADDITIONALASSETATTRIBUTES和ZCLOUDMASTER对应资源。

3. 读取库内文件名及来源属性，确认目标照片为IMG_0011.JPG。

验证依据或核验要求：关联应依实际外键关系核对，不能因几张表的主键恰好都为11就假定通用连接规则。

易错点：仅有IMG格式文件名不证明它由原生相机拍摄。

#### Q112 拍摄应用

状态：正式复核。公开结论：C。

证据定位：CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.

方法依据：复现说明。

1. 保持Q111同一照片资源。

2. 读取照片来源或导入应用属性，记录应用标识及显示名称。

3. 将该属性与题目选项对应，并说明它能直接证明的是来源/导入应用。

验证依据或核验要求：本场依据照片来源属性得到选项C；若要严格证明拍摄行为，还需要原图元数据或相机生成证据。

易错点：导入应用不必等于实际拍摄应用，答辩时不要扩大字段含义。

#### Q113 照片原始文件名

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.

方法依据：复现说明。

1. 在Q111目标资源的附加属性中定位原始文件名字段。

2. 将原始名称与ZASSET当前库内名称并列比较。

3. 按题目保留原始名称的大小写与扩展名。

验证依据或核验要求：原始名称应与同一个照片资源关联。

易错点：不能把IMG_0011.JPG这个重命名后的库内名称当原始文件名。

#### Q114 Cloud Master GUID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.

方法依据：复现说明。

1. 从目标照片关联到ZCLOUDMASTER对应记录。

2. 读取Cloud Master唯一标识字段。

3. 保留完整字符，核对未误取本地资源UUID或文件名。

验证依据或核验要求：同资源关联链是GUID归属依据。

易错点：不同ID列看起来都像长字符串，但语义不同。

#### Q115 iCloud同步时间

状态：正式复核。公开结论：C。

证据定位：CL-02.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite；ZASSET Z_PK=11; ZADDITIONALASSETATTRIBUTES Z_PK=11; ZCLOUDMASTER Z_PK=11. Original export includes matching WAL.

方法依据：复现说明。

1. 列出目标照片的创建、修改、导入和云相关时间字段。

2. 依据题意确定本场采用的同步时间口径，记录原始字段及值。

3. 按该字段纪元和单位转换，再转UTC+8并对应选项C。

验证依据或核验要求：复现时必须先核对字段语义；导入时间不能在没有解释时直接改称云端同步完成时间。

易错点：同一照片的多个时间相近不代表可以互换。

#### Q116 原图文件传送群组JID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6

方法依据：复现说明。

1. 定位ZWAMESSAGE Z_PK=110、111。

2. 核对消息以文件形式发送且媒体对应目标原图。

3. 关联到ZWACHATSESSION Z_PK=6，读取完整群组JID。

验证依据或核验要求：消息→媒体→会话的关联共同限定群组。

易错点：不能用照片出现在某群缩略图中替代原图以文件发送的证据。

#### Q117 该群组名称

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6

方法依据：复现说明。

1. 沿Q116已确认的会话Z_PK=6。

2. 读取群组标题字段并核对相关消息发生时的群组语境。

3. 按原记录保留名称，而不是抄发送者显示名。

验证依据或核验要求：名称和Q116群组JID必须来自同一会话。

易错点：当前群名与创建时名称可能不同，须按题目时点。

#### Q118 原图文件传送次数

状态：正式复核。公开结论：2。

证据定位：CL-02.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；ZWAMESSAGE Z_PK=110,111; ZWACHATSESSION Z_PK=6

方法依据：复现说明。

1. 限定Q116同一目标原图及群组。

2. 逐条核对Z_PK=110、111的媒体类型和附件对应关系。

3. 按独立发送消息计数，本场为2次。

验证依据或核验要求：两条记录都符合原图以文件发送的口径。

易错点：重试、转发、缩略图和普通图片消息需按题意分别判断，不能只数同名文件。

### 跨检材与Windows内存

#### Q119 跨检材原始照片缺失设备

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：CM-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在所涉手机镜像中分别列出目标消息的附件关系及媒体目录。

2. 核对原图内容与实际文件，不以文件名相同或缩略图存在替代原图。

3. 对未找到原图的设备记录检索路径、已覆盖目录及附件引用，最后比较各设备。

验证依据或核验要求：缺失结论依赖完整的已检查范围；本场记录包含CM-01聊天数据库关联。

易错点：只搜索一个目录无命中，不能声称整部手机没有该图。

#### Q120 内存采集系统时间

状态：正式复核。公开结论：2026-08-07 15:02:29。

证据定位：COM-01_ram.raw；读取 windows.info 的 SystemTime，转换UTC+8。

方法依据：复现说明。

1. 确认COM-01_ram.raw属于对应内存案件。

2. 读取windows.info返回的SystemTime原始时间。

3. 按题意转换UTC+8，记录2026-08-07 15:02:29。

验证依据或核验要求：保留原始UTC及转换过程，避免重复加8小时。

易错点：文件复制时间和采集工具输出文件时间不能替代内存系统时间。

#### Q121 计算器进程PID

状态：正式复核。公开结论：18652。

证据定位：COM-01_ram.raw；从进程列表定位Calculator的真实PID。

方法依据：复现说明。

1. 读取活动进程列表并定位Calculator对应进程。

2. 核对进程名称、PID及状态，必要时与扫描结果区分。

3. 记录实际PID18652。

验证依据或核验要求：PID来自目标进程记录，不由窗口标题推断。

易错点：计算器可涉及多个进程，不要把宿主或父进程PID直接当目标PID。

#### Q122 explorer子进程总数

状态：正式复核。公开结论：14。

证据定位：COM-01_ram.raw；对所有explorer.exe PID求子进程并集，检查父PID语义。

方法依据：复现说明。

1. 找出全部explorer.exe进程及其PID。

2. 在进程记录中筛选PPID属于该集合的直接子进程。

3. 按实际进程身份去重后求并集，本场14个。

验证依据或核验要求：核对父PID与进程创建时间，避免PID复用导致不合理父子关系。

易错点：只统计一个explorer实例或把全部后代当直接子进程都会改变口径。

#### Q123 浏览器明文凭据

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM-01_ram.raw；内存片段与对应浏览器保存凭据记录交叉定位；公开稿不保留秘密值。

方法依据：复现说明。

1. 在既有内存片段中定位浏览器相关凭据上下文。

2. 与相应浏览器保存凭据记录的站点和账号关系交叉定位。

3. 只将题目要求的匹配结果保存在本地，并记录来源片段。

验证依据或核验要求：孤立明文字符串不够，需要站点/账号/浏览器记录的一致关联。

易错点：当前遗留文件未恢复原值及完整偏移，不能把教程示例密码作为本案答案。

#### Q124 最近退出的远控进程

状态：正式复核。公开结论：2026-08-07 11:20:54。

证据定位：COM-01_ram.raw；筛选已终止rustdesk.exe且ExitTime有效的记录，取最大退出时间。

方法依据：复现说明。

1. 筛选rustdesk.exe进程记录。

2. 保留已终止且ExitTime有效的记录，区分仍运行项和残留扫描项。

3. 按退出时间排序取最近一次，按题目时间格式记录。

验证依据或核验要求：本场最终时间2026-08-07 11:20:54；核对该时间是退出而非创建。

易错点：仅按PID大小或列表位置判断“最近”不可靠。

#### Q125 Edge已加载DLL

状态：正式复核。公开结论：ABC（ucrtbase.dll、ntdll.dll、version.dll）。

证据定位：COM-01_ram.raw；检查实际msedge.exe进程的模块加载列表；仅证明加载，不能证明Edge独有或PE直接导入。

方法依据：复现说明。

1. 定位实际名称msedge.exe的目标进程。

2. 读取其模块加载列表并逐项查找ucrtbase.dll、ntdll.dll、version.dll。

3. 记录两份列表的可读范围：172条完整；另一份192条中12条名称不可读。

4. 按“已加载”口径对应ABC，并明确缺失页限制。

验证依据或核验要求：三项在加载记录中有正面命中支持。

易错点：已加载不等于Edge专有，也不等于PE导入表的直接依赖；不可读不等于不存在。

结论边界：题面edge.exe按产品简称处理，实际是msedge.exe；已加载不等于产品专有或PE静态直接导入。

#### Q126 Hive数量最少的用户

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM-01_ram.raw；按用户对应Hive路径计数，处理同名或重复映射。

方法依据：复现说明。

1. 枚举内存中可辨认Hive及其来源路径。

2. 按用户归属分组，处理同名Hive和重复映射。

3. 比较各用户的有效计数，取题目要求的最少者。

验证依据或核验要求：核对分组依据是用户路径/映射，而非相似文件名。

易错点：同一Hive多次映射不能无条件算作多份独立Hive。

#### Q127 采集时仍登录的用户

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM-01_ram.raw；结合登录会话与用户映射，不以目录存在推断仍登录。

方法依据：复现说明。

1. 读取内存中的登录会话相关记录。

2. 将会话身份映射回用户，检查采集时的有效登录状态。

3. 按题目范围列出仍登录用户，区分历史痕迹。

验证依据或核验要求：结论依赖会话状态及用户映射共同支持。

易错点：用户目录、注册表Hive或旧凭据存在，均不独立证明当前仍登录。

### WKH-01 系统属性与隐写

#### Q128 设备制造商

状态：正式复核。公开结论：samsung。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 打开WKH-01的system_backup/shell/getprop/getprop.out。

2. 定位制造商属性，保留键名和完整值。

3. 将samsung与型号、品牌等相邻属性区分后作答。

验证依据或核验要求：原始制造商属性支持samsung。

易错点：不要将芯片厂商误作整机制造商。

#### Q129 设备型号

状态：正式复核。公开结论：SM-G9980。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在同一getprop.out定位产品型号属性。

2. 比较相邻产品名、设备代号，确认题目要求的是型号值。

3. 完整记录SM-G9980。

验证依据或核验要求：设备型号来自原始属性而非外观推断。

易错点：市场宣传名称与内部型号可能不同。

#### Q130 出厂初始API级别

状态：正式复核。公开结论：C。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out找初始API级别对应属性。

2. 同时留意当前SDK字段，确认所取的是设备出厂初始级别。

3. 将初始API值对应选项C。

验证依据或核验要求：以属性名称的初始/当前语义区分数值。

易错点：系统升级后当前SDK提高，不代表设备出厂API随之变化。

#### Q131 安全补丁日期

状态：正式复核。公开结论：2026-01-01。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out定位ro.build.version.security_patch。

2. 读取日期字符串并保持年月日格式。

3. 将2026-01-01作为安全补丁日期。

验证依据或核验要求：该键直接描述补丁日期。

易错点：构建时间和系统安装时间不能替代安全补丁日期。

#### Q132 构建指纹特征

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 找到完整构建指纹并保留原文。

2. 按分隔符拆出品牌、产品/设备、版本、构建与类型等部分。

3. 逐项与题目描述比较，确定选项B。

验证依据或核验要求：让每项判断都对应指纹中的具体段。

易错点：不能只看到某个版本号便推断其余构建特征。

#### Q133 显示构建版本

状态：正式复核。公开结论：AP3A.240905.015.A2.G9980ZHSGHZB1。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out定位面向显示的完整构建版本值。

2. 保留AP3A.240905.015.A2.G9980ZHSGHZB1全部分段。

3. 与Bootloader等相近版本字段并列检查，避免截短。

验证依据或核验要求：完整显示构建字符串与题目格式一致。

易错点：只写尾部G9980版本会丢失前面的Android构建标识。

#### Q134 芯片型号

状态：正式复核。公开结论：SM8350。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out查芯片或平台相关属性。

2. 区分硬件平台、CPU架构与整机型号。

3. 按本题芯片型号记录SM8350。

验证依据或核验要求：核对原属性明确对应芯片/平台对象。

易错点：arm64是架构，SM-G9980是设备型号，都不能替代SM8350。

#### Q135 市场销售代码

状态：正式复核。公开结论：TGY。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 查getprop.out中的销售代码或Carrier ID相关属性。

2. 区分出厂销售区域与当前SIM运营商信息。

3. 记录TGY并按题目格式保留大小写。

验证依据或核验要求：销售代码来自对应设备属性。

易错点：当前使用香港SIM不能单独证明销售区域代码。

#### Q136 SIM移动国家代码

状态：正式复核。公开结论：454。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out定位SIM1运营商数字码。

2. 确认该字段为MCC/MNC组合而非电话号码。

3. 按MCC部分取454。

验证依据或核验要求：先确定SIM槽位再提取国家代码。

易错点：双卡信息、MCC、MNC和销售代码不是同一指标。

#### Q137 出厂语言地区

状态：正式复核。公开结论：D。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 定位设备出厂语言和地区属性。

2. 将其与当前用户语言配置分别列出。

3. 按题目要求用出厂属性对应选项D。

验证依据或核验要求：字段语义明确指向出厂设置。

易错点：当前界面语言可能被用户修改，不能代替出厂地区。

#### Q138 Verified Boot与Bootloader

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 列出verifiedbootstate、锁定状态和相关安全启动属性。

2. 把多个字段放在同一设备状态下解释，排除互相矛盾的理解。

3. 按组合状态对应选项B。

验证依据或核验要求：多项属性共同支持启动验证与锁定状态的判断。

易错点：仅一个布尔值不足以概括全部Verified Boot和Bootloader状态。

#### Q139 用户数据加密方式

状态：正式复核。公开结论：C。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 读取crypto状态与类型属性。

2. 确认用户数据是否加密，并区分文件级加密与全盘加密类型。

3. 将原始属性组合对应选项C。

验证依据或核验要求：同时检查状态与类型，避免只凭encrypted字样选择具体机制。

易错点：“已加密”和“采用哪种加密方式”是不同问题。

#### Q140 完整启动原因

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out找到bootreason相关属性。

2. 保留完整字符串及逗号等后缀信息。

3. 按完整值对应选项B。

验证依据或核验要求：核对未因切分或显示截断丢失后缀。

易错点：bootreason前半段相同的多个值可能表示不同启动上下文。

#### Q141 ADB运行属性绝对偏移

状态：正式复核。公开结论：B。

证据定位：local-artifact/WKH-01/WKH-01/WKH-01.bin；原镜像偏移 0x1F8A9A80

方法依据：复现说明。

1. 在导出属性文本定位init.svc.adbd对应内容。

2. 确定该文本片段在原镜像中的映射位置，而不是只取导出文本内偏移。

3. 使用原镜像绝对字节位置核对目标字符串，本场0x1F8A9A80。

验证依据或核验要求：应能从绝对偏移回读对应属性片段。

易错点：文本行号、文件内偏移与整个镜像绝对偏移三者不能混用。

#### Q142 主要CPU架构

状态：正式复核。公开结论：C。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 在getprop.out定位主要ABI/CPU架构属性。

2. 区分首选ABI与兼容ABI列表。

3. 按题目“主要”架构选择C。

验证依据或核验要求：比较主要字段和兼容列表，确认选的是首选架构。

易错点：设备支持32位应用不代表主要CPU架构是32位。

#### Q143 固件构建时间

状态：正式复核。公开结论：A。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 读取固件构建日期字符串及对应时间戳字段。

2. 按时间戳的单位和显示时区转换。

3. 检查字符串与转换结果是否一致，再对应选项A。

验证依据或核验要求：两种表示方式交叉核对构建时间。

易错点：补丁日期、首次启动时间和固件构建时间不同。

#### Q144 Bootloader版本

状态：正式复核。公开结论：G9980ZHSGHZB1。

证据定位：WKH-01.bin/分区1/system_backup/shell/getprop/getprop.out

方法依据：复现说明。

1. 定位bootloader版本属性。

2. 读取完整G9980ZHSGHZB1，不带入显示构建ID的前缀。

3. 与题目要求的Bootloader对象确认后作答。

验证依据或核验要求：字段来自bootloader而非build display值。

易错点：显示构建版本可能包含同一尾串，但字段含义不同。

#### Q145 Play商店账号

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WKH-01.bin/分区1/data_backup/ABR/device_info.json

方法依据：复现说明。

1. 打开data_backup/ABR/device_info.json。

2. 定位与Play商店关联的账号记录。

3. 核对服务归属后保留对应邮箱原文于本地。

验证依据或核验要求：确认该账号属于目标服务而非设备上任意Google账号。

易错点：多个Google账号同时存在时，不能取第一条邮箱。

#### Q146 云媒体提供程序组件

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.apps.photos.out

方法依据：复现说明。

1. 查看com.google.android.apps.photos.out的包组件转储。

2. 查找云媒体设置相关Action及其匹配的Activity/Intent Filter。

3. 以组件完整身份对应选项B。

验证依据或核验要求：必须确认Action属于该组件的过滤器。

易错点：在整个包文件搜到Action字符串，不足以确定其归属组件。

#### Q147 Drive域名跳转规则

状态：待复核或未解。公开结论：未定。

证据定位：WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.apps.docs.out

方法依据：未解后续步骤。

1. 完整读取com.google.android.apps.docs.out中DriveOpenUrlActivityAlias。

2. 枚举其全部Intent Filter，记录action、category、hostname与path条件。

3. 将各候选域名逐一代入对应过滤器，检查是否同时允许多个候选。

4. 因题目未唯一指定组件/路径而保留未定。

验证依据或核验要求：同一Alias支持多个候选hostname；另一个Launcher过滤器不能取消这些规则。

易错点：不得选择一个孤立命中或按参考答案反推唯一域名。

结论边界：同一DriveOpenUrlActivityAlias匹配多个候选hostname；题目未给组件/路径，不能唯一选。

#### Q148 Gmail实际包名

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.google.android.gm.out

方法依据：复现说明。

1. 打开com.google.android.gm.out。

2. 读取系统登记的包身份，确认它属于Gmail。

3. 按实际包名与题目选项对应B。

验证依据或核验要求：包登记信息比界面应用名称更直接。

易错点：应用显示名可本地化，不能据显示名猜包名。

#### Q149 消息隐写机制

状态：正式复核。公开结论：A（零宽字符隐写）。

证据定位：WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15

方法依据：复现说明。

1. 定位WKH-01已解密WhatsApp聊天中的可疑消息。

2. 导出原始Unicode，逐字符查看码点及不可见字符分布。

3. 确认可见文本外存在有规律的零宽字符编码序列，对应A。

验证依据或核验要求：编码符号分布支持隐写机制判断；解码校验在Q150继续。

易错点：截图或手打会丢失不可见字符，不能作为完整解码输入。

#### Q150 隐写有效载荷还原

状态：正式复核。公开结论：C；完整有效载荷不公开。

证据定位：WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15

方法依据：复现说明。

1. 从同一原始Unicode串按已验证的8种字符映射还原3bit序列。

2. 按实际位序拼出178字节帧，解析magic、nonce、长度及CRC字段。

3. 依题给初态(nonce<<16) OR magic运行xorshift32左13右17左5，并保持32位无符号。

4. 按本案最低位先取规则组装密钥流，与密文异或恢复167字节UTF-8载荷。

5. 验证长度和CRC32后再对应选项C。

验证依据或核验要求：CRC32通过、长度167字节和UTF-8可读共同支持还原；没有访问还原地址。

易错点：不能猜8字符映射或帧字段偏移；本次保留稿缺完整映射，步骤不能当可直接运行的完整脚本。

#### Q151 Threads实际包名

状态：正式复核。公开结论：B。

证据定位：WKH-01.bin/分区1/system_backup/shell/dumpsys/package/com.instagram.barcelona.out

方法依据：复现说明。

1. 读取com.instagram.barcelona.out包转储。

2. 确认其中系统登记的包身份与Threads相对应。

3. 用实际注册名匹配选项B。

验证依据或核验要求：原包身份是证据，不能仅根据应用图标。

易错点：商店名称与包标识不要求字面相同。

#### Q152 联系人底层LID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15

方法依据：复现说明。

1. 在已解密WhatsApp数据定位目标一对一会话。

2. 关联联系人映射，分别列出手机号JID和内部LID。

3. 用消息发送/接收端点核对底层LID并对应题目。

验证依据或核验要求：同一会话与联系人映射共同支持目标标识。

易错点：不要将CL-02的同名字段结构未经核查直接套用Android数据库。

#### Q153 场地变更后的房间

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15

方法依据：复现说明。

1. 检索场地安排的连续聊天并按时间排序。

2. 标出旧地点、提出变更和确认变更的消息。

3. 取题意要求的最后有效房间，保留上下文。

验证依据或核验要求：后续明确变更覆盖旧安排，而非仅按最先命中的房间号。

易错点：引用旧地点的消息可能晚于变更，不等于又改回旧地点。

#### Q154 现场人数

状态：正式复核。公开结论：D。

证据定位：WKH-01.bin/分区1/media/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15

方法依据：复现说明。

1. 定位要求清点现场人数的消息。

2. 找到紧随其后与该请求对应的回复。

3. 从回复提取现场人数并对应D。

验证依据或核验要求：计数依据是现场清点报告。

易错点：聊天参与者、群成员数与实际到场人数不同。

### WC-01 聊天与APK

#### Q155 指定通话时长

状态：正式复核。公开结论：36。

证据定位：WC-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata

方法依据：复现说明。

1. 打开WC-01的CallHistory.storedata。

2. 按题目对象、时间和呼出方向筛选目标通话。

3. 读取实际duration，核对通话状态后记录36秒。

验证依据或核验要求：时长字段与目标呼出记录一致。

易错点：振铃时间、失败拨号尝试或邻近另一次通话不能混入。

#### Q156 WhatsApp来电号码

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WC-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata

方法依据：复现说明。

1. 在WC-01通话记录中限定WhatsApp来源。

2. 定位题目所指的来电并读取发起方标识。

3. 将发起方对应到号码，保留国家区号和题目要求格式。

验证依据或核验要求：应用来源、来电方向与号码属于同一通话。

易错点：设备机主号码、被叫号码和来电号码角色不同。

#### Q157 VIP购买页面路由

状态：正式复核。公开结论：ProductShop。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite；local-artifact/team/members/P01_CL02/exports/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/d/3/[UUID].apk

方法依据：复现说明。

1. 从同案聊天APK提取assets/index.android.bundle并确认Hermes96格式。

2. 解析字符串、函数及指令，定位AppNavigator函数6931注册的ProductShop。

3. 跟踪UserDashboard函数9414的VIP条件与onPress闭包。

4. 在函数9427确认navigation.navigate参数为ProductShop，再检查函数9446页面内容。

5. 将该路由与WC聊天中的VIP授权变化关联。

验证依据或核验要求：注册路由、VIP入口、实际跳转参数和页面内容形成闭环。

易错点：只搜到ProductShop字符串不够；COM-02对应TSX复核未完成，不能声称所有源码版本已核验。

结论边界：WC聊天与同案CL-02导出APK已独立核验；COM-02相应TSX源码交叉检查尚未完成。

#### Q158 指定批次附件类型

状态：正式复核。公开结论：D。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在WC-01 ChatStorage.sqlite限定题目所指同一批消息。

2. 逐条关联媒体项，读取媒体类型及附件元数据。

3. 汇总实际出现的类型，按选项D作答。

验证依据或核验要求：每种类型须能回到本批次具体消息。

易错点：只看文件扩展名不能保证知道聊天软件采用的发送类型。

#### Q159 照片发送附件类型

状态：正式复核。公开结论：C。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 定位目标照片对应的消息记录。

2. 关联媒体项并读取消息类型和附件元数据。

3. 判断它作为图片还是文件等类型发送，再对应C。

验证依据或核验要求：发送类型来自消息/媒体记录，而非照片能否被图片查看器打开。

易错点：同一JPEG可作为照片消息或文档文件发送。

#### Q160 订单照片中的商品

状态：正式复核。公开结论：C。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 由订单消息关联到原始订单照片文件。

2. 打开完整图像，读取商品名称、数量等可见内容。

3. 将照片中的商品内容与题目选项核对，得到C。

验证依据或核验要求：商品应由原图直接支持，必要时与相邻订单对话对应。

易错点：ProductShop是页面路由，不是照片中购买的商品名称。

#### Q161 指定文字的消息ID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在ChatStorage.sqlite按指定原文检索消息。

2. 核对发送者、会话和时间，排除转述或重复文本。

3. 从匹配记录读取稳定消息ID并完整保留。

验证依据或核验要求：原文命中与消息上下文共同确定唯一记录。

易错点：数据库自增主键不一定是题目要求的跨设备消息ID。

#### Q162 实体取货位置

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 围绕实体取货安排读取连续对话。

2. 区分预约地点、实际确认地点及后续修改。

3. 按题目所指时点记录具体位置与证据消息。

验证依据或核验要求：位置由上下文确认，不能只凭某一地名出现。

易错点：聊天中的地址也可能是公司地址、旧地点或邻近地标。

#### Q163 Safari搜索词

状态：正式复核。公开结论：yahoo finance。

证据定位：WC-01.bin/分区1/var/mobile/Library/Safari/History.db

方法依据：复现说明。

1. 打开WC-01 Safari History.db。

2. 定位目标搜索访问URL，读取其实际检索参数。

3. 正确URL解码，保留词间空格与大小写，得到yahoo finance。

验证依据或核验要求：搜索词应能从对应URL参数还原。

易错点：页面标题、网站名和搜索词不是同一字段。

#### Q164 Signal包标识

状态：正式复核。公开结论：org.whispersystems.signal。

证据定位：WC-01.bin/分区1/var/Manifest.plist

方法依据：复现说明。

1. 解析WC-01的var/Manifest.plist。

2. 在应用登记信息中定位Signal。

3. 读取Bundle Identifier，记录org.whispersystems.signal。

验证依据或核验要求：应用身份与Bundle Identifier相互对应。

易错点：安装目录名、应用显示名称或商店链接不能替代Bundle ID。

#### Q165 图片实际存储路径

状态：正式复核。公开结论：B。

证据定位：WC-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 定位题目图片对应的聊天消息。

2. 沿媒体项读取真实媒体相对路径，并拼接到正确应用容器。

3. 确认该路径实际指向原图文件，再对应B。

验证依据或核验要求：数据库路径与真实文件内容相互核对。

易错点：缩略图或缓存路径可能可打开，但不等于原图存储路径。

#### Q166 HEIC原始GPS

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WC-01.bin/分区1/var/mobile/Media/DCIM/100APPLE/IMG_0010.HEIC；WC-01.bin/分区1/var/mobile/Media/PhotoData/Photos.sqlite

方法依据：复现说明。

1. 读取WC-01的IMG_0010.HEIC原文件EXIF GPS。

2. 记录经纬度方向及原始数值，按题意转换展示格式。

3. 与Photos.sqlite位置记录对照，存在尾数差异时以题目指定原图口径作答。

验证依据或核验要求：原文件元数据是本题的直接证据。

易错点：纬度经度顺序、南西负号及提前四舍五入都可能造成错误。

### WW-01 手机与附件

#### Q167 系统版本

状态：正式复核。公开结论：26.6。

证据定位：WW-01.bin/分区1/iDevice_info.txt；line 83

方法依据：复现说明。

1. 打开WW-01的iDevice_info.txt。

2. 在第83行附近读取系统版本字段。

3. 记录26.6并核对文件确实来自WW-01。

验证依据或核验要求：设备身份和版本字段一致。

易错点：不要使用CL-02的26.5或某应用版本替代。

#### Q168 设备序列号

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/iDevice_info.txt；line 91

方法依据：复现说明。

1. 在WW-01 iDevice_info.txt第91行附近定位序列号。

2. 区分Serial Number与UDID、IMEI等标识。

3. 按字符串保留序列号原值和大小写。

验证依据或核验要求：明确字段名及同一设备归属。

易错点：外形相似的设备标识不能互换。

#### Q169 主要认证邮箱

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/iDevice_info.txt；line 300

方法依据：复现说明。

1. 读取WW-01 iDevice_info.txt第300行附近账号信息。

2. 根据认证服务及字段含义确定主要认证邮箱。

3. 完整记录邮箱原文，并与设备其他联系人邮箱区分。

验证依据或核验要求：认证记录而非任意通讯录邮箱支撑答案。

易错点：多个账号同时出现时，不能把列表第一项默认当主要认证账号。

#### Q170 服务绑定电话

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Library/Preferences/group.net.whatsapp.WhatsApp.shared.plist；FullUserName, OwnJabberID, LastOwnJabberID

方法依据：复现说明。

1. 解析group.net.whatsapp.WhatsApp.shared.plist。

2. 并列查看FullUserName、OwnJabberID、LastOwnJabberID等本机账号相关值。

3. 核对现有与历史身份是否一致，按题目服务绑定电话口径提取号码。

验证依据或核验要求：本机WhatsApp账号身份与号码映射支持结果。

易错点：LastOwnJabberID可能是历史值，不能无条件覆盖当前账号。

#### Q171 来电所用应用

状态：正式复核。公开结论：C。

证据定位：WW-01.bin/分区1/var/mobile/Library/CallHistoryDB/CallHistory.storedata；ZCALLRECORD Z_PK=5

方法依据：复现说明。

1. 打开WW-01 CallHistory.storedata。

2. 定位ZCALLRECORD Z_PK=5，核对来电对象和时间。

3. 读取应用来源标识，将其对应到服务选项C。

验证依据或核验要求：来源标识属于同一目标来电记录。

易错点：不能因为某号码在WhatsApp联系人里就断定来电使用WhatsApp。

#### Q172 Signal注册验证码

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Library/SMS/sms.db

方法依据：复现说明。

1. 只读打开WW-01 sms.db副本。

2. 筛选Signal注册相关短信并核对发送来源、正文和时间。

3. 读取该次注册验证码，按题意原样保留本地。

验证依据或核验要求：以短信正文明确的服务及注册语境确认验证码归属。

易错点：登录码、注册号、短信发送号码可能同时为数字，不能混取。

#### Q173 储物柜图片路径

状态：正式复核。公开结论：C。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；original file plus ChatStorage.sqlite ZWAMESSAGE Z_PK=295 / ZWAMEDIAITEM Z_PK=277

方法依据：复现说明。

1. 在ChatStorage.sqlite定位ZWAMESSAGE Z_PK=295。

2. 沿关联查ZWAMEDIAITEM Z_PK=277，读取媒体路径。

3. 打开该路径的原图确认储物柜内容，得到题目对应路径。

验证依据或核验要求：消息、媒体项及图像内容三者一致。

易错点：按文件名搜索到别的同名图片或缩略图不能算完成定位。

#### Q174 图片原始字节数

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；entire original file byte count; ZWAMEDIAITEM Z_PK=277 ZFILESIZE

方法依据：复现说明。

1. 沿Q173路径取得同一个原始JPEG文件。

2. 读取完整文件字节长度，包含原文件中实际存在的全部字节。

3. 与ZWAMEDIAITEM Z_PK=277的ZFILESIZE对照。

验证依据或核验要求：实际长度与媒体记录相互核验。

易错点：不能用重保存后的图像大小或只算第一JPEG图像流长度。

#### Q175 交接地点

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；second JPEG stream beginning at byte 76934

方法依据：复现说明。

1. 对Q173原JPEG检查是否存在额外图像流。

2. 从字节76934开始读取第二JPEG流并在派生副本中查看。

3. 从图像内容提取交接地点，再与聊天语境交叉核对。

验证依据或核验要求：地点来自第二JPEG流及对应消息，而非第一幅储物柜图的猜测。

易错点：普通图片查看器可能只显示第一幅图，不能据此认定文件只有一张图像。

#### Q176 收款钱包

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/b/3/[UUID].jpg；second JPEG stream beginning at byte 76934

方法依据：复现说明。

1. 读取同一文件字节76934开始的第二JPEG流。

2. 在完整图像中辨认收款钱包信息，并与相关文字上下文核对。

3. 按题目选项或完整地址格式作答，保留原始字符。

验证依据或核验要求：图像中的钱包信息与交易语境共同支持归属。

易错点：不能把发款方、收款方或交易哈希互相替代；OCR结果需目视核对。

#### Q177 发送图片主文件名

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 定位题目指定发送图片的聊天记录。

2. 读取该附件的原始文件名，而不是导出时生成的随机名称。

3. 按题意去掉最后的扩展名，保留主文件名中的其他点号和连字符。

验证依据或核验要求：文件名必须属于目标发送消息的媒体项。

易错点：去扩展名不等于把文件名从第一个点开始全部截断。

#### Q178 转账交易哈希

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/3/f/[UUID].jpg；ASCII appended after JPEG EOI

方法依据：复现说明。

1. 由对应聊天附件取得指定原JPEG。

2. 检查JPEG EOI之后的剩余字节，提取追加ASCII文本。

3. 按交易语境识别其中转账交易哈希并保留完整字符。

验证依据或核验要求：值来自图像尾部追加内容，能够回到原文件具体位置。

易错点：对JPEG整体计算文件哈希，得不到题目要求的交易哈希。

#### Q179 群组创建时间

状态：正式复核。公开结论：2026-07-30 17:11:36。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在目标群组聊天中定位创建系统事件。

2. 读取事件时间，核对时间纪元和单位。

3. 转换UTC+8后记录2026-07-30 17:11:36。

验证依据或核验要求：使用创建事件而不是现存最早普通消息。

易错点：数据库创建时间或加入群组时间不一定是群组创建时间。

#### Q180 群组原始名称

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 先定位群组创建事件及其当时标题。

2. 再检查后续改名系统事件，建立名称随时间变化的顺序。

3. 按题目“原始名称”使用创建时名称。

验证依据或核验要求：原名由创建及改名事件链支持。

易错点：当前会话标题可能已被后续改名覆盖。

#### Q181 指定房间

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在WW-01目标会话中定位题目指定消息。

2. 读取前后上下文，确认房间号用于题目所述活动。

3. 保留该阶段有效房间，不混用其他检材的场地变更结论。

验证依据或核验要求：题目消息、活动和房间三者对应。

易错点：同一案件出现多个房间，不能仅按数字出现次数决定答案。

#### Q182 二维码用途

状态：正式复核。公开结论：D。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/Message/Media/[标识已脱敏]/9/3/[UUID].jpg；QR decoded offline via OpenCV QRCodeDetector.detectAndDecode

方法依据：复现说明。

1. 沿聊天媒体关系取得指定二维码原图。

2. 使用离线二维码解码结果识别内容，本场采用OpenCV QRCodeDetector.detectAndDecode。

3. 结合索取与发送前后消息判断业务用途，选择D。

验证依据或核验要求：二维码内容与聊天语境共同支持用途；无需访问解码出的地址。

易错点：解码成功仅说明能读取内容，不证明其中网站安全或请求已执行。

#### Q183 申请VIP的注册账号

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：WW-01.bin/分区1/var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

方法依据：复现说明。

1. 在ChatStorage.sqlite定位申请VIP的原始消息。

2. 读取申请中明确给出的注册账号，核对申请人和上下文。

3. 保留账号大小写及数字，不用聊天昵称替代。

验证依据或核验要求：注册账号直接来自申请文本。

易错点：显示名、电话号码和业务注册账号可能完全不同。

### COM-02 服务器与数据库

#### Q184 Graph token文件大小

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：先在宿主共享项目定位Graph token候选文件，记录其宿主路径及项目归属。

2. 对比虚拟机内同名副本，按题目指定来源选择目标，不混用不同修改时间的副本。

3. 读取目标文件的逻辑字节长度，并连同文件名、路径记录。

验证依据或核验要求：需要同一目标文件的目录记录和导出后字节长度相符；原始证据闭环未完成。

易错点：不能用磁盘占用空间、编辑器字符数或另一个同名文件大小代替。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q185 Graph token文件名与SHA256

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：复用Q184确定的同一Graph token文件，先确认文件名与来源层级。

2. 在只读导出副本上按题目要求计算SHA256，保留文件路径、字节长度和计算结果。

3. 将原始目录中的文件名与所计算文件对应，避免将其他副本的哈希拼在一起。

验证依据或核验要求：需能证明文件名、大小、SHA256来自同一份文件；当前不能将参考哈希当复验值。

易错点：只知道参考答案中的长字符串不等于完成哈希验证。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q186 Qwen工具调用解析器

状态：正式复核。公开结论：hermes。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/start_qwen_8000.sh；vLLM launch arguments --tool-call-parser

方法依据：既有记录复述。

1. 从WSL导出/home/[用户]/start_qwen_8000.sh，以文本方式读取。

2. 定位vLLM启动参数中的--tool-call-parser，检查参数是否续行以及是否处于实际启动命令。

3. 读取该参数值hermes，并与其他模型启动脚本区分。

验证依据或核验要求：原脚本参数支持hermes；没有执行启动脚本。

易错点：不要把模型家族名或Hermes字节码格式当本题工具调用解析器的来源。

#### Q187 移动访问令牌有效小时

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位当前移动服务配置中访问令牌有效期的定义。

2. 追踪配置是默认常量还是被环境变量覆盖，并确认运行项目版本。

3. 根据字段单位将有效期换算为小时，保留原值和换算过程。

验证依据或核验要求：需验证实际配置来源及单位；目前没有完成当前服务证据闭环。

易错点：访问令牌有效期与刷新令牌、会话失效时间不是同一配置。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q188 默认Session Secret

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位服务会话配置中的Session Secret定义。

2. 检查题目所问的是默认值还是运行时值，分别记录代码回退值与环境覆盖关系。

3. 仅在本地保留对应秘密值及字段定位，公开稿保留方法。

验证依据或核验要求：需证明所读值确实属于目标服务会话配置；当前未完成复核。

易错点：不能用任意API key、数据库口令或其他服务的Secret替代。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q189 二维码请求客户端版本

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：将题给本地时间换算到请求日志所用时区，明确筛选窗口。

2. 在该窗口筛选二维码端点及目标设备的请求元数据。

3. 从同一请求记录读取客户端版本，保留状态码与请求标识用于关联。

验证依据或核验要求：时间、端点、设备和版本须属于同一事件；当前未完成原始日志复验。

易错点：旧APK静态版本不一定等于该次请求的客户端版本。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q190 二维码请求端点

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在访问日志按题目时段及二维码操作筛选请求。

2. 读取记录中的方法和完整URI，分清路径与查询参数。

3. 以对应后端路由作交叉核对，记录实际被访问的路径。

验证依据或核验要求：实际请求日志应支持端点；APK字符串只能提示候选。

易错点：可能存在相似的生成、获取、刷新二维码路径，不能只匹配qr关键字。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q191 管理员二维码页面源码

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在目标前端项目定位管理员二维码功能的页面文件。

2. 沿路由配置的导入与组件引用找到实际被挂载页面。

3. 查看页面是否包含题目所指二维码操作及对应请求调用，记录源文件相对路径。

验证依据或核验要求：文件、路由和功能调用需形成完整关系；当前源码复核未完成。

易错点：相似组件名、翻译文字或未被引用的旧页面不能直接作答。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q192 币价刷新秒数

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位币价获取/刷新逻辑及其配置项。

2. 查定时器或调度参数，判断原值单位是毫秒、秒还是其他单位。

3. 按题目要求换算为秒，并核对是否存在不同页面或服务的刷新频率。

验证依据或核验要求：需要代码使用处证明参数单位及目标功能；当前未完成。

易错点：不能把Token有效期、请求超时或缓存TTL当币价刷新间隔。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q193 DHCP精确MAC对应主机

状态：待复核或未解。公开结论：未定。

证据定位：COM-02宿主 ProgramData/VMware 的DHCP租约及备份；Tronic_s2轮转vmware日志。

方法依据：未解后续步骤。

1. 建议后续核验：读取COM-02宿主ProgramData/VMware的DHCP租约及备份。

2. 将题目MAC按六个字节精确比较，关联匹配记录的主机字段。

3. 再对照Tronic_s2轮转vmware日志中的网卡记录，保留fc与6c的一字节差异。

验证依据或核验要求：已见实际记录与题面并非精确一致，仍为未解冲突。

易错点：近似MAC和相近主机名不是精确映射的证明。

结论边界：题面MAC一字节为fc，实际租约及另一VM日志为6c；相近标识仅是候选，不能声称精确命中。

#### Q194 结算关联表外键目标

状态：成员复现待主复核。公开结论：A（transactions）。

证据定位：Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql

方法依据：复现说明（成员复现待主复核）。

1. 在共享项目setup.sql中定位结算关系及transaction_id列。

2. 读取该列的FOREIGN KEY或REFERENCES定义，记录目标表及目标列。

3. 将目标表名称与选项核对，成员结果为transactions。

验证依据或核验要求：setup.sql外键定义支持选项A；属于成员复现待主复核。

易错点：不能仅因字段名叫transaction_id就猜目标表。

#### Q195 数据库IP与端口

状态：成员复现待主复核。公开结论：[敏感值不公开]。

证据定位：Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/config.py

方法依据：复现说明（成员复现待主复核）。

1. 读取共享项目app/config.py中的数据库连接配置。

2. 把主机、端口、用户名和库名拆开记录，确认默认值所用的环境变量或回退路径。

3. 继续核对当前VM运行环境是否覆盖默认值；这一覆盖关系当时未完成。

验证依据或核验要求：目前只支持共享项目默认连接配置，不能声称已确认当前运行地址。

易错点：默认配置与部署环境实际连接目标可能不同。

结论边界：共享项目默认配置已复现，当前VM运行配置覆盖关系尚待核对。

#### Q196 营业时段已完成结算批次

状态：成员复现待主复核。公开结论：4。

证据定位：/var/lib/postgresql/18/main/base/16389/49490

方法依据：复现说明（成员复现待主复核）。

1. 通过PostgreSQL catalog及pg_filenode.map确定业务库与结算表的物理文件；本案业务库OID16389、实际文件49490。

2. 解析页与tuple，结合事务状态和标志筛掉不可见或历史版本。

3. 根据应用写入时间语义，把香港09:00—17:00对应到UTC01:00—09:00，再筛completed。

4. 对满足全部条件的当前有效记录计数，成员结果4条。

验证依据或核验要求：成员记录中37条有效结算记录经同一筛选得到4条；需主复核确认。

易错点：表OID49278不等于实际relfilenode49490；xmax非零也不必然删除。

#### Q197 金额字段加密格式

状态：成员复现待主复核。公开结论：fernet。

证据定位：Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/tronic_amount_crypto.py；Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql；/var/lib/postgresql/18/main/base/16389/49490

方法依据：复现说明（成员复现待主复核）。

1. 读取tronic_amount_crypto.py中的加解密实现，核对数据库字段设计。

2. 确定v1前缀与实际令牌的分离方式，再按源码调用格式识别Fernet。

3. 对匹配记录执行认证解密，保留认证成功与明文类型检查结果。

验证依据或核验要求：源码与令牌认证解密共同支持Fernet，当前为成员复现。

易错点：仅看Base64外观或前缀不能证明具体加密格式。

#### Q198 已完成结算金额合计

状态：成员复现待主复核。公开结论：14194443.00。

证据定位：/var/lib/postgresql/18/main/base/16389/49490

方法依据：复现说明（成员复现待主复核）。

1. 使用Q196同一组4条有效结算记录，固定记录标识与筛选条件。

2. 按Q197确认的格式逐条认证解密金额，并按Decimal读取。

3. 将1000000、580000、12134443、480000求和，得到14194443.00。

4. 核对输出币种和小数位是否符合题目。

验证依据或核验要求：四笔金额与筛选集合一一对应；成员结果待主复核。

易错点：不要更换记录集合、混入未完成批次或用浮点累加引入精度差。

#### Q199 三类邮件状态字段

状态：成员复现待主复核。公开结论：A（email_status、bank_email_status、otc_email_status）。

证据定位：Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/setup.sql；Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/models.py

方法依据：复现说明（成员复现待主复核）。

1. 在setup.sql中定位结算邮件相关状态列。

2. 对照app/models.py同一模型，分别记录普通、银行及OTC邮件状态字段。

3. 按原字段名保留email_status、bank_email_status、otc_email_status并匹配选项。

验证依据或核验要求：DDL与模型定义相互支持成员选项A。

易错点：状态字段不等于收件地址、发送时间或布尔成功显示文字。

#### Q200 数据库口令候选核验

状态：成员复现待主复核。公开结论：[敏感值不公开]。

证据定位：/var/lib/postgresql/18/main/global/1260

方法依据：复现说明（成员复现待主复核）。

1. 从目标PG数据目录的角色记录取得对应SCRAM验证器，确认角色关联。

2. 只对题目给定候选按验证器参数进行离线派生。

3. 分别比较派生的StoredKey与ServerKey，记录匹配候选及验证方式。

验证依据或核验要求：成员执行的是离线候选校验，没有网络登录；待主复核。

易错点：不能把SCRAM验证器当明文密码，也不能说成功登录了数据库。

#### Q201 数据库连接用户

状态：成员复现待主复核。公开结论：[敏感值不公开]。

证据定位：Com-02.e01/分区6/Users/[用户]/Documents/Virtual Machines/Tronic/share/tronic-investment/app/config.py

方法依据：复现说明（成员复现待主复核）。

1. 读取共享项目app/config.py中的数据库用户名定义。

2. 区分代码默认值与环境变量读取路径。

3. 继续核对当前VM部署配置是否覆盖；未完成时明确只代表默认配置。

验证依据或核验要求：共享项目默认用户名有成员复现，运行覆盖关系仍待核对。

易错点：Linux登录用户名、PostgreSQL角色名与应用登录账号可能不同。

结论边界：共享项目默认配置已复现，当前VM运行配置覆盖关系尚待核对。

#### Q202 Tronic操作系统与内存

状态：成员复现待主复核。公开结论：B（Ubuntu 64-bit、4096MiB）。

证据定位：local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/Tronic.vmx；guestOS; memsize

方法依据：复现说明（成员复现待主复核）。

1. 读取Tronic/Tronic.vmx，确认该文件对应题目目标VM。

2. 查guestOS和memsize原始配置。

3. 将操作系统标识与内存单位解释为Ubuntu 64-bit、4096MiB并匹配选项。

验证依据或核验要求：VMX配置支持成员选项B，未提升为主复核结论。

易错点：配置内存不是宿主总内存，也不是当时已用内存。

#### Q203 第一块网卡硬件型号

状态：成员复现待主复核。公开结论：e1000。

证据定位：local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/Tronic.vmx；ethernet0.virtualDev

方法依据：复现说明（成员复现待主复核）。

1. 在同一Tronic.vmx中定位ethernet0配置组。

2. 读取ethernet0.virtualDev，保留原值e1000。

3. 检查没有误读ethernet1或宿主物理网卡信息。

验证依据或核验要求：第一块虚拟网卡的配置项支持e1000，属于成员复现。

易错点：网卡MAC、连接模式和虚拟硬件型号是三个不同字段。

#### Q204 独立数据库虚拟机名

状态：成员复现待主复核。公开结论：Tronic_s2。

证据定位：local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic_s2/Tronic_s2.vmx；displayName

方法依据：复现说明（成员复现待主复核）。

1. 读取Tronic_s2目录的VMX配置及displayName。

2. 将目录路径、配置文件和虚拟磁盘所属关系对应起来。

3. 结合数据库角色证据确认该VM是题目所指独立数据库VM，成员结果Tronic_s2。

验证依据或核验要求：名称与角色需共同对应；当前仍为成员复现待主复核。

易错点：目录名相似不代表已证明服务角色，不能只按s2后缀猜测。

#### Q205 下午首次异常关机后启动

状态：待复核或未解。公开结论：未定。

证据定位：COM-02宿主 Tronic虚拟机目录全部vmware*.log、mksSandbox日志及VMware宿主日志。

方法依据：未解后续步骤。

1. 建议后续核验：汇集目标Tronic目录的轮转vmware日志、mksSandbox及宿主相关日志。

2. 按事件原始时区排序，区分启动时读入DICT cleanShutdown与运行中Setting FALSE。

3. 对本地下午的启动逐条检查上一关机状态，再与上午异常启动分开。

验证依据或核验要求：已检异常启动在上午；下午读入TRUE，题面与证据冲突未解。

易错点：运行中把cleanShutdown设FALSE是状态变化，不能直接等同上一次崩溃。

结论边界：已检日志中的两次异常关机启动均在本地上午；下午启动读入cleanShutdown=TRUE。运行中的Setting FALSE不表示上次异常退出，题证冲突未解。

#### Q206 工作区加载另一虚拟机的时间

状态：成员复现待主复核。公开结论：B（04:07:48 UTC）。

证据定位：local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/vmware.log；line 270

方法依据：复现说明（成员复现待主复核）。

1. 在Tronic/vmware.log定位含另一VMX路径的Workspace Session记录。

2. 保留该行上下文，确认事件是工作区加载对应VM而非其业务启动。

3. 读取记录时间04:07:48 UTC，并按题目时间口径匹配选项。

验证依据或核验要求：成员定位为vmware.log第270行；结论待主复核。

易错点：工作区加载时间不必等于客体操作系统启动或用户登录时间。

#### Q207 首次虚拟磁盘锁定错误

状态：成员复现待主复核。公开结论：A（2026-08-03 11:52:03 UTC+8）。

证据定位：local-artifact/gpt/P01_COM02_HOST/exports/Users/[用户]/Documents/Virtual Machines/Tronic/vmware-2.log；line 673

方法依据：复现说明（成员复现待主复核）。

1. 扫描目标Tronic的全部轮转vmware日志中的虚拟磁盘锁定错误。

2. 按原始时间排序，不按文件名编号顺序推定先后。

3. 定位最早匹配事件并转换题目要求时区，成员结果2026-08-03 11:52:03 UTC+8。

验证依据或核验要求：成员定位vmware-2.log第673行，并以全轮转范围比较；待主复核。

易错点：仅在当前vmware.log搜到第一条不一定是整个保留范围的第一次。

#### Q208 指定价格请求源IP

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：把题目指定分钟换算到日志时区。

2. 分别检查/api/price与/api/prices实际记录，明确单复数路径差异。

3. 在满足题目请求条件的记录上读取来源字段，并核对代理转发语义。

验证依据或核验要求：需保留实际请求行和来源字段定义；尚未闭环。

易错点：不能把相似端点、相邻请求或upstream地址当客户端来源。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q209 代理转发后端节点

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：先固定题目所指请求的时间、方法、URI及请求标识。

2. 在代理日志查同一请求的转发/upstream记录。

3. 读取实际选择的后端节点，结合配置解释其角色。

验证依据或核验要求：同一请求的代理关联记录才支持节点结论；当前未完成。

易错点：配置中列出的所有后端不等于该次请求实际命中的后端。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q210 生成二维码请求ID

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：联合筛选来源、时段、成功响应和生成二维码端点。

2. 定位唯一目标请求后读取request ID原值。

3. 检查是否因重试产生多条相近请求，保留与题目吻合的一条及理由。

验证依据或核验要求：需要完整筛选条件和目标行；当前仍未定。

易错点：不能从另一条二维码获取请求借用ID。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q211 Nginx实际访问日志名

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：读取目标服务实际启用的Nginx配置及其包含关系。

2. 定位生效server/location中的access_log设置。

3. 将日志文件名与磁盘实际日志对应，区分HTTP配置与HTTPS模板。

验证依据或核验要求：需要有效配置链及日志存在证据；当时未完成。

易错点：项目内模板文件不自动证明其已被Nginx加载。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q212 指定价格请求源IP选项

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：明确指定时段及价格请求路径，并将时间统一。

2. 筛选满足成功条件的请求，按时间排序。

3. 从第一个符合条件的记录读取来源IP，再与选项逐项比较。

验证依据或核验要求：第一个成功请求的完整记录是验证对象；当前未完成。

易错点：不能用第一条任意请求或相邻行的来源替代。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q213 API代理监听端口

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位API代理的启动命令或服务配置。

2. 读取实际绑定地址和端口，区分前端HTTPS、代理及后端端口。

3. 结合启动/运行日志核对生效监听值。

验证依据或核验要求：配置与运行记录应共同支持端口；当前未复现。

易错点：请求URL上的端口可能属于上游入口，不是该API代理自身监听端口。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q214 二维码请求IP与ID组合

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：按题目条件筛选成功的二维码POST请求。

2. 在同一条记录读取来源IP及request ID，保留时间、URI、状态。

3. 检查相关日志字段是否经过代理重写或使用转发头。

验证依据或核验要求：IP和ID必须出自同一事件；目前未完成。

易错点：分别在两条日志找到正确格式的值，拼在一起并不构成答案。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q215 登录设备UA与系统版本

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：按题给日期、时段与设备型号筛选登录事件。

2. 核对事件是登录成功而非失败、刷新令牌或普通访问。

3. 从同一事件读取UA和系统版本，保留原始大小写和版本段。

验证依据或核验要求：设备、成功状态与元数据需对应同一记录；当前未完成。

易错点：网页UA与应用上报设备元数据可能不同，应按题目指定字段。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q216 登录设备唯一标识

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：复用Q215已确定的同一次登录事件。

2. 读取该记录的Device ID并核对关联设备信息。

3. 检查是否存在会话ID、广告ID等其他标识，明确字段名称后作答。

验证依据或核验要求：需目标登录记录支持Device ID；目前无完整复验。

易错点：不能把用户ID、请求ID或设备型号当设备唯一标识。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q217 客户端版本与构建号

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位题目对应请求的设备/客户端元数据。

2. 分别读取app_version与app_build，保持版本字符串及构建号格式。

3. 与同一登录或操作记录关联，排除其他安装版本。

验证依据或核验要求：同一请求提供版本和构建号才支持组合答案；未完成。

易错点：不能用聊天中较早APK的Manifest版本替代后来请求上报的版本。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q218 日报主要收件人

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位结算日报所用服务的邮件环境配置。

2. 追踪日报发送逻辑使用哪个收件变量，而非只搜索任意邮箱。

3. 读取主要收件人字段，并与抄送、银行和OTC地址区分。

验证依据或核验要求：需发送类别与配置变量对应；当前未完成。

易错点：参考邮件收件人或其他通知地址不自动等于系统日报默认收件人。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q219 Graph客户端标识

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：先确认目标是题目所指项目的Graph Token JSON。

2. 读取客户端标识字段，保持完整字符串。

3. 与项目认证配置核对同一应用，避免取成tenant或用户标识。

验证依据或核验要求：目标文件和字段尚待原始检材复核。

易错点：客户端ID、租户ID、授权令牌是不同内容。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q220 token_type与tenant

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在同一Graph Token记录中分别定位token_type和tenant相关字段。

2. 确认字段名、数据类型和原始值，不从其他文件拼接。

3. 与该项目认证上下文核对并按题意组织答案。

验证依据或核验要求：类型与租户字段需来自同一目标记录；尚未完成。

易错点：token_type不是访问范围scope，tenant也不是登录邮箱域名的直接推断。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q221 Token有效秒数

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：读取题目指定Token记录中的有效期字段。

2. 确认原值是持续时间还是到期时间点，以及其单位。

3. 必要时根据同记录的起止时间计算秒数，并保留计算依据。

验证依据或核验要求：需字段语义与秒数对应；当前未完成。

易错点：不能把Unix时间戳直接当有效秒数，也不能混用刷新令牌有效期。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q222 日报与银行邮件路由

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：读取邮件服务的实际环境变量及邮件发送分支。

2. 逐项映射日报、银行和其他类别分别使用的收件配置。

3. 保留每个类别对应的地址及来源行，检查运行覆盖关系。

验证依据或核验要求：需要路由分支与生效变量相互支持；当前未完成。

易错点：不要按邮箱名称猜角色，也不能把测试配置当部署配置。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q223 OTC邮件地址

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在同一邮件环境配置中定位OTC收件变量。

2. 检查OTC发送分支引用该变量的关系。

3. 按原值保留邮箱字符与大小写，本地作答并公开脱敏。

验证依据或核验要求：配置与OTC分支尚未闭环，参考值不作确定答案。

易错点：普通日报地址或银行地址不能代替OTC收件地址。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q224 OpenClaw工作目录与Provider

状态：正式复核。公开结论：C（WSL用户工作目录、Provider vllm）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；agents.defaults.workspace; agents.defaults.model.primary

方法依据：既有记录复述。

1. 只读进入WSL文件系统并打开.openclaw/openclaw.json。

2. 读取agents.defaults.workspace，记录工作目录。

3. 读取agents.defaults.model.primary，从默认模型标识的Provider前缀确认vllm。

验证依据或核验要求：工作目录与默认模型同源，结果对应选项C。

易错点：Provider ID不是api字段的协议名称。

#### Q225 数据库MCP命令

状态：正式复核。公开结论：/home/[用户]/.openclaw/bin/postgres-isolated-mcp。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；mcp.servers.postgres-isolated.command

方法依据：既有记录复述。

1. 在主配置openclaw.json定位mcp.servers。

2. 找到postgres-isolated服务，读取command完整绝对路径。

3. 保留路径中的用户目录和文件名于本地，公开稿仅匿名化用户部分。

验证依据或核验要求：字段mcp.servers.postgres-isolated.command直接支持命令路径。

易错点：配置声明调用该命令，不等于证明其已启动或连接成功。

#### Q226 DeepSeek Provider ID

状态：正式复核。公开结论：vllm_gpu1。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm_gpu1

方法依据：既有记录复述。

1. 在openclaw.json的models.providers中遍历模型条目。

2. 找到DeepSeek模型所在的对象。

3. 读取包住该模型的Provider键名vllm_gpu1。

验证依据或核验要求：模型ID与所属Provider层级共同支持vllm_gpu1。

易错点：显示名称、模型ID和Provider ID不能混为一谈。

#### Q227 Qwen参数规模

状态：正式复核。公开结论：D（32B）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.models[0].id

方法依据：既有记录复述。

1. 定位models.providers.vllm.models中的Qwen条目。

2. 完整读取模型ID，确认其32B规模标识。

3. 与默认模型引用对应并选择32B。

验证依据或核验要求：主配置模型ID支持参数规模32B。

易错点：AWQ等量化标记不是参数数量，contextWindow也不是参数规模。

#### Q228 DeepSeek参数规模

状态：正式复核。公开结论：C（14B）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm_gpu1.models[0].id

方法依据：既有记录复述。

1. 定位models.providers.vllm_gpu1.models中的DeepSeek条目。

2. 完整读取该模型ID中的14B规模。

3. 核对该条目确属DeepSeek而非旁边Qwen模型。

验证依据或核验要求：模型条目支持14B，选项C。

易错点：不能套用通用DeepSeek旗舰模型规模，题目问的是此处配置模型。

#### Q229 17时结算任务名

状态：正式复核。公开结论：tronic-settlement-monitor-1700-close。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].name

方法依据：既有记录复述。

1. 打开cron/jobs.json，先按schedule及payload找17:00收市结算任务。

2. 核对它与日报任务、营业时段监控任务的区别。

3. 读取同一任务对象的name，保留tronic-settlement-monitor-1700-close。

验证依据或核验要求：任务用途、时刻与名称在同一对象中对应。

易错点：仅按名称含settlement搜索可能命中多个不同周期任务。

#### Q230 17时任务ID与cron

状态：正式复核。公开结论：A（目标任务ID、0 17 * * *；ID不公开）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].id/schedule

方法依据：既有记录复述。

1. 复用Q229确定的17:00收市任务对象。

2. 同时读取id与schedule的cron表达式。

3. 核对时区，解释0 17 * * *是该配置时区每日17:00。

验证依据或核验要求：ID、cron及时区来自同一任务；原ID仅本地保留。

易错点：不能把相邻任务ID与这个cron组合；cron本身不包含所有时区信息。

#### Q231 营业时间监控频率

状态：正式复核。公开结论：E（30分钟）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].schedule.expr

方法依据：既有记录复述。

1. 从jobs.json定位营业时间结算监控任务。

2. 读取schedule.expr的分钟列及生效时间范围。

3. 解析为每30分钟，另将每1分钟审批任务列出以排除混淆。

验证依据或核验要求：配置表达式支持营业监控30分钟频率。

易错点：1分钟审批与30分钟监控是不同任务，不能按最短间隔回答。

#### Q232 可检索记忆chunks数量

状态：正式复核。公开结论：C（0条）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/memory/main.sqlite；chunks

方法依据：既有记录复述。

1. 只读打开.openclaw/memory/main.sqlite并检查存在chunks表。

2. 执行PRAGMA quick_check，记录结构检查结果。

3. 执行SELECT COUNT(*) FROM chunks，结果0。

验证依据或核验要求：结构检查通过且该表计数为0，支持选项C。

易错点：0条chunks只描述该表当前状态，不证明整个设备从未产生记忆。

#### Q233 Gateway监听端口

状态：正式复核。公开结论：18789。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；gateway.port

方法依据：既有记录复述。

1. 打开WSL中的OpenClaw主配置。

2. 定位gateway对象，读取port字段18789。

3. 与模型Provider的8000/8001端口区分。

验证依据或核验要求：gateway.port直接支持18789。

易错点：配置端口不自动证明运行时对外可达。

#### Q234 Qwen服务地址

状态：正式复核。公开结论：http://127.0.0.1:8000/v1。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.baseUrl

方法依据：既有记录复述。

1. 在models.providers定位Qwen所属vllm对象。

2. 读取baseUrl完整值http://127.0.0.1:8000/v1。

3. 保留协议、地址、端口和路径，不省略/v1。

验证依据或核验要求：Qwen模型与同一Provider的baseUrl对应。

易错点：不要取DeepSeek的端口或OpenClaw Gateway端口。

#### Q235 定时任务错误原因

状态：正式复核。公开结论：C（timeout）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs-state.json；jobs.*.state.lastErrorReason

方法依据：既有记录复述。

1. 打开cron/jobs-state.json而非只读jobs.json。

2. 定位对应任务的state及lastErrorReason。

3. 读取timeout，并保留任务标识与状态关联。

验证依据或核验要求：执行状态字段直接记录timeout。

易错点：错误原因反映该状态记录，不能据此推断所有历史执行都超时。

#### Q236 WSL发行版版本与UID

状态：正式复核。公开结论：C（Ubuntu、WSL2、UID 1000）。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/host/partition-3/Users/[用户]/NTUSER.DAT；Software/Microsoft/Windows/CurrentVersion/Lxss/{[UUID]}

方法依据：既有记录复述。

1. 在宿主用户NTUSER.DAT读取Software/Microsoft/Windows/CurrentVersion/Lxss。

2. 逐个发行版子键核对DistributionName、Version和DefaultUid。

3. 将同一发行版的Ubuntu、2、1000组成答案。

验证依据或核验要求：注册表同一子键支持发行版、WSL版本和UID。

易错点：Version=2指WSL代际，不是Ubuntu发行版号；UID也不是Windows SID。

#### Q237 Gateway绑定位置

状态：正式复核。公开结论：loopback。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；gateway.bind

方法依据：既有记录复述。

1. 在openclaw.json定位gateway。

2. 读取bind字符串原值loopback。

3. 结合port字段说明这是网关绑定配置，不改写成推测的公网IP。

验证依据或核验要求：gateway.bind支持loopback。

易错点：不能因宿主存在端口转发就把此字段改答为0.0.0.0。

#### Q238 Qwen上下文容量

状态：正式复核。公开结论：8192。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.models[0].contextWindow

方法依据：既有记录复述。

1. 定位Qwen对应模型条目，确认不是DeepSeek条目。

2. 读取contextWindow=8192。

3. 与maxTokens及模型参数规模分别记录。

验证依据或核验要求：Qwen模型对象的contextWindow直接支持8192。

易错点：最大输出token、上下文窗口和模型参数量不同。

#### Q239 自动结算美元阈值

状态：正式复核。公开结论：50000。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/cron/jobs.json；jobs[id=[UUID]].payload.message

方法依据：既有记录复述。

1. 在jobs.json找到日常交易监控及自动结算任务。

2. 阅读payload.message及描述中的触发条件。

3. 确认金额为累计美元阈值50000，再按题目格式只填数字。

验证依据或核验要求：任务payload及描述支持同一美元累计阈值。

易错点：单笔门槛、累计阈值与余额要求不能混用，币种也必须核对。

#### Q240 Qwen授权密钥

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/openclaw.json；models.providers.vllm.apiKey

方法依据：既有记录复述。

1. 在openclaw.json定位models.providers.vllm。

2. 确认该Provider承载Qwen模型后读取apiKey完整值。

3. 本地保留原值并记录字段路径，公开稿省略秘密值。

验证依据或核验要求：主配置Qwen条目与授权字段同源。

易错点：不应取agents/main/agent/models.json中的同名配置替代。

#### Q241 DeepSeek Provider文件密钥

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：local-artifact/gpt/P01_COM02_WSL/exports/wsl/home/[用户]/.openclaw/agents/main/agent/models.json；providers.vllm_gpu1.apiKey

方法依据：既有记录复述。

1. 按题目Provider文件口径打开agents/main/agent/models.json。

2. 定位providers.vllm_gpu1，并核对其模型为DeepSeek。

3. 读取该对象的apiKey，保留字面值；再对照主配置，记录两处值不相同。

验证依据或核验要求：本地保留截图可核对Provider文件；公开稿省略原值。

易错点：主配置中DeepSeek的apiKey不是本题所指定Provider文件的值。

结论边界：此题以Provider文件models.json为准；其值与主配置同名字段不同。公开稿两处原值均省略。

#### Q242 移动项目owner

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在目标移动项目中定位定义owner属性的配置文件。

2. 核对文件属于目标项目及对应版本。

3. 读取owner原值并保留大小写、数字及连字符。

验证依据或核验要求：尚需项目文件与属性的原始证据；目前未完成。

易错点：仓库组织名、应用显示名称和项目owner不一定相同。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q243 HTTPS端口

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：找到Tronic网站配置中负责HTTPS的server部分。

2. 读取对应listen配置并确认该块的TLS用途。

3. 按题意记录端口，与HTTP端口和后端代理端口分开。

验证依据或核验要求：目标HTTPS配置原值尚未复核。

易错点：不能凭HTTPS惯例直接填443，也不能把模板存在说成已生效。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q244 TLS协议版本

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在同一HTTPS配置块定位ssl_protocols。

2. 读取全部协议标识及版本，不只取第一个。

3. 核对配置包含关系及目标文件版本，再与选项比较。

验证依据或核验要求：需目标配置中实际列出的两种协议；当前未完成。

易错点：浏览器支持的协议或Nginx默认能力不能代替配置原值。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q245 密码套件顺序参数

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在题目所指HTTPS配置中查ssl_prefer_server_ciphers。

2. 读取参数值，并解释其是否要求服务器套件顺序优先。

3. 核对没有被其他同层或生效配置覆盖。

验证依据或核验要求：参数及其值须来自目标配置；当前未完成。

易错点：ssl_ciphers列表与ssl_prefer_server_ciphers的控制含义不同。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q246 证书SAN中的IP

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位该站点实际证书及其生成脚本或配置。

2. 解析Subject Alternative Name中的IP Address类型项。

3. 只汇总IP SAN，与脚本预期及题目两个地址核对。

验证依据或核验要求：证书扩展与生成配置应相互对应；当前未完成。

易错点：不要从证书CN、服务器绑定地址或DNS解析结果推断IP SAN。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q247 证书SAN中的DNS

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：复用同一证书或对应生成配置。

2. 在SAN扩展中筛选DNS类型条目。

3. 按完整DNS名称与题目选项核对，另列CN以免混淆。

验证依据或核验要求：需SAN实际条目支持，当前未完成。

易错点：证书Subject的CN不等于全部DNS SAN授权范围。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q248 根证书到期时间

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：先确认目标文件是根证书而非服务器叶证书。

2. 解析其NotAfter原值及时间表示。

3. 按题目格式和时区转换后记录完整到期时间。

验证依据或核验要求：需要根证书身份、NotAfter及转换过程共同支持；尚未复验。

易错点：脚本中的有效天数或文件修改时间都不能替代证书实际到期时间。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q249 安装WSL及默认WSL2命令

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位相关用户的ConsoleHost_history.txt。

2. 查安装WSL以及设置默认WSL2的实际输入行。

3. 保留命令参数与顺序，区分历史事实和建议安装命令。

验证依据或核验要求：历史记录才支持本题实际命令；当前未完成。

易错点：常见教程命令不能证明该设备上输入过相同命令。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q250 Windows日报任务完整名称

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定位Windows计划任务定义，确认对应日报业务。

2. 读取任务URI或完整注册路径，而非只取显示短名。

3. 结合触发器和动作确认目标任务，与WSL cron日报分开。

验证依据或核验要求：任务定义中的URI及动作需对应；当前未完成。

易错点：Windows任务计划与Linux cron同名任务不能互换。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q251 PowerShell端口转发目标

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：在PowerShell历史中筛选portproxy相关命令。

2. 完整解析目标命令的监听参数与connect目标参数。

3. 按题目实际输入历史取目标，另将当前注册表或动态脚本值作为不同时间状态。

验证依据或核验要求：原历史命令尚需复验。

易错点：不能用当前WSL动态地址改写过去命令中的目标地址。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q252 WSL虚拟磁盘总容量

状态：成员复现待主复核。公开结论：256（GiB口径）。

证据定位：local-artifact/gpt/P01_COM02_WSL/tool-logs/wsl-discovery.json；VHDX metadata VIRTUAL_DISK_SIZE_GUID

方法依据：复现说明（成员复现待主复核）。

1. 从WSL VHDX元数据读取VIRTUAL_DISK_SIZE_GUID对应虚拟容量。

2. 保留原字节数274877906944，与宿主文件长度187435057152分别标记。

3. 按1024³换算为256GiB，按题目格式回答。

验证依据或核验要求：成员读取虚拟容量元数据支持256GiB；仍待主复核。

易错点：虚拟容量、文件长度和文件系统已用/可用空间不是同一指标。

#### Q253 VIP状态修改时间

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：按目标设备和管理员VIP修改端点筛选请求。

2. 核对被修改用户、修改操作和成功响应属于同一事件。

3. 读取并转换该事件时间，排除仅查询VIP状态的请求。

验证依据或核验要求：尚缺完整请求与成功状态闭环。

易错点：请求发出不等于状态修改成功，目标用户也不能从相邻记录借用。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q254 设备成功管理员登录次数

状态：待复核或未解。公开结论：未定。

证据定位：未完成原始检材复验，参考答案仅作线索。

方法依据：未解后续步骤。

1. 建议后续核验：定义成功管理员登录的端点、设备匹配规则和成功状态条件。

2. 枚举题目时间范围内全部匹配记录。

3. 排除登录失败、刷新令牌及普通认证请求后计数，保留逐条清单。

验证依据或核验要求：需可复算的匹配记录集合；当前未完成。

易错点：访问管理员页面次数不是成功登录次数，重试也需按事件语义处理。

结论边界：已有他人参考答案，但未完成本方原始证据闭环；赛后停止新增解题，不将参考值填作结论。

#### Q255 VIP订单商品及数量

状态：成员复现待主复核。公开结论：A（Oil 20、Ice 5）。

证据定位：/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/32873；/var/lib/postgresql/18/main/base/16389/90873

方法依据：复现说明（成员复现待主复核）。

1. 从成员恢复的PG关系中选取当前可见orders，限定目标客户及题目订单范围。

2. 通过商品关联键连接products，核对数量和商品名称。

3. 成员结果为Oil20、Ice5，保留订单与商品对应明细。

验证依据或核验要求：有效订单、商品及客户关系共同支持选项A；待主复核。

易错点：不要把旧tuple、已删除订单或商品库存数量混入购买数量。

#### Q256 订单发起设备

状态：成员复现待主复核。公开结论：B（Redmi 23124RA7EO）。

证据定位：/var/lib/postgresql/18/main/base/16389/90873

方法依据：复现说明（成员复现待主复核）。

1. 固定Q255两笔目标订单及其客户/actor。

2. 在活动记录中按同一订单或actor关联设备元数据。

3. 读取品牌及型号，成员结果Redmi 23124RA7EO。

验证依据或核验要求：对应活动记录支持成员选项B，待主复核。

易错点：不能从某次无关登录或设备清单中选同品牌型号。

#### Q257 订单交易总额

状态：成员复现待主复核。公开结论：85000。

证据定位：/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/90873

方法依据：复现说明（成员复现待主复核）。

1. 固定Q255同两笔当前可见订单。

2. 读取各自有效金额70000、15000，并确认数据库币种口径。

3. 用十进制相加得到85000，再与活动记录核对。

验证依据或核验要求：金额来自同一订单集合，成员结果待主复核。

易错点：客户端照片中的换汇显示金额不应替代数据库本币金额。

#### Q258 当前订单状态

状态：成员复现待主复核。公开结论：D（pending）。

证据定位：/var/lib/postgresql/18/main/base/16389/32894；/var/lib/postgresql/18/main/base/16389/90873

方法依据：复现说明（成员复现待主复核）。

1. 使用事务可见性筛选后的两笔目标订单。

2. 读取各自status原值，而非历史状态或活动说明。

3. 核对两笔均为pending，按选项D作成员结论。

验证依据或核验要求：当前有效记录支持pending，待主复核。

易错点：有订单记录或有金额不代表已支付、已完成。

#### Q259 PostgreSQL完整版本

状态：成员复现待主复核。公开结论：D（18.4）。

证据定位：/var/log/postgresql/postgresql-18-main.log.1；/var/lib/dpkg/status

方法依据：复现说明（成员复现待主复核）。

1. 读取/var/log/postgresql/postgresql-18-main.log.1中的启动版本信息。

2. 对照/var/lib/dpkg/status中同一PostgreSQL包版本。

3. 保留完整小版本18.4并匹配选项D。

验证依据或核验要求：启动日志与包记录共同支持成员结果，待主复核。

易错点：目录名18或PG_VERSION只能支持主版本，不足以确定18.4。

### COM-03 NAS与阵列

#### Q260 md0阵列UUID

状态：正式复核。公开结论：C。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/mdadm/mdadm.conf

方法依据：既有记录复述。

1. 读取NAS系统盘/etc/mdadm/mdadm.conf的md0定义。

2. 记录阵列UUID并对应到两块成员的superblock身份。

3. 确认目标为md0且属于同一阵列后与选项核对。

验证依据或核验要求：配置和成员元数据支持同一阵列身份。

易错点：MD阵列UUID、EXT4文件系统UUID和磁盘分区UUID并非同一个值。

#### Q261 Debian与OMV版本及升级前版本

状态：正式复核。公开结论：B。

证据定位：COM03_NAS_DISK0.E01/分区2/usr/lib/os-release；COM03_NAS_DISK0.E01/分区2/var/log/apt/history.log；COM03_NAS_DISK0.E01/分区2/var/lib/dpkg/status

方法依据：既有记录复述。

1. 从/usr/lib/os-release读取当前Debian发行信息。

2. 在/var/lib/dpkg/status定位OpenMediaVault当前安装版本。

3. 再读/var/log/apt/history.log中的升级前后记录，将旧版本与当前版本分别记录。

验证依据或核验要求：系统信息、包状态和升级历史相互对应，支持选项B。

易错点：不要将安装包缓存名或旧日志版本作为当前运行版本。

#### Q262 NAS网络配置

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/netplan/20-openmediavault-enp0s3.yaml；COM03_NAS_DISK0.E01/分区2/etc/openmediavault/config.xml

方法依据：既有记录复述。

1. 读取/etc/netplan/20-openmediavault-enp0s3.yaml中的目标接口配置。

2. 对照/etc/openmediavault/config.xml中的同一接口项目。

3. 分别整理地址、前缀、网关等题目要求项，并核对接口身份。

验证依据或核验要求：两个配置文件中目标接口的网络参数形成交叉核对。

易错点：配置记录不直接证明某时刻网络连通；不能取其他接口或回环地址。

#### Q263 双配置中的挂载UUID

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/fstab；COM03_NAS_DISK0.E01/分区2/etc/openmediavault/config.xml

方法依据：既有记录复述。

1. 在/etc/fstab定位目标数据文件系统的挂载条目。

2. 从源字段读取文件系统UUID，再与OpenMediaVault存储配置对应。

3. 确认两者指向同一存储对象后按题目格式作答。

验证依据或核验要求：fstab与config.xml双来源支持目标UUID。

易错点：不要把mdadm的阵列UUID误当文件系统挂载UUID。

#### Q264 指定日期Web错误日志数

状态：正式复核。公开结论：B。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/nginx/openmediavault-webgui_error.log.1

方法依据：既有记录复述。

1. 读取openmediavault-webgui_error.log.1，确认覆盖题目指定日期。

2. 按日志记录时间及ERROR等级筛选。

3. 对匹配事件计数，并排除其他日期与warning记录。

验证依据或核验要求：保留筛选范围和匹配明细以复算，对应选项B。

易错点：行数不必等于事件数；错误堆栈续行不能重复计为多个事件。

#### Q265 TCoin宣传图片数量

状态：正式复核。公开结论：9。

证据定位：由两块有效成员重建 md0 派生镜像；EXT4文件枚举、原图目视及OCR交叉复核。

方法依据：既有记录复述。

1. 核对两块MD成员同阵列、role0和role2及一致events；记录layout2、chunk512KiB、data offset18432扇区。

2. 按left-symmetric RAID5条带与校验位置异或恢复缺失role1，写新派生镜像。

3. 验证11处EXT4超级块CRC32C并用独立文件系统导出检查，已记录92文件、61目录。

4. 枚举图片，结合缩略图、OCR和逐图目视筛出TCoin宣传图，最终9张。

验证依据或核验要求：阵列身份、文件系统校验及内容筛选共同支持9张。

易错点：图片文件总数不等于宣传图数量，OCR命中也不能自动替代目视确认。

#### Q266 USERS组人数

状态：正式复核。公开结论：C。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/group

方法依据：既有记录复述。

1. 打开/etc/group并定位题目指定的USERS组条目。

2. 按组成员字段拆分显式用户名并去除空项。

3. 依题目该字段口径计数，与选项C核对。

验证依据或核验要求：保留原组行与拆分列表，计数可回查。

易错点：不要把系统全部用户数当该组显式成员数；主组归属属于另一统计口径。

#### Q267 SMB白名单未包含账号

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/samba/smb.conf

方法依据：既有记录复述。

1. 读取/etc/samba/smb.conf中目标共享的允许用户配置。

2. 确定题目给定用户集合及白名单中的实际用户名/组表达式。

3. 比较集合，找不在该允许范围中的账号。

验证依据或核验要求：应能列出候选与允许列表逐项比较依据。

易错点：账号存在于系统或普通组不自动表示被该Samba共享允许。

#### Q268 SSH与普通组交集人数

状态：正式复核。公开结论：5。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/group

方法依据：既有记录复述。

1. 在/etc/group分别定位SSH组与题目普通组。

2. 把两组显式成员拆成去重集合。

3. 求集合交集并计数，得到5。

验证依据或核验要求：原始组行、两个集合及交集清单支持5。

易错点：求交集不是求并集，也不能把SSH配置允许项误当/etc/group组成员。

#### Q269 Admin组成员

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/group

方法依据：既有记录复述。

1. 在/etc/group定位题目管理员组。

2. 读取冒号分隔记录中的成员列表。

3. 按原始账号保留成员并检查是否有多个，公开稿省略账号值。

验证依据或核验要求：管理员组成员字段直接提供结论。

易错点：管理员组成员、拥有sudo权限的全部主体、当前登录管理员不是同一集合。

#### Q270 SSH白名单配置

状态：正式复核。公开结论：A。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/ssh/sshd_config

方法依据：既有记录复述。

1. 读取/etc/ssh/sshd_config并定位AllowUsers、AllowGroups等访问限制。

2. 检查是否位于全局段或Match条件内，保留相关上下文。

3. 按实际配置解释用户名白名单或组白名单，并与选项A比较。

验证依据或核验要求：配置项与作用范围共同支持结论。

易错点：AllowGroups的组名不能直接解释为单个用户名。

#### Q271 成功SSH认证次数

状态：待复核或未解。公开结论：未定。

证据定位：NAS / var/log/journal；接受认证事件与后续会话链。

方法依据：未解后续步骤。

1. 建议后续核验：以完整journal范围筛选成功Accepted认证事件，保留时间、进程/会话上下文。

2. 关联session opened、断开及关闭，检查额外事件是否真实独立。

3. 独立扫描journal条目与entry数组交叉计数，均为26。

4. 记录选项不含26的冲突，不能自行缩窄为某一天取25。

验证依据或核验要求：额外一次具有会话链；本题保持未定而非强选。

易错点：认证次数、日志行数、会话数是不同指标。

结论边界：全范围得到26次成功认证，选项不含26；只取其中一天得到25但题面未限定，故不强选。

#### Q272 可识别SSH会话数

状态：正式复核。公开结论：D。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/wtmp.db；COM03_NAS_DISK0.E01/分区2/var/log/wtmp

方法依据：既有记录复述。

1. 读取wtmp.db及wtmp中的SSH登录/会话记录。

2. 结合Accepted、session opened、断开和关闭信息建立会话对应关系。

3. 按题意计可识别会话，而非把每个日志事件计一次。

验证依据或核验要求：会话级关联支持选项D。

易错点：缺少Logout不自动等于失败认证，也不能将认证条数直接代替会话数。

#### Q273 成功SSH会话源IP

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/wtmp.db；COM03_NAS_DISK0.E01/分区2/var/log/wtmp

方法依据：既有记录复述。

1. 复用已确认的成功SSH会话集合。

2. 从wtmp.db/wtmp对应记录读取RemoteHost或来源字段。

3. 对来源按题意去重或列举，保留每个来源对应的成功会话。

验证依据或核验要求：来源必须能回到成功会话，不能混入失败尝试。

易错点：sshd配置允许地址或端口转发地址不等于实际会话来源。

#### Q274 失败登录日志大小

状态：正式复核。公开结论：A。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/btmp

方法依据：既有记录复述。

1. 定位NAS系统盘/var/log/btmp原文件。

2. 读取其逻辑字节长度，并核对题目单位。

3. 保持该日志身份与题目失败登录日志一致后匹配选项A。

验证依据或核验要求：原文件长度支持选项，不能由解析输出大小推算。

易错点：导出的文本大小、压缩包大小和磁盘分配大小均不是本题文件长度。

#### Q275 同一启动组raid disk 0设备名

状态：待复核或未解。公开结论：未定。

证据定位：NAS / var/log/journal；按 boot_id 分组的 md/EXT4启动记录。

方法依据：未解后续步骤。

1. 建议后续核验：按journal的boot_id将启动事件分组。

2. 在每一组关联md阵列、raid disk0角色与设备名。

3. 比较12组结果：前11组为sdb，末组为sdd，记录题目未唯一限定组别。

验证依据或核验要求：跨启动差异已明确，本题仍无法唯一确定。

易错点：sdb/sdd不是跨启动恒定身份；相同容量或UUID不能替代启动范围。

结论边界：12个启动组中前11个raid disk 0为sdb，最后一个为sdd；题面未明确组别，无法唯一确定。

#### Q276 md0容量变化字节数

状态：正式复核。公开结论：21455962112。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/journal/[长标识]/system.journal

方法依据：既有记录复述。

1. 在目标启动日志定位md0容量变化事件。

2. 读取变化前后扇区数及日志表示单位。

3. 按标准512字节扇区换算变化量，结果21455962112字节。

验证依据或核验要求：原扇区计数及512字节换算支持精确字节值。

易错点：不要用厂商GB标称值、文件长度或1024字节扇区替代。

#### Q277 EXT4数据与配额模式

状态：正式复核。公开结论：A。

证据定位：COM03_NAS_DISK0.E01/分区2/var/log/journal/[长标识]/system.journal

方法依据：既有记录复述。

1. 在journal中定位与目标md0/EXT4对应的挂载事件。

2. 读取日志中数据模式与配额模式相关描述。

3. 保留同次挂载上下文，与选项A逐项对应。

验证依据或核验要求：具体挂载日志支持实际记录的模式。

易错点：fstab期望参数和日志中的实际挂载状态应区分，不能取其他卷的记录。

#### Q278 最低SMB协议版本

状态：正式复核。公开结论：A。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/samba/smb.conf

方法依据：既有记录复述。

1. 读取/etc/samba/smb.conf的全局协议配置。

2. 定位最低SMB协议限制并保留原值。

3. 检查是否存在题目所指作用域或覆盖项，再对照选项A。

验证依据或核验要求：最低协议配置项提供结论。

易错点：最低版本不是最高允许版本，也不能由Samba软件版本直接推出。

#### Q279 文件系统挂载点

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：COM03_NAS_DISK0.E01/分区2/etc/fstab

方法依据：既有记录复述。

1. 在/etc/fstab用目标文件系统UUID定位挂载条目。

2. 读取同一行的挂载目录。

3. 结合OpenMediaVault存储配置核对目标与目录的对应，保留完整路径于本地。

验证依据或核验要求：来源UUID和挂载点属于同一条目。

易错点：目录名称相似或目录已存在，不自动证明它对应目标文件系统。

### DOC-01 资金流水

#### Q280 邮件委托资金总额

状态：正式复核。公开结论：23010346.36。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 读取DOC-01邮件委托指示及PyCHK_to_police.xlsx，确认资金范围。

2. 依据交易行From/To校正两处工作表标签错误，避免错归钱包或重复纳入。

3. 按Reference Data_Rate统一USD，采用Decimal汇总。

4. 核对0.0004 USD的原始口径差异，保留两位小数结果23010346.36。

验证依据或核验要求：邮件范围、汇率、校正和合计可对应；微小差异不改变两位小数。

易错点：不能把全部交易流量重复相加当最初委托金额。

结论边界：存在两处工作表标签错误与0.0004 USD的原始口径差异；已显式对齐，不改变两位小数结果。

#### Q281 最终资金留存地址数

状态：正式复核。公开结论：B。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 先按交易标识去重并保留成功交易。

2. 逐地址计算成功转入、转出及题目范围内的净留存。

3. 结合资金路径识别仍有余额的终点，统计其地址数并对应选项B。

验证依据或核验要求：终点列表及各自留存金额应可回查。

易错点：转入过资金的地址不一定是最终留存地址；失败交易不能记已到账。

#### Q282 最终停留资金最多的钱包

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 复用Q281确认的最终留存终点集合。

2. 把各终点净留存统一为USD。

3. 比较留存金额，回查最大项的实际地址及相关交易。

验证依据或核验要求：排名依据是净留存，不是累计流量；原地址仅本地保留。

易错点：高频中转钱包可能交易额最大但最终余额很低。

#### Q283 黑洞地址用途

状态：正式复核。公开结论：B（销毁/黑洞地址的常见用途）。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 定位题目提及的Burn/Sink或黑洞地址语境。

2. 解释此类地址常用于让资产退出可正常支配流通的销毁场景。

3. 将一般用途与选项B对应，同时区分本案是否有具体销毁交易证据。

验证依据或核验要求：本题支持的是地址类别常见用途。

易错点：仅见到地址标签或地址存在，不能证明某笔资金已经销毁。

#### Q284 全链路钱包数量

状态：正式复核。公开结论：26。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 读取完整链路全部交易行的From和To。

2. 按对应地址规则规范化比较，并保留原展示字符串。

3. 取发送方与接收方去重并集，得到26个钱包。

验证依据或核验要求：完整地址集合计数支持26。

易错点：只数工作表或只数发送方会漏掉没有独立表的地址。

#### Q285 缺少独立工作表的钱包

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 从完整交易链得到去重地址集合。

2. 核对每张独立工作表实际对应的钱包，先修正错误标签。

3. 计算链路地址集合减工作表地址集合，得到缺表钱包。

验证依据或核验要求：差集项仍可在交易对手字段回查。

易错点：不能用未校正的表标题直接做集合差，否则会制造假缺失。

#### Q286 该钱包币种

状态：正式复核。公开结论：A（Bitcoin）。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 固定Q285识别出的缺表地址。

2. 回查出现该地址的交易网络、币种及关联记录。

3. 确认其属于Bitcoin并匹配选项A。

验证依据或核验要求：网络/币种记录与同一地址对应。

易错点：地址外观只能辅助筛查，不能替代交易记录中的网络证据。

#### Q287 除Q Coin以外币种数

状态：正式复核。公开结论：3。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 读取链路记录中实际出现的币种字段。

2. 统一同币种的书写变体，按定义去重。

3. 剔除Q Coin后计数，结果3。

验证依据或核验要求：币种集合和排除项可列出复算。

易错点：交易表数、钱包数与币种数没有一一对应关系。

#### Q288 首次跨链资金最多币种

状态：正式复核。公开结论：C。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 按时间整理跨链/兑换路径，并识别各币种第一次进入事件。

2. 将首次转换金额用题给汇率统一USD。

3. 只比较各币种首次进入金额，排除之后回流或再次转换，按最大项匹配选项C。

验证依据或核验要求：首次事件与换算金额需能对应到交易行。

易错点：把某币种全部历史流入合计会改变题目“首次跨链”口径。

#### Q289 成功交易手续费USD

状态：正式复核。公开结论：24.84。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 按交易标识去重，筛出405条成功交易，排除1条失败交易。

2. 检查Gas Fee字段单位，并按Reference Data_Rate换成USD。

3. 每笔费用只计一次，以Decimal求和得到24.84 USD。

验证依据或核验要求：去重键、状态筛选和费用换算明细支撑合计。

易错点：发送与接收表重复记录会把费用算两遍；原已为USD的列不能再次换汇。

#### Q290 转入转出总额最大钱包

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 复用去重后的成功交易集。

2. 按地址分别汇总转入与转出本金USD，费用单独保留。

3. 按题意将两类本金流量合计并排名，回查最大项的地址。

验证依据或核验要求：最大累计流量地址由分项明细支持。

易错点：累计转入加转出不是净留存，也不应额外把手续费计作本金。

#### Q291 累计中转停留最长钱包

状态：正式复核。公开结论：[敏感值不公开]。

证据定位：DOC-01/PyCHK_to_police.xlsx

方法依据：既有记录复述。

1. 按题目资金路径整理每个钱包可匹配的入出区间。

2. 对每一有效区间计算停留秒数，再按地址累计。

3. 比较累计值，已归档最大6479秒、次大6456秒，回查对应钱包。

4. 保留原匹配口径；当前原脚本已清理，不补造多笔并行资金的具体分配算法。

验证依据或核验要求：现有记录支持累计结果及排名边界，但本次没有重跑匹配脚本。

易错点：一笔最长停留不等于累计最长；同时有多笔资金时不能随意最近邻配对。

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


## 2026-11-14 清理结果

WP上传并回读一致后，用户明确确认“删除本场资料，保留填写后的模板”。已删除并逐项验证本场三个工作/案件/解压目录，以及答案文件、题目文本和两份参考答案附件，共七个目标。工作目录内指向外部运行时的联接仅移除联接，外部工具仍存在；未删除skill、知识库及上午案件。

填写后的团体赛模板保留：回读仍为131张图片，文件31326338字节，ZIP完整性检查通过。原检材所在A盘未挂载，原件未删除；本次临时复盘目录的最后删除被自动审批以“blocked by policy”拒绝，该目录仍保留，未绕过拦截。因此不能表述为所有本地材料均已清空。公开知识库仅保留脱敏WP及方法，完整原始检材不在仓库中。


## 答辩知识点与步骤（赛后讲解）

团体赛答辩速记：知识点、步骤与证据

依据：本场已归档WP。以下是已完成过程的讲解，不代表现场重新操作。正式核验、成员复现和未解冲突仍分别保留；原工作检材已按用户要求清理，现场展示应使用保留的截图模板。



开场可以这样讲

“我们的分析按证据链展开：先确认检材和数据来源，再定位原始字段或代码，进行关联与计算，最后用独立记录或校验结果验证。对题目、参考答案和原始记录之间的冲突，我们保留差异，不为了匹配选项改动统计范围。”



一、Q106/Q108：为什么两个答案可以一样

知识点：手机号是联系方式；JID/LID是应用内部的账号或会话标识。显示名称、电话号码和会话标识不是同一字段。

步骤：

1. 从CL-02导出WhatsApp的ChatStorage.sqlite；存在同名WAL时一并保全，在副本上只读分析。

2. 查看ZWACHATSESSION，定位目标会话。

3. 对比ZCONTACTIDENTIFIER和ZCONTACTJID：本案前者记录电话JID，后者记录LID。

4. 关联同一会话的收发消息，检查发送方、接收方标识是否与该LID对应。本案有147条对方消息、23条本机消息用于关联。

5. 对照独立解析器的字段映射：iLEAPP的Chat ID使用ZCONTACTJID。

结论：本题两个问题按各自记录定位后可以指向相同LID。不是因为“两个名字相同”，也不是所有聊天软件的Chat ID都等于LID。

追问回答：“我们纠正过最初误取手机号映射字段的问题，最终依据原始会话字段和消息关联关系。”



二、Q150：零宽字符如何藏信息

知识点：文字肉眼看不见，不代表字符串里没有字符。8种符号可表示0到7，即每个符号承载3个二进制位。

步骤：

1. 定位可疑WhatsApp消息，导出原始Unicode文本，不能从截图重新手打。

2. 统计不可见字符的码点和顺序，识别8种编码符号。

3. 按本题确定的映射还原3bit序列，拼成178字节的帧。

4. 解析帧头中的magic、版本、nonce、长度和CRC32等字段。

5. 按题给xorshift32规则生成密钥流：左移13、右移17、左移5，并按32位无符号运算处理；初态及字节/位序沿用题给格式。

6. 本案关键是生成器32位输出按最低位先取，再按实际字节排列异或还原；得到167字节UTF-8有效载荷。

7. 计算还原载荷的CRC32，与帧头值比较，通过后再比对题目选项。

结论：Q150为C；没有访问还原出的下载地址。

追问回答：“能读出一段中文不够，我们还核对了长度和CRC。CRC支持本题还原结果的一致性，不是对来源真实性的密码学证明。”



三、Q157：为什么是ProductShop

知识点：React Native应用可能把业务JavaScript编译成Hermes字节码；界面文字、组件名和导航路由名需要区分。

步骤：

1. 打开同案聊天附件中的Tronic.apk，提取assets/index.android.bundle。

2. 根据文件头识别Hermes字节码版本96，使用对应格式解析字符串、函数和字面量。

3. 从AppNavigator定位Screen注册，找到ProductShop。

4. 回到UserDashboard，确认VIP标志控制购买入口。

5. 跟进该入口的onPress闭包，确认实际调用navigation.navigate，参数为ProductShop。

6. 检查目标页面确实包含商品、库存或价格相关内容，再与聊天中的VIP授权变化关联。

结论：ProductShop是导航路由；Product Shop、VIP Market、VIP Product Shop是不同显示文案。

追问回答：“关键证据是入口事件实际跳向该路由，不是只在字符串表里搜到了一个词。”

边界：当时尚未完成COM-02对应TSX源码的交叉复核，不要说所有源码版本都已验证。



四、Q265及NAS：少一块盘为什么还能恢复

知识点：三盘RAID5每个条带具有分布式奇偶校验；已知另外两块对应条带时，可通过异或恢复一块缺失成员。两块同时缺失通常超出这组RAID5的冗余能力。

步骤：

1. 读取MD RAID元数据，核对阵列身份、各盘role、events、布局、chunk和data offset。

2. 本案确认role0与role2存在，role1缺失；layout为left-symmetric，chunk为512KiB，data offset为18432扇区。

3. 按每个条带的轮转校验位置确定数据顺序，不能把两盘简单拼接。

4. 用异或恢复缺失条带，写入新的派生镜像，原成员保持只读。

5. 检查EXT4主/备超级块；本案11处CRC32C通过，并用独立文件系统工具验证目录可读。

6. 导出图像集合，先用缩略图/OCR辅助筛选，再逐图目视确认目标宣传图片，排除其他图片和重复范围。

结论：Q265为9张目标宣传图。

追问回答：“恢复成功不只看文件系统能打开，还核对阵列参数、多个超级块和实际导出文件。”



五、COM-02/WSL：配置文件各回答什么问题

知识点：E01是外层取证容器，里面可以是NTFS，再包含VHDX，里面才是WSL的EXT4。文件实际占用、虚拟磁盘容量、文件系统可用空间不同。

步骤：

1. 完整读取EWF，定位宿主NTFS第三分区。

2. 从用户注册表Lxss确认Ubuntu、WSL版本2及默认UID1000，并定位对应发行版目录。

3. 找到LocalState/ext4.vhdx，以只读方式解析内部EXT4。

4. 从/home/[用户]/.openclaw/openclaw.json读取默认模型、Provider ID、baseUrl、contextWindow及gateway。

5. 从cron/jobs.json读取任务名称、周期和时区；从jobs-state.json读取上次执行状态，不能把“配置了任务”说成“任务成功运行”。

6. 用只读SQLite检查memory/main.sqlite的chunks行数，并检查数据库结构完整性；本案为0。

7. 需要Provider授权字段时，区分主配置与agents/main/agent/models.json，按题指定的文件回答，密钥不在答辩材料中公开。

本案例子：Qwen为32B，DeepSeek为14B；网关端口18789、绑定loopback；营业时段监控每30分钟、收市任务17:00执行。1分钟自动审批是另一任务。

Q252：成员读取VHDX虚拟容量274877906944字节，除以1024的三次方为256GiB；不能用VHDX文件长度代替。

追问回答：“我们按照配置对象分别取字段，并用任务状态或数据库记录核对运行结果。”



六、DOC-01：资金流统计怎样避免重复

知识点：一个交易可能出现在发送方和接收方两张表中；表名、地址、交易标识、币种和金额单位必须一起核对。

步骤：

1. 读取原邮件及XLSX，整理交易标识、From、To、时间、状态、币种、金额和手续费。

2. 用相同交易标识去重，并用两侧明确的From/To核对归属；本案发现过工作表标签错置，不能只相信表名。

3. 统一地址比较规则：0x地址的大小写按相应标识规则处理，Base58地址保留大小写。

4. 区分成功与失败交易；成功资金流统计不把失败交易当作已发生转账。

5. 按参考汇率和各列单位转换金额，用Decimal或等价十进制计算避免浮点误差。

6. 同笔手续费只记一次；本金流向排名与手续费分开。

7. “首次跨链”只算首次进入该币种；“累计中转停留”累加相应入出区间，不能拿一笔最长停留替代。

结论示例：按交易标识去重后406笔，其中405成功、1失败；成功手续费合计24.84；累计停留最长6479秒，第二6456秒。

追问回答：“先确认统计对象和去重键，再计算总量；不会把跨工作表的重复记录当新增交易。”



七、COM-02 PostgreSQL：如果被问到数据库题

状态必须先说明：这些是成员离线复现结果，比赛冻结时没有进入主会话正式核验清单。

知识点：PostgreSQL一个表有多个历史tuple版本；OID与物理文件号未必一致；xmax非零不必然代表已删除。

步骤：

1. 从Tronic_s2虚拟磁盘定位EXT4及PostgreSQL数据目录，保持离线只读。

2. 由pg_database、pg_class、pg_attribute和pg_filenode.map确定业务库、物理关系文件和字段布局。

3. 按数据页、行指针、空值位图、对齐及varlena格式解析记录；numeric用十进制恢复。

4. 用pg_xact和tuple事务标志判断提交与可见版本；HEAP_XMAX_LOCK_ONLY不能按删除处理。

5. 根据应用写入时间的方式确定时区，筛选2026-08-04香港时间09:00至17:00且completed的结算记录。

6. 根据实际加密格式使用Fernet认证解密金额，以Decimal汇总；成员结果为4笔、14194443.00港元。

7. 对订单、商品和活动记录按关联键核对商品、数量、设备、金额与状态；不能把手机展示的换汇金额替代数据库本币金额。

8. 通过pg_control/映射CRC、116页页校验及checkpoint之后的有效WAL尾段核对一致性；不能只因文件可读就称数据库一致。

追问回答：“本次没有启动原数据库，也没有实际网络登录。口令题做的是候选SCRAM验证器离线比对，应准确说明验证方式。”



八、遇到证据与题目冲突怎么回答

Q147：同一Intent Filter允许多个候选域名，尚不能唯一选择。

Q193：目标MAC与实际记录不完全一致，近似命中不能当精确命中。

Q205：上午的异常关机启动与下午的正常启动不同；运行中的Setting FALSE不能解释成上次关机异常。

Q271：全范围成功认证26次而选项没有26，不删掉一条有效记录去凑25。

Q275：不同启动时磁盘名变化，sdb/sdd不是跨启动恒定身份，需要阵列元数据和启动范围。

统一答法：“目前证据支持这个观察，但题干限定与记录存在差异，所以我们保留冲突，没有将候选升级为确定结论。”



现场最值得记住的五句话

1. 工具显示是线索，原始字段和关联关系才是结论依据。

2. 配置存在、请求发出、执行成功，是三种不同事实。

3. 时间先确认字段语义与时区；计数先确认范围和去重键。

4. 恢复结果需要结构、校验和实际内容共同验证。

5. 没做过的复验和现场操作不补写；用已有截图展示真实完成的步骤。


## 答辩详细操作与追问（2026-11-14）

团体赛答辩详细步骤——知识点、证据路径、操作与追问
整理日期：2026-11-14
来源：本场冻结WP、当场分析记录及保留截图。原检材已清理；下面解释当时的分析过程，SQL和伪代码是帮助复现的示例，本次没有重新运行原检材。数据库专项仍是成员复现待主复核。原值只放本地版；本节仅归档方法及已公开的验证结果。

现场讲解统一顺序
先说“题目问什么”，再说“在哪份检材的哪个文件”，接着说“查哪个字段、怎么关联”，最后说“怎样验证、结论是什么”。不要只说“软件搜出来的”。
示范：“本题要确认的是应用内部会话ID。我在原始聊天数据库定位会话，读取会话标识，再用双方消息端点核对，因此能排除电话号码字段的混淆。”

一、Q106、Q108：WhatsApp内部会话ID
结论：两题指向同一个LID。具体标识仅保留于本地答辩稿。
1. 在CL-02定位 var/mobile/Applications/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite。导出数据库及匹配的WAL；分析副本，避免只导出主库漏掉尚未合并的数据。
2. 用数据库取证工具或SQLite只读查看器打开副本。先看表结构，确认ZWACHATSESSION、消息表及关联字段确实存在。不能将其他版本的表名直接套用。
3. 查询目标会话。下面是本案已知字段的示例SQL：
   SELECT Z_PK,ZPARTNERNAME,ZCONTACTJID,ZCONTACTIDENTIFIER
   FROM ZWACHATSESSION WHERE Z_PK=8;
4. 解释字段：Z_PK是本地会话主键；ZPARTNERNAME是名称；ZCONTACTIDENTIFIER在这条记录中是电话JID；ZCONTACTJID在这条记录中是LID。名称可变，不能单凭名称确定身份。
5. 在消息表按ZCHATSESSION=8筛选，查看ZISFROMME、ZFROMJID、ZTOJID、ZSTANZAID和消息类型。确认对方发来消息的端点及本机发送目标都能回到同一LID。本案关联依据包括147条对方消息、23条本机消息；统计时说明是否排除了系统事件，别混算所有类型。
6. 对照iLEAPP WhatsApp解析器，确认其Chat ID取自ZCONTACTJID。解析器字段映射是交叉核对，不替代原数据库。
7. Q106曾误取电话JID，后来按上述字段关系更正。Q108要求联系人LID，因此两题出现相同值是有证据的。
答辩可讲：“相同不是照抄；两道题分别定位后，都回到同一条会话的ZCONTACTJID。”
追问：为什么能认为网页版/桌面版？当时消息ID前缀模式提供了定位线索，但单个前缀不宜概括为所有版本的永久规则。本题最终ID依赖原字段关联。
展示：会话记录及消息端点查询截图。不能说火眼聊天表已经显示验证；当时该检材没有可用的火眼聊天分析表。

二、Q149、Q150：零宽字符隐写
结论：Q149=A；Q150=C。关键是位序与CRC闭环，不是肉眼猜明文。
1. 在WKH-01聊天数据定位可疑消息，直接导出原始Unicode字符串。截图、复制时自动清理字符的编辑器、手工重打都可能丢失隐写符号。
2. 枚举每个字符的Unicode码点与出现次数，将普通可见文字和不可见字符区分。可用“对每个字符输出位置、U+码点”的方式检查。
3. 找到8种编码符号，按照题给或已验证映射，将每种符号映射到0—7，再写成固定3bit。不能按出现频率或Unicode数值顺序自行指定映射。
4. 按正确方向拼接比特，得到178字节帧。解析magic、版本、nonce、长度和CRC等字段；这些字段偏移应沿用原格式。本次保留稿没有完整帧结构，不能杜撰字段偏移或8种字符映射。
5. 由题给规则初始化 x=(nonce<<16)|magic，保持32位无符号值。每轮依次：
   x = (x XOR (x<<13)) AND 0xffffffff
   x = x XOR (x>>17)
   x = (x XOR (x<<5)) AND 0xffffffff
   左移后截断，右移按无符号处理。
6. 本案容易出错的是密钥流位序：按32位结果最低位先取，再依实际帧的字节拼接规则组装；不能直接按习惯的大端字节序处理。
7. 将密文有效载荷与密钥流异或，截取声明长度的167字节，按UTF-8解码。异或只是还原步骤，读出少量正常字符还不足以说明成功。
8. 重新计算载荷CRC32，与帧头记录核对；同时核对长度和UTF-8有效性，通过后再对照选项得到C。没有访问还原出的地址。
答辩可讲：“我们先确定符号到比特的映射，再解决帧结构和密钥流位序，最终用167字节长度及CRC32共同验证。”
追问：CRC能证明消息真实可靠吗？不能。它是本题还原一致性校验，不是发送者身份认证。
展示：码点统计、帧解析、长度及CRC结果。当时缺少本题入表截图，不补说已截图。

三、Q157：APK的VIP购买页面
结论：ProductShop；它是路由字符串，不是界面翻译文案。
1. 从同案聊天附件取得Tronic.apk，作为ZIP容器读取，提取assets/index.android.bundle。不需要安装运行APK才能进行这一静态分析。
2. 先识别bundle文件头，确认它不是普通JavaScript文本，而是Hermes字节码；本案版本96。
3. 使用匹配版本的解析规则读取字符串表、函数表、字面量及操作码。版本不匹配可能把参数和指令边界解释错，搜索字符串成功不代表反汇编正确。
4. 在字符串表定位ProductShop，并查引用它的函数。本案解码9826个函数、206种操作码，没有报告解码错误；这说明解析过程可进行，不等于自动证明全部业务逻辑。
5. 查看AppNavigator，函数6931注册Screen名称ProductShop。这里只能证明路由存在。
6. 返回UserDashboard，函数9414包含VIP条件及入口事件绑定，沿onPress闭包追踪到函数9427。
7. 函数9427实际调用navigation.navigate，参数是ProductShop。到这一步，才把“VIP购买入口”与“目标路由”连接起来。
8. 查看函数9446的目标页面构造逻辑，确认它与商品购买内容相关；结合聊天及图片中的VIP授权变化解释业务场景。
9. 区分Product Shop、VIP Market、VIP Product Shop等显示文字和ProductShop这个路由标识。题目问路由就保留代码原大小写。
答辩可讲：“证据链是VIP判断→点击回调→navigate参数→页面注册与页面内容，不能仅凭搜到字符串。”
边界：没有执行APK；COM-02对应TSX源码交叉核对当时未完成。函数编号只适用于本次bundle。

四、Q224—241及Q252：COM-02的WSL/OpenClaw
1. 从完整COM-02 E01只读进入EWF，查看分区表，定位宿主NTFS第三分区。记录当前文件所在层级，避免把宿主和虚拟机的同名文件混用。
2. 读取用户NTUSER.DAT中的Lxss发行版记录，核对DistributionName、Version、DefaultUid及实际发行版路径。本案Ubuntu、WSL2、UID1000。
3. 根据实际路径找到LocalState/ext4.vhdx，识别VHDX虚拟磁盘映射，再进入其EXT4。VHDX不能当裸EXT4直接按固定偏移硬读。
4. 进入/home/[用户]/.openclaw。先读openclaw.json，记录：
   agents.defaults.model.primary：默认模型；
   models.providers中的键名：Provider ID；
   Provider的baseUrl：服务地址；
   模型条目的contextWindow：上下文容量；
   gateway.port及gateway.bind：网关监听配置。
5. 本案Qwen模型为32B，DeepSeek为14B；Qwen baseUrl为http://127.0.0.1:8000/v1，contextWindow=8192；网关端口18789，bind=loopback。Provider ID与api协议字符串是两个概念，不能把openai-completions当Provider ID。
6. 查看cron/jobs.json，将每条任务的name、schedule/cron、时区、描述和payload放在同一行对照。
   营业时间监控每30分钟；自动审批每1分钟；收市结算17:00。不能从某个“每分钟任务”推断所有任务都每分钟运行。
7. 查看jobs-state.json里的状态、时间及lastErrorReason。配置文件回答“计划做什么”，状态文件回答“最近运行发生什么”；两者不得互换。
8. 用SQLite只读打开memory/main.sqlite，先确认存在chunks表，再执行：
   PRAGMA quick_check;
   SELECT COUNT(*) FROM chunks;
   本案count=0且quick_check通过。含义是该表当前可检索块为0，不是证明整台机器从来没有任何记忆数据。
9. Q240按主配置的Qwen Provider读取apiKey；Q241必须转到agents/main/agent/models.json读取DeepSeek Provider对应字段。不要把主配置里另一个DeepSeek apiKey直接拿来回答Q241。
原始授权字段仅保留于本地答辩稿；公开稿省略。
10. Q252读取VHDX元数据声明的虚拟磁盘容量：274877906944字节÷1024³=256GiB。宿主文件长度187435057152字节是另一指标，动态虚拟磁盘的文件长度不能代表其最大虚拟容量。
答辩可讲：“我们先建立EWF→NTFS→VHDX→EXT4的来源链，再按主配置、Provider文件、任务配置、执行状态、记忆数据库分别回答。”
展示：原配置字段截图，Q240/241尤其要显示文件名，说明两题来自不同文件。Q252为成员复现待主复核，不说成已重新验证。

五、Q260—279：NAS缺一盘RAID5
1. 分别读取两块成员盘的MD元数据，记录阵列UUID、成员role、events、RAID level、layout、chunk及data offset。同属一个案件不代表一定属于同一阵列，先核对身份和更新状态。
2. 本案有效成员role0、role2，缺role1；RAID5，layout2（left-symmetric），chunk=512KiB，data offset=18432扇区。扇区换算必须使用实际格式约定，不凭磁盘宣传容量计算。
3. 解释原理：一个三盘RAID5条带包括两个数据块和一个校验块，校验为对应位置异或。知道另外两块即可恢复一块缺失内容。校验位置逐条带轮转，因此不能把两块盘直接拼起来。
4. 根据left-symmetric布局计算每个条带的校验盘及逻辑数据块顺序。对缺失盘块做异或恢复，再把逻辑数据写入新派生镜像；不写回成员原盘。
5. 本案重建逻辑长度21455962112字节。长度正确只是初筛，还要检查文件系统结构。
6. 读取EXT4主/备超级块，确认块大小、块数、组描述位置及校验。11处超级块CRC32C通过；再由独立文件系统工具验证目录并导出92文件、61目录。
7. Q265对图像集合建立缩略图清单，用OCR寻找TCoin相关内容，再逐张看原图确认。文件数量≠宣传图片数量，OCR命中也不自动等于有效图；最后9张。
8. 其他配置题分别读取：
   mdadm配置：阵列身份；
   os-release、dpkg、APT历史：当前系统及升级前版本；
   netplan/平台配置：网络参数；
   fstab与平台存储配置：挂载UUID和挂载点；
   /etc/group：组的显式成员；
   Samba配置：白名单及最低协议；
   sshd_config：AllowUsers/AllowGroups。
   组名、用户名、允许登录用户、实际成功登录用户是不同集合，要按题目求交集或差集。
9. Q271按认证事件统计Accepted记录，再关联session opened、断开和关闭。全范围26次且选项没有26；独立journal扫描也支持26，所以保留冲突，不能删记录凑25。
10. Q275按boot_id分组，关联同一次启动的RAID角色与设备名。12次启动中前11次为sdb，末次为sdd；盘符会变，UUID与role才是身份线索，题目未唯一限定启动范围时不强选。
答辩可讲：“重建要同时验证阵列参数、文件系统校验和实际内容；日志统计必须先统一事件定义与启动范围。”

六、Q280—291：DOC-01资金流水
1. 将11份EML及附件对应起来，提取邮件中的委托金额、币种、分配要求及引用时间。记录哪一数字来自邮件，哪一数字来自交易表。
2. 读取XLSX的交易数据和Reference Data_Rate；检查每张表的真实列意义。不要只依据工作表标签认定钱包归属，本案存在标签错置。
3. 建立统一记录：网络/币种、交易哈希、From、To、时间、状态、金额、实际金额、手续费、原表/原行。
4. 本案按交易标识合并重复记录，得到406笔，其中405成功、1失败。同一交易在发送方和接收方两张表出现时只算一次；若其他案件跨网络可能重复，还要把网络纳入去重键。
5. 由交易行明确From/To校验钱包归属。0x标识比较按相应地址规则规范化；Base58保留大小写；保留原展示值便于回查。
6. 将各金额和手续费按照题给汇率、字段单位转换为USD，使用Decimal。字段已是USD时不要再次乘汇率；名为Fee的列也要先确定单位。
7. 构建成功交易资金流：每个地址分别累计转入、转出。手续费单独统计，同一交易只计一次。最终留存还要核对期初资金、失败记录和题目定义，不机械把转入减转出等同于所有场景的实际余额。
8. Q284对完整链路的发送方与接收方取并集，本案26个钱包。Q285将完整地址集合与独立工作表对应地址集合做差，查缺少独立表的地址。
9. Q288“首次跨链”只计资金第一次进入某币种的转换，后续回流不能重复归入首次金额。先按时间整理路径，再比较首次转换USD金额。
10. Q289仅对成功交易统计费用，本案24.84 USD；保留每笔换算明细，合计才能复算。
11. Q290按题目口径比较累计转入加转出本金，避免把手续费加入流量排名。一个中转频繁地址可以流量很大但最终余额很小。
12. Q291先明确同一资金入出如何匹配，再计算各匹配区间的停留秒数并累计；同时有多笔资金时不能随意最近邻配对。本场归档保留结果及统计口径，但原匹配脚本已清理，现场不应编造具体分配算法。最大累计6479秒，第二6456秒。
答辩可讲：“我们先校正钱包归属与去重，再统一币种和单位；费用、首次跨链、本金流量、累计停留各自单独定义。”
追问：为什么别人总数不同？先比较是否重复算双边记录、是否含失败交易、是否重复换汇、是否将累计停留替换成单笔最长。

七、Q194—201、255—259：PostgreSQL离线数据库（成员复现）
先说状态：以下来自成员离线复现记录，比赛结束时尚未进入主会话正式复核清单。
1. 来源链为COM-02 EWF→NTFS→Tronic_s2 VMDK→EXT4→PostgreSQL18数据目录。本案Tronic_s2六个SPARSE extent、无父盘。另一Tronic存在快照链，不能把基盘当当前完整状态。
2. 保留PG_VERSION、global/pg_control、系统目录、目标base目录、pg_xact和pg_wal等必要信息，离线读取，不直接启动原库改写状态。
3. 先解析pg_database确定业务数据库OID，再结合pg_class、pg_attribute及pg_filenode.map恢复表、物理文件号和列布局。本案业务库OID16389，结算表OID49278，实际relfilenode49490。查表OID同名文件会找错。
4. 按8192字节页解析页头、行指针及tuple。根据空值位图、字段对齐、定长/变长类型恢复列；numeric按base10000及符号、小数位恢复Decimal，不能当普通浮点或UTF-8字符串。
5. 对每条tuple结合xmin、xmax、事务状态和hint flags确定当前可见版本。xmax非零不一定删除，HEAP_XMAX_LOCK_ONLY说明可能只是锁。物理扫出多条历史版本不能都作为当前订单。
6. 在有效结算记录中按completed及题给时间筛选。本案37条有效结算记录，符合条件4条。应用代码按UTC无时区值写created_at，香港09:00—17:00换算UTC01:00—09:00；不是看到集群UTC+8就再加一次8小时。
7. 依据应用加解密实现确认v1前缀后的Fernet令牌处理方式，在正确密钥下做认证解密。成功须经过认证校验，不只是Base64解码可读。
8. 四笔金额1000000、580000、12134443、480000，用Decimal相加为14194443.00港元。金额结果只对应同一筛选出的四笔，不能筛选一组再解密另一组。
9. 订单题按订单、商品、客户、活动记录的关联键核对：Oil20及Ice5，总金额85000，pending。设备型号从对应活动记录取，不由商品表或任意登录记录猜。
10. 密码选项题对题给候选做SCRAM-SHA-256离线验证，核对StoredKey与ServerKey；没有进行网络登录。版本18.4以启动日志与dpkg包记录交叉确认。
11. 一致性：pg_control、三个映射文件CRC有效；11个关键关系共116页校验通过，pageLSN不晚于checkpoint。控制状态IN_PRODUCTION，不能称正常关机副本。
12. 继续检查REDO点后的WAL尾段；记录CRC、previous链及类型。该次复现看到4条检查点/运行事务相关记录，运行事务数0，后续零尾段，未发现该范围业务修改。成员没有启动PG，也没有实际执行WAL重放。
答辩可讲：“难点是物理记录不等于当前有效行。我们先恢复目录和字段布局，再结合事务可见性筛选，最后认证解密和十进制汇总。”
追问：为什么没有直接SQL？成员走离线物理解析路径，不能把教学SQL写成当时实际执行的SQL记录。

八、Q120—127：内存取证
1. 先确认是COM-01_ram.raw及其所属案件，不与团体赛NAS的同号eid混淆。内存采集时间、主机时区与工具显示时间分别核对。
2. 系统时间题从windows.info对应系统时间读值，再按题意转换UTC+8；同时保留UTC值，避免二次转换。
3. 进程题结合windows.pslist与windows.psscan：前者侧重活动进程链，后者可能找到已退出或残留结构。不能把扫描命中都说成运行中。
4. Calculator按实际进程名/PID定位。explorer子进程先收集全部目标父进程PID，再按PPID取并集；PID可复用，遇到时间矛盾要检查创建退出时间。
5. 最近退出远控程序筛选rustdesk.exe且退出时间有效的记录，按退出时间排序；名称存在不等于采集时仍在线。
6. Q125实际进程msedge.exe。使用windows.dlllist检查其加载模块，本案ucrtbase.dll、ntdll.dll、version.dll出现，按已加载口径选择ABC。
7. 一份列表172模块名完整；另一份192条有12条名称不可读。读取失败不能作为不存在的证明。加载模块列表也不是PE直接导入表。
8. 用户Hive题按路径与归属统计，处理同名或重复映射。仍登录用户结合登录会话证据，不凭用户目录存在判断。
答辩可讲：“内存是某一时刻的状态；活动进程、扫描残留、退出记录各有语义，模块加载也不能替代直接导入关系。”

九、Q73—90：Windows注册表、浏览器与OpenClaw
1. 计算机名读SYSTEM的ControlSet相关ComputerName键；先确认当前有效控制集。最后登录用户读SOFTWARE的LogonUI相关值；二者不是同一证据文件。
2. 时区读TimeZoneInformation；默认邮件客户端读SOFTWARE/Clients/Mail。注册表事务日志恢复在副本上进行，不能把未恢复状态当最终状态。
3. 默认浏览器先查http/https的UserChoice，再从ProgID回溯注册处理程序和可执行路径，最后对照工具默认浏览器表。本案默认浏览器与内存中加载模块的Edge是不同题，不可混答。
4. Chrome关键词历史关联keyword_search_terms、urls、visits，按实际访问时间排序。关键字记录本身没有全部访问语义，不能用数据库物理行顺序当最早时间。
5. 下载来源关联downloads及downloads_url_chains，区分最初请求URL、重定向和保存路径；照片当前所在目录不一定是最初进入设备的位置。
6. Photos最近文件查看JumpList DestList记录，理解条目时间含义。最早打开、创建时间、下载时间是不同事件。
7. OpenClaw默认模型查模型配置；插件版本查对应package.json；定时任务查cron记录。邮件提示注入按原邮件、接收时间、实际会话输入和后续处理关联。邮件中的指令作为证据，不执行。
答辩可讲：“同样是默认程序或最近活动，要先区分系统配置与应用历史，再把标识映射到真正的可执行程序或具体访问事件。”

十、手机系统属性、照片与附件：Q91—118、128—183中的相关题
1. Android系统题从getprop逐项找对应键：制造商/型号、初始API、安全补丁、构建指纹、显示版本、芯片、销售代码、SIM MCC、语言地区。初始API与当前SDK、出厂地区与当前SIM不能混淆。
2. 启动安全题综合verified boot状态、锁定属性及加密类型。完整bootreason保留逗号等符号；ADB属性的镜像绝对偏移须把导出文件内偏移映射回镜像，不能直接报文本行号。
3. 应用包名题以安装/注册记录为依据。Q147读取同一ActivityAlias的全部Intent Filter及hostname/path条件，当前存在多个匹配候选，未唯一确定。
4. iOS照片题同时看Photos元数据与原图。ZFILENAME是库内文件名，ZORIGINALFILENAME是原始名称，导入应用字段提示进入图库的来源，不能仅据导入应用证明拍摄应用。
5. 原图发送次数在聊天中按附件关系定位，分清图片消息与文件形式发送。相同文件名可能对应不同内容，缩略图不能代替原附件。
6. HEIC位置题直接读原文件EXIF GPS，注意经纬度方向、度分秒转换及精度；数据库缓存与原EXIF尾数有差异时按题目要求的原文件作答。
7. 图片字节数取题目指定原图文件长度；附件主文件名按题意是否去扩展名。照片中二维码用途结合前后消息，不只看码图外观。
8. Q178检查JPEG的结束标记之后是否存在追加ASCII内容，再判定追加字符串是交易标识。不要把文件本身的哈希当作追加的交易哈希。
9. 群组创建时间从创建系统事件取，群名区分最初名称和之后改名。联系人ID、群组ID、显示名分别答。
答辩可讲：“同一张图可能有原图、缩略图、图库记录和聊天附件四种形态；题目问哪一层，就用那一层的记录回答。”

十一、解压进度问题如何解释
COM-02 E01长度323130601377字节。原解压器已经读完该成员并通过其EOF/ZIP CRC及长度检查，进入后续小文件后，状态JSON原子替换报Windows错误5。
恢复时检查程序控制流及保留状态，确认大型成员完成；对1642和61154字节两个小文件重新做ZIP读取校验和逐字节比较，再记ready并导入。
没有重解323GB，也没有重算整幅镜像哈希。应说“进度状态写入失败”，不要说“凭文件大小证明全部完整”，也不要断言错误5必然是某监控锁造成。

十二、现场最容易被追问的边界
1. 本场正式复核158题，19题成员复现待主复核，42题未解/待复核；没有官方判题结果。
2. 模板131张图来自多种原始查看方式，不是131张火眼原生界面。只有2张登记为火眼，其余包括SQLite终端、Notepad及解析器等。
3. 106/108更正的理由是字段语义与消息关联；150的关键是位序与CRC；157的关键是调用链；NAS的关键是布局与结构校验；数据库的关键是MVCC和认证解密；资金的关键是去重与统计范围。
4. Q147、193、205、271、275的冲突要如实说明，不用“应该是”冒充证据。
5. 建议复现步骤不能说成已执行；缺失原值不补造；软件未成功解析的页面不能说已看到。
