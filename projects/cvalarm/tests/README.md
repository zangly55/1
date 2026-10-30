# 测试目录说明

本目录是**工程唯一的测试位置**：单元测试、命令级冒烟、报告结构与渲染检查全部在这里。
被测试的代码在 `../cvalarm/`，测试不修改工程源码，也不写工程的 `state/` 与 `runs/`
（全部使用临时目录）。

## 怎么跑

```bash
# 推荐：一键跑全部（逐文件统计，打印汇总表）
python tests/run_all.py
python tests/run_all.py -v          # 显示每个用例
python tests/run_all.py -k fsm      # 只跑文件名含 fsm 的文件

# 标准 unittest 方式（两种都支持）
python -m unittest discover -s tests
python -m unittest tests.test_fsm -v

# 也可以从命令行工具里跑
python run.py selftest              # 配置自检 + 全部单元测试
```

要求：Python 3.10+，**无需安装任何第三方包**。唯一的可选依赖是 `node`，
只用于"真正执行报告页 JS"的深度检查；没有 node 时该文件自动 skip，其余照常。

## 文件清单（15 个测试文件 / 219 个用例）

| 文件 | 覆盖内容 |
|---|---|
| `test_geometry.py` | 多边形 ROI（含边界语义）、IoU、锚点、分位数、Wilson 区间 |
| `test_tracker.py` | ByteTrack 两级关联续轨、新轨迹阈值、丢失淘汰、类不匹配、预测幂等 |
| `test_fsm.py` | 六状态全分支、防抖计时、离开确认、遮挡容差、三种植入策略、身份不符→丢失、窗口超期、丢帧不算离开 |
| `test_locator.py` | Kadane 解码、标定、bin 特征、三向分流 8 条路径、遮挡已解释、审计样本不降级 |
| `test_rules.py` | 条件求值、静态校验 8 类、引擎优先级与平级次序、暂存/发布/回滚/账本、回归门禁 |
| `test_card.py` | 卡片结构校验（含 evidence/provenance）、签名与防篡改、错误密钥 |
| `test_metrics.py` | ROC-AUC、事件匹配（TP/FA/重复/容差/跨机位/转人工/抑制）、误报合并、TTA |
| `test_cost.py` | 成本公式逐项、r1/r2 实测、灵敏度是否落在论文范围、三拓扑、无效拓扑 |
| `test_pipeline.py` | 端到端确证/抑制、指标与条件召回、卡片完整性、采集中断不冒充告警、产物落盘 |
| `test_feedback.py` | 驳回必须给理由、非法理由拒绝、选择偏差提示、漏检率置信区间 |
| `test_server.py` | 看板首页、7 个 API、404、反馈回传校验、`/media` 全量与 Range(206) 回放 |
| `test_docx_alignment.py` | 双时延口径、定位精度与存在性分离、证据回放块、溯源、资源与模型记录、开发/测试隔离、首版单镜头两类事件、接口探测 |
| `test_cli.py` | **命令级冒烟**：init/demo/run/probe/test-report/calibrate/report/metrics/cost/rules/bench/feedback/export-frames 的退出码与产物；错误路径的退出码 |
| `test_report_html.py` | **报告结构检查**（纯 Python）：容器 id 齐全、脚本引用的 id 都存在、页面完全自包含、内嵌数据与磁盘产物一致、卡片校验与签名、面板数据完整性 |
| `test_render_js.py` | 可选：用 node + 最小 DOM 桩真正执行一次渲染脚本，确认所有面板都被写入、证据示意图按卡片生成 |

## 支撑文件

| 文件 | 作用 |
|---|---|
| `helpers.py` | 共用夹具：`TinySource`（最小可运行数据源）、`obs()`/`make_fsm()`（状态机观测构造）、`default_config()`、`make_run()`（生成一份含报告的运行产物）、安全读取助手 |
| `render_check.js` | DOM 桩执行器（node）：加载报告页脚本、记录每个面板的 innerHTML、断言面板非空与证据块数量 |
| `run_all.py` | 全量运行器：逐文件统计用例/失败/跳过/耗时并汇总 |
| `__init__.py` | 让 `import helpers` 在 `discover` 与 `python -m unittest tests.xxx` 两种方式下都成立 |

## 约定

1. **每个用例自带临时目录**（`tempfile.mkdtemp`），跑完即弃；不写工程目录。
2. **不依赖网络、不依赖 GPU、不依赖第三方包**；`node` 缺失只影响一个可选文件。
3. 需要标注"未配置/未测得"的行为，测试里必须断言它**如标注**（例如 `probe` 的未配置项返回 warn，
   `resources.gpu.used == False`），防止以后悄悄改成"假装通过"。
4. 新增测试：文件名以 `test_` 开头即可被 `run_all.py` 与 `discover` 自动发现；
   需要共享夹具时放进 `helpers.py`，不要在用例之间相互 import。
