# 2026 精武杯服务器取证 WP（公开脱敏版）

## 来源、覆盖范围与公开边界

- 原始附件：`解题WP_服务器取证_59-70(1).docx`。
- 覆盖范围：原 WP 已解Q59—66、68—70，共11题；Q67及Q71—88仍在分析中，未收录答案，不能把文件名59—70理解为12题全部完成。
- 脱敏说明：Q61管理安全入口、Q62密码哈希、Q64口令、Q66/Q69 API Key在汇总和过程段落全部替换。仅发布转写后的Markdown，不上传含原值的DOCX及其元数据。

整理日期：2026-11-13。来源为用户上传的 WP；本次只做文本核对、格式整理与公开脱敏，未重新分析 E01、pcap、数据库或服务运行状态，也未取得判题反馈。“原 WP 已核实/已解”只指原报告所述证据状态，不代表官方答案或本次独立复验。文中命令是原 WP 的复现记录，本次未执行。检材路径、案件号、文件字段和帧号保留供溯源；原始附件及检材未公开上传。

补充边界：Q63依据部署说明和容器映射，不增写实时监听验证；Q65原 WP 记述已统计162条，但未附完整查询输出；Q62保留原报告的算法判断边界。

检材：服务器镜像.E01

工具：弘连火眼 GES 命令行（ges）

范围：第 59–66、68–70 题（已解）

## 一、答案汇总

| 题号 | 考点 | 答案 |
| --- | --- | --- |
| 59 | 操作系统的版本 | Ubuntu 22.04.5 LTS |
| 60 | 根文件系统(/)的UUID | ea044f8e-b4ad-4151-a508-135bf5e57a94 |
| 61 | 运维面板安全入口 | [面板安全入口已脱敏] |
| 62 | 面板管理员密码哈希(MD5) | [管理员密码哈希已脱敏] |
| 63 | 知识库监听端口 | 3001 |
| 64 | 知识库登录密码 | [知识库登录密码已脱敏] |
| 65 | LanceDB 向量数量 | 162 |
| 66 | 知识库智谱 API Key | [智谱 API Key 已脱敏] |
| 68 | dsh(DeepSeek Harness) 版本号 | 0.1.1-rc.2 |
| 69 | dsh 配置的 DeepSeek API Key | [服务器端 DeepSeek API Key 已脱敏] |
| 70 | DSH 用户安装插件数量 | 5 |

## 二、解题过程

### 第 59 题  该服务器的操作系统版本是什么？

答案：Ubuntu 22.04.5 LTS

解题过程：

在原始检材根分区的系统发行版本文件中读取：/evidence_mounts/eid-1/分区5/etc/os-release（实际文件为 /usr/lib/os-release）。

文件内容中 PRETTY_NAME="Ubuntu 22.04.5 LTS"，即服务器操作系统版本。

辅助佐证：GES 检材信息中操作系统同样识别为 Ubuntu 22.04。

### 第 60 题  该服务器的根文件系统（/）的 UUID 是多少？

答案：ea044f8e-b4ad-4151-a508-135bf5e57a94

解题过程：

读取分区表配置文件：/evidence_mounts/eid-1/分区5/etc/fstab。

其中根分区挂载行：UUID=ea044f8e-b4ad-4151-a508-135bf5e57a94  /  ext4  defaults  0  1。

该行的 UUID 即根文件系统（/）的 UUID。

### 第 61 题  该服务器部署的运维面板安全入口是什么？

答案：[面板安全入口已脱敏]

解题过程：

服务器部署小皮面板（XP.cn，目录 /xp），面板配置存于 SQLite 数据库 /xp/db/app.db。

用 ges copy 将 app.db 连同 -wal/-shm 复制到本地，再用 sqlite3 查询 panel_cfgs 表。

命中记录 ('panel','Entry','[面板安全入口已脱敏]','3')，其中 value 字段即面板安全入口：[面板安全入口已脱敏]。

### 第 62 题  该面板管理员密码的哈希值（32位MD5）是多少？

答案：[管理员密码哈希已脱敏]

解题过程：

同 /xp/db/app.db，查询 users 表。

管理员记录：username='xiaopi'，password='[管理员密码哈希已脱敏]'。

原 WP 将该 password 字段按题干要求记为 MD5 哈希。整理注：32位十六进制外观本身不足以单独证明哈希算法；本次未补验应用实现，原值已脱敏。

### 第 63 题  该服务器部署的知识库监听端口是什么？

答案：3001

解题过程：

服务器部署 AnythingLLM 知识库，目录 /opt/anythingllm，部署说明见 /opt/anythingllm_DEPLOY.md。

部署文档与容器端口映射均显示 3001:3001，知识库对外监听端口为 3001。

### 第 64 题  该知识库的登录密码是什么？

答案：[知识库登录密码已脱敏]

解题过程：

读取知识库环境变量文件：/opt/anythingllm/storage/.env。

其中 AUTH_TOKEN='[知识库登录密码已脱敏]'，即知识库的登录口令/访问密码。

### 第 65 题  部署的知识库向量数据库（LanceDB）中存储的向量数量是多少？

答案：162

解题过程：

知识库使用 LanceDB 作为向量库，向量表为 document_vectors。

/opt/anythingllm_DEPLOY.md 记载“工作区文档 32 篇、document_vectors 162 条”。

对 LanceDB 数据实际统计得到记录数 COUNT = 162，与文档一致。

### 第 66 题  知识库中配置的智谱 API Key 是什么？

答案：[智谱 API Key 已脱敏]

解题过程：

同 /opt/anythingllm/storage/.env。

其中 LLM_PROVIDER='zai'（智谱），ZAI_API_KEY='[智谱 API Key 已脱敏]'。

该值即知识库配置的智谱 API Key。

### 第 68 题  dsh（DeepSeek Harness）的版本号是多少？

答案：0.1.1-rc.2

解题过程：

dsh 部署于 /opt/dsh，源码仓库位于 /opt/dsh/repo。

读取仓库根 package.json（包名 @deepseek-ai/dsh-root）与 apps/cli/package.json（包名 @deepseek-ai/dsh，dsh 命令入口）。

两者 version 均为 0.1.1-rc.2，即 dsh 的版本号。

### 第 69 题  dsh 中配置的 DeepSeek API Key 是什么？

答案：[服务器端 DeepSeek API Key 已脱敏]

解题过程：

读取 dsh 用户配置目录下的凭据文件：/opt/dsh/dsh-home/.dsh/.credentials.yaml。

内容：refs:  DEEPSEEK_API_KEY: [服务器端 DeepSeek API Key 已脱敏]。

该值即 dsh 配置的 DeepSeek API Key。

### 第 70 题  DSH 中用户安装的插件数量是多少？

答案：5

解题过程：

dsh 通过 profile 管理插件，插件清单记录在 /opt/dsh/dsh-home/.dsh/profiles/web/package.json。

dependencies 中用户安装的插件共 5 个：@dhicoc/dsh-reverse-skill、dsh-better-sidebar、dsh-dream-skin、dsh-skill-hub、dshmarket。

（bundles 列表中的 @deepseek-ai/dsh-base、@deepseek-ai/dsh-web-app 为内置模板，不计入用户安装。）

故用户安装的插件数量为 5。

说明：第 67 题（LUKS 加密卷解密口令）及第 71–88 题仍在分析中，本报告仅收录当前已确认的题目。
