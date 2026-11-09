# GPT 八子代理工作制

## 固定分工：6＋1＋1

八人指八个不同 agent_id 的独立 GPT 子代理。主会话是队长，负责火眼准备、监督、独立复核与交付，不占八人名额。继承主会话 GPT 模型；不调用外部模型或旧 dsh 启动脚本，不递归委派。

| 成员 | 职责 | 默认研究方向或产物 |
|---|---|---|
| P01 | 解题手 | 设备、网络、系统 |
| P02 | 解题手 | 通讯录、身份、账号 |
| P03 | 解题手 | 安装卸载、浏览器、搜索 |
| P04 | 解题手 | AI 应用、会话、HTTP |
| P05 | 解题手 | 聊天、交易、钱包、社交媒体 |
| P06 | 解题手 | 可疑程序静态分析、压缩、哈希 |
| P07 | WP 编写者 | 本案件 wp/ 下完整题解 |
| P08 | 知识库整理者 | {KNOWLEDGE_DIR}/ 下方法与索引 |

六名解题手按真实检材调整研究方向；每个有效题号只分配一个 owns 主解，辅助证据方向记 support。跳过题不分配主解。题量少时给其余解题手具体辅助任务，不编造题号或结果。P07/P08 不承担主解或专职复核。

队长写 work/team/team-plan.json，逐项核对有效题号覆盖、唯一主解、角色、输入和输出目录。示例仅为字段示意，执行时替换真实题号：

~~~json
{"members":[
  {"id":"P01","kind":"solver","owns":["Q01"],"support":[]},
  {"id":"P02","kind":"solver","owns":["Q02"],"support":[]},
  {"id":"P03","kind":"solver","owns":["Q03"],"support":[]},
  {"id":"P04","kind":"solver","owns":["Q04"],"support":[]},
  {"id":"P05","kind":"solver","owns":["Q05"],"support":[]},
  {"id":"P06","kind":"solver","owns":["Q06"],"support":[]},
  {"id":"P07","kind":"wp","owns":[],"support":[]},
  {"id":"P08","kind":"knowledge","owns":[],"support":[]}
]}
~~~

## 原生调度与容量

1. 从当前系统工具说明确认并发容量、是否包括队长、可用槽位和返回/中断后是否释放槽位。使用当前原生多代理工具；本环境为 collaboration.spawn_agent 等，直接调用，不通过 functions.exec，也不使用 create_thread 创建用户侧聊天。
2. 初始化 brief.md、questions.json、prep.json、verified.json 与 team-state.json；首次 spawn_agent 调用前固定 started_utc 和 deadline_utc=started_utc+2700 秒。所有批次、准备等待、重试和归档共用此期限。
3. 至少能容纳队长加八个子代理时，直接调用 spawn_agent 创建 P01–P08，让其并行工作。task_name 用 p01 至 p08 等唯一名称；message 按 templates.md 填入角色、题目、绝对路径、允许写入目录和统一截止时间，保存为成员 prompt.txt。默认继承父模型，不指定其他模型。
4. 总槽位只有 4 时，队长外最多同时 3 个。若平台支持完成后释放槽位，按实际可用槽位分批创建独立成员，例如 P01–P03、P04–P06、P07–P08；材料依赖和已复核结果允许时可提前安排归档成员。不要凭空认为 completed 或 interrupt_agent 会释放槽位；先依据工具说明/实际返回确认，不调用不存在的 close/release 接口。
5. 若槽位按存活代理累计且没有释放接口，不能保证创建八人：记录已创建和未创建成员、真实限制，明确报告“八子代理未达成”。可由现有成员继续各自任务、队长完成余项，但不能把角色轮换计作八个独立代理，不通过新聊天、嵌套代理或外部进程绕过容量，也不自动修改全局设置。
6. 返回成功后立即登记真实 agent_id 和角色映射。通过 send_message 协调活动成员，followup_task 继续已返回成员的同一职责，list_agents 核实状态，wait_agent 接收更新；具体参数以当次工具说明为准。队长同步运行火眼准备、消费检查点与独立复核。
7. 一个批次返回不等于六名解题手全部结束。尚有未派发成员且可释放容量时继续调度；同一角色的可恢复启动失败仅重试一次，保留原期限与旧 agent_id 的尝试记录。不得同时保留两个该角色写入者。

## 状态与八人验收

队长唯一维护团队状态与成员 state.json，成员独写 progress.json、answers/、exports/、drafts/ 和实际工具日志。team-state.json 至少记录：

- started_utc、deadline_utc、phase、stop_reason。
- capacity、peak_active、started_count、responding_count、pending_members。
- members：member_id、role、agent_id、attempt、status、started_utc、ended_utc、output_dir、output_evidence、stop_confirmed、outstanding_jobs。
- eight_agents_verified：八个不同 agent_id 均有符合角色的实质输出才为 true。未知信息用 null，不用猜测补齐。

仅有八条分工、八个目录或八次调用不构成验收；重试 ID 不计作新角色，单代理轮换角色也不计作多人。分批参与的八人与同时在线八人分别报告。工具调用成功以实际输出为据，不能以自述证明已调用火眼。completed 只表示代理本次返回，答案还需独立复核。

## 归档与单一写入者

P07 独写 wp/；P08 独写用户知识库。遍历完整questions.json，逐题读取正式answer快照中的答案、范围、状态、版本和证据，并用verified.json核对已确认条目。不读取成员旧候选充数；未解、撤回及跳过题保留章节或状态，不以不在verified中为由漏掉。无已确认答案时也可整理正式缺口、已核实失败原因与未决冲突，但不能把候选写成事实或将未复核算法写成方法。

容量充足时持续消费新版本；分批时处理派发时的已确认版本并返回，后续有新结果由队长按实际工具能力续派同一成员。不让归档代理空等占满解题槽位。progress.json 写已处理题号、消费版本、实际发布文件和待办；知识库按现有主题查重增补，保留旧知识，通用条目脱敏。无写权限时保留在自己的 staging 并标未发布，不扩大无关目录权限。

较大的WP任务按题或小批落盘正文与证据索引，不能只汇报“已读取几十题”而所有正文仍在上下文中。单题缺图或缺记录，先存已有正文与缺口，继续独立题。中断后队长先核对实际代理存活状态、文件及最后完成题号；确认旧写入者停止后才改派。接续阶段可按类别分派互不重叠的草稿目录，队长统一合并；不将这一写作分工计作首轮八人达成。

全解或六名解题手结束且候选复核完后设置 analysis_complete=true，另记 all_questions_resolved、needs_review 与 skipped_ids；前者只代表本阶段收口。全解立即交答案，归档不延迟交付。队长确认对应写入者停止后才接管 wp/ 或知识库。

## 截止、停止与接续

每 20–30 秒结合消息/文件查看进度，每次工具等待不超过 60 秒且不超过剩余预算；队长继续独立准备。到期取消待派发首轮任务，立即 interrupt_agent 所有仍活动的本轮成员，记录工具返回和实际停止时间。用户要求停止时同样处理，且不再接续分析。

原生中断不等于操作系统进程树清理，不承诺旧脚本式硬性 watchdog。核实成员登记的工具会话、实际 PID/启动时间（仅如存在）、job_id/task_id；只处理本任务可安全停止的对象。共享火眼服务和用户原有任务不停止。无法确认的状态标 stop_confirmed=false 并交接，不接管尚可能被写入的目录。

超时或提前结束先交付已复核答案、未解题与实际人数/结束原因，再写 handoff.json 并由 GPT 接续。正常到期不自动新开第二轮 45 分钟；补交检材与纠错沿用检查点，不重启八人。旧案件保留原始来源字段，当前新增答案写 source_model=GPT、真实 source_member、source_agent_id 和 phase。

## 验证范围

文档静态校验不能证明八个代理已经成功运行。下一次真实题组需依据实际代理返回与产物验收，不为维护技能启动真实取证或消耗八名解题代理。归档验收按 [verification.md](verification.md)，检查值、范围、方向和关键统计，不能只检查文件存在或版本号。
