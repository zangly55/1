# Android 应用取证（GES）：清单、版本、账号与聊天数据

- 条目 ID：KB-TOPIC-ANDROID-APP-001
- 状态：通用方法；实例见 [案件20261022195255R](../cases/20261022195255R-android-phones.md)（Q01—Q03、Q05—Q09、Q11—Q14 已复核）
- 适用条件：Android 手机 E01 已经火眼 GES 解析完成，题目问“安装了多少款某类应用”“某应用的包名/版本/登录用户名/登录密码”“某应用是否安装/运行过”“某应用首次打开时间”“扫描了几个 IP/主机”“向某人发送了几个文件”，或需从聊天应用还原控制链。
- 来源：案件 20261022195255R 的已复核答案（Q01—Q03、Q05—Q09、Q11—Q14）、GES CLI 文档与本机实测查询。

## 数据源与互证

同一“已安装应用/应用身份”问题至少有六类可互相印证的数据，作用不同，不能混用：

1. **火眼应用列表**：`/case/<案件节点>/基本信息/应用列表/data.csv`
   已安装应用清单，通常含应用名称、包名、版本、安装时间、是否系统应用。统计“安装数量”时以它为全集。
2. **APK 列表**：`/case/<案件节点>/App分析/APK列表/data.csv`
   APK 元数据（名称、包名、版本、大小、路径）。它证明“存在安装包”，可能包含未安装、残留或重复的 APK，不能单独当已安装全集。
3. **系统包登记**：`/evidence_mounts/eid-<eid>/<镜像>/分区<N>/system/packages.list`
   证明包被系统登记为已安装，适合做第二来源。
4. **应用私有目录**：`/evidence_mounts/eid-<eid>/<镜像>/分区<N>/data/<包名>/`
   仅目录存在不足以证明曾运行，须结合首次启动字段、数据库或日志；卸载后目录可能残留，不能单独证明“当前已安装”。
5. **应用配置 `shared_prefs/*.xml`**：常含当前客户端版本、OTA 版本、当前账号 ID、username/globalName、release channel 等运行态字段。
6. **键值/消息库**：如 Discord 的 `files/kv-storage/@account.<id>/a` 是 SQLite（`messages0` 等表），保存聊天正文、作者、机器人消息与配对提示；导出后用只读方式查询。

## 标准步骤与命令

```powershell
# 1. 绑定已就绪案件（cid/url 必须来自 prep.json 的 ready 绑定，案件号与简报一致）
ges.exe status --json
ges.exe --cid <cid> --ges-url <ges_url> case ls --json

# 2. 先发现案件节点，再读应用清单
ges.exe ls /case/ --json
ges.exe read "/case/<节点>/基本信息/应用列表/data.csv" --offset 0 --limit 200

# 3. APK 列表与包名确认
ges.exe read "/case/<节点>/App分析/APK列表/data.csv" --offset 0 --limit 100

# 4. 系统包登记（原始挂载，无溯源句柄）
ges.exe read "/evidence_mounts/eid-<eid>/<镜像>/分区<N>/system/packages.list" --offset 0 --limit 200

# 5. 私有目录存在性（先有界 glob，不猜全盘）
ges.exe glob -p "**/*" --path "/evidence_mounts/eid-<eid>/<镜像>/分区<N>/data/<包名>/" --json
```

引用 `/case/` 记录时先 `read` 取文件顶部真实 `Goldeneyes://<case_number>/<node_id>` 基址，再追加正文行号；`/evidence_mounts/` 与 `ges copy` 导出物没有溯源句柄，不能标链接。

## 版本与账号字段

- **版本三处互证**：APK 列表的版本号（如 `311.20 - Stable`）、`BundleUpdater.xml` 的 `ota_version`、`CacheStore.xml` 的 `client_version`（如 `311.20 - rn`）。题目给数字格式时取数字部分，渠道后缀保留在说明中；三处不一致时并列并说明取值。
- **账号字段分离**：`CacheStore.xml` 的 `users` 数组与消息库里的 `author` 同时给出 `username`（可能带尾点，如 `test901234.`）与 `globalName/global_name`（如 `test901234`）。题目问“用户名”时要判断是 handle 还是显示名，答案与说明分别写清；不能直接把带点 handle 当显示名。
- **账户节点**：`/case/<节点>/<应用>/<账号名(账号ID)>/账户信息/data.csv` 可交叉确认当前登录账户；引用时按 `read` 顶部基址加行号。

## 聊天应用作为控制通道

聊天应用（Discord 等）可能被用作 PC agent 的 C2 通道，判定要看消息内容而非应用功能：

1. 在消息库中检索机器人提及、IP、扫描/爆破命令（nmap、gobuster、sqlmap、hydra 等）与配对提示。
2. 机器人消息常自述产品名（如 Hermes Agent），并给出 `pairing approve <平台> <配对码>` 一类命令；配对码属于凭据，知识库脱敏，原值只留题解。
3. 用应用列表/APK 证明客户端已安装，用账户信息证明登录身份，用消息库证明控制行为，三者链式成立才下结论。

## 扫描目标 IP 统计

1. 先锁定“该应用”对应的账号与消息库（依赖前序题，如 Q05=Discord），导出 `kv-storage` 的 SQLite 连同 `-wal`/`-shm`。
2. 提取IPv4后先分用户请求、工具调用、工具结果。问实际扫描时仅纳入有扫描调用支持的目标，再按IP去重，不能将所有请求算成已扫描。
3. 同一目标重复调用只计1；ping本身仅为探测，须结合nmap等扫描调用。摘要目标截断时用任务请求、相邻完整目标和后续调用交叉归属，注明不等于完整执行日志。
4. 记录覆盖：消息条数、频道数、时间范围、是否含 WAL/SHM、是否回扫空闲页；区分“用户要求扫描”与“机器人实际执行”。

## 加密聊天库（Flutter + SQLCipher）

部分内部通联应用是 Flutter 开发、数据库用 SQLCipher 加密，步骤：

1. **识别框架**：应用目录存在 `libflutter.so`、`shared_prefs/FlutterSharedPreferences.xml`（键名带 `flutter.` 前缀）。
2. **找库口令**：配置里常见 `flutter.db_password` 字段，但不应直接当口令使用；需按应用自身逻辑变换（如截取子串）后，在导出副本上验证能否打开。验证成功才继续，不能猜口令或把外部题解口令直接套用。
3. **完整导出**：`ges copy` 数据库时连同 `-wal`/`-shm`（必要时 `-journal`）一起复制；原检材只读，所有解密/查询在副本上做。
4. **表结构**：常见 `user`、`friendship`、`conversation`、`conversation_member`、`message`、`message_file`，身份与附件分别落在 `user` 与 `message_file`。
5. **应用层加密**：消息正文可能再做 AES 加密，密钥/IV 存在 `user.config_data` 一类字段；先全部解密成功，再统计正文与附件，避免只统计到密文条数。
6. **文件发送统计**：`message_file` 与 `message` 按 `message_id` 关联，限定会话名/发送者/`type=file`，按 `message_id` 去重；再用全表 `message_file` 行数做闭合校验（如全库仅 2 条附件、目标会话也是这 2 条）。

口令、密钥、IV 属于凭据：知识库一律写“已脱敏，见题解”，不抄原值；案例页只保留方法链路。

## 账号口令哈希复核

题目问“账号登录密码”时，数据库里通常只有 `password_hash` + `password_salt`，需要本地复算而不是猜：

1. 在导出副本的 `user` 表读取 `password_hash`（常见 64 位十六进制）、`password_salt`、`username`。
2. 先确认散列方案。按优先级试：`SHA256(password+salt)`、`SHA256(salt+password)`、双层 `SHA256(HEX(SHA256(password+salt)))`、PBKDF2 等；每试一种都与库值逐字节比对，命中才记录。
3. 候选生成要有界（如 8 位数字全空间），保存脚本与命中日志；失败只说明该方案/空间未命中，不能断言“无密码”。
4. 外部题解给的值只能当候选，必须用本地 `password_hash` 复现后才可采信；前导 0、大小写、十六进制编码都要原样保留。
5. 严格区分**数据库加密口令**（SQLCipher）与**账号登录密码**：同一应用里两套凭据用途不同，不能互相替代。

明文、盐、散列值、数据库口令在知识库中一律脱敏，原值只留题解。

## 首次打开时间（first_open）

“首次安装”与“首次打开”是两个字段，题目问首次打开时优先查应用自身的启动/统计记录：

1. Firebase 统计的 `first_open_time` 常落在应用私有目录的 `shared_prefs/com.google.android.gms.measurement.prefs.xml`，值是 Unix 毫秒：

```powershell
ges.exe read "/evidence_mounts/eid-<eid>/<镜像>/分区<N>/data/<包名>/shared_prefs/com.google.android.gms.measurement.prefs.xml" --offset 0 --limit 20
[DateTimeOffset]::FromUnixTimeMilliseconds(<值>).ToOffset([TimeSpan]::FromHours(8)).ToString('yyyy-MM-dd-HH:mm:ss')
```

2. 设备时区从同一应用的 `setup.log`（`Timezone: Asia/Shanghai`）确认；不要凭主机时区或火眼界面时区直接套用。
3. 应用日志里可能还有第二次初始化/启动时间（如环境初始化），不能当首启；以 `first_open_time` 或最早的使用记录为准。
4. 毫秒按题目格式截断到秒，并在答案中注明截断；时间格式示例只表示位数，不改变实际时区。

## 计数与归类口径

- 全集：应用列表的实际条数（如 90、91 条），按包名去重；题目说“安装”时明确是否排除系统预装应用。
- “款”按独立包名计：同一产品的正式版与极速版（如抖音与抖音极速版、快手与快手极速版）是两个包，通常分别计数；若题目定义不同，须在 `assumptions` 说明。
- 分类字段只是参考：火眼分类可能没有题目要的类目（如“理财”“短视频”），或把某应用归入“其他”。应逐条按应用实际功能判断，并在 `assumptions` 写明归类口径。综合视频社区、视频编辑工具不要自动算作短视频平台。
- 有争议时并列候选与依据（例如只按“股票网银”字段为 3 款，按实际理财功能含虚拟资产交易为 4 款；或把哔哩哔哩计入短视频得 5），确定答案选一个口径，其余候选标 `rejected` 并写理由，不把候选混入答案栏。
- 统计题必须记录 `coverage`：总记录数、去重键、纳入/排除清单、数据源是否完整（`next_offset=null` 且 `source_complete=true`）。

## 易错点

- 题干答案格式（如 `com.xxx.ui`）只是排版示例，不是包名约束；真实包名可能是 `gptos.intelligence.assistant` 这类非 `com.` 前缀，必须按检材记录作答。
- 应用列表条数（如 90、91）与 APK 条数（如 27）不是同一范围；把 APK 条数当安装数会错。
- 应用名称可能含功能描述词（如“优质客户AI判定”“OpenClaw & Codex - Anyclaw”），与题目俗称/措辞不完全一致；“龙虾”这类俗称要回到 APK 名称、应用内配置目录（如 `.openclaw`）双重核对，不按名称字面猜包名。
- “安装时间”不是“首次打开时间”；首启要查 `first_open_time`/使用记录/启动日志，不能拿 `firstInstallTime` 代替。
- 同一应用日志里的后续启动/初始化时间不能当首启；注意区分第一次与第二次启动。
- 私有目录存在本身不能证明当前已安装或曾主动运行；须结合包登记与运行痕迹，卸载残留需排除。
- 同名应用多版本、多包名（马甲包）要按包名分别统计；不能只按应用显示名去重。
- 火眼展示时间与原始字段可能有时区差异，涉及时间题要回到原始字段并注明时区；Unix 毫秒按设备时区换算后再格式化。
- `files/kv-storage/@account.<id>/a` 这类无扩展名文件可能是 SQLite（文件头 `SQLite format 3`），不能只当文本 grep；导出副本后以只读方式打开，确认表名（如 `messages0`）再查询。
- 消息库可能含空闲页/删除残留（如更早的配对码、已删消息）。统计当前有效记录时以活动消息为准，残留只作历史线索；不能因残留存在就改写当前答案，也不能声称旧值从未使用。
- 统计“几个 IP/几台主机”时按目标去重，不按指令条数；重复的“继续扫描”不能加一。
- 账号字段末尾的点号、下划线等是字段原值的一部分；先判断题目问 handle 还是显示名，再决定是否去掉，不能机械裁剪后当唯一答案。若正式答案文件的 `answer` 字段与 `publication_note`（或正文说明）冲突，按复核规则暂不发布该题结论，标待复核并交 GPT 修正，不自行二选一。
- 不要重复执行队长已登记的打开、init、导入、索引与解析任务；成员只做有界查询并导出到本人目录。

## 证据来源

- `answer/Q01.json`、`answer/Q02.json`、`answer/Q03.json`、`answer/Q05.json`、`answer/Q06.json`、`answer/Q07.json`、`answer/Q08.json`（配对码已脱敏）、`answer/Q09.json`、`answer/Q11.json`（登录密码/盐/散列已脱敏）、`answer/Q12.json`（数据库口令/消息密钥已脱敏）、`answer/Q13.json`、`answer/Q14.json`（20261022195255R，GPT 复核）。
- 查询命令和命中行号见案件页；本条目不复制具体答案，只提炼方法。


GPT补充复核：Discord messages0的实际列是data等键值字段，正文位于data前导类型字节之后的JSON message对象，不能直接SELECT不存在的content/timestamp列。保留原样WAL/SHM，另复制分析副本以免SQLite checkpoint改变原样导出。提取紧邻中文的IPv4时不使用Unicode词边界，改用数字/点的前后断言。


### 工具计数的口径与摘要截断
“暴力破解”未限定口令时，不能机械排除目录字典爆破工具。按实际命令和工具功能分类，重复调用同一工具不重复计种类。聊天摘要存在2000字符上限或增量版本时，先复核WAL历史版本；最长版本仍截断只能给可见工具下限，不能推断全部总数。非官方WP的一致值不能替代完整性证据。

### 2026-10-22纠错实例
本案Q09原3个请求目标误作已扫描目标，现按可见调用改1。请求、调用、成功结果分别统计。版本号保留尾零，username与globalName分别保存，不能迎合参考正文改原值。
