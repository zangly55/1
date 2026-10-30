# cvalarm 1.1 · 可复现的告警流水线参考工程

本版修复运行、模型接口、评测和人工复核问题。默认运行是**合成检测数据 + 参考定位器 + 规则核验器**，用于验证工程行为。YOLO、VideoJev、Qwen 的真实权重、视频、推理服务和性能数据未随包提供，也未实测。

完整进度、缺失项、优先级与验收条件见 [项目明细](项目明细.md)。

从 GitHub 克隆整个仓库后，先进入项目目录：

```bash
git clone https://github.com/zangly55/1.git
cd 1/projects/cvalarm
```

## 最短复现路径

需要 Python 3.10+；建议先用 Python 3.12。本轮在 Windows / Python 3.12.14 验证。默认流程只用标准库，不需要显卡、联网或安装依赖。

在解压后的 cvalarm 目录执行：

```bash
python run.py demo --profile v1 --out runs/v1
python run.py test-report --out runs/test-report --state-dir state/holdout
python -m unittest discover -s tests -v
python run.py serve --run runs/v1 --port 8080
```

浏览器打开 http://127.0.0.1:8080/ 。展开告警卡，可填写操作员、选择结论和理由并提交复核。直接打开 report.html 是只读报告；服务看板读取已落盘的运行结果，不代表摄像头实时接流。

首版两类事件准确含义：ROI-A **进入后累计在场达到 45 秒**；ROI-D **累计在场达到 300 秒**。遮挡重关联记录会保留，累计在场不等于连续在场。

默认 demo 为 3 小时合成时轴，处理通常只需几秒；耗时受电脑影响。指标以本次生成文件为准，旧版本演示数值不可当作本版验收值。

## 跨电脑使用

源码版用相对路径，运行目录相对工程根目录；安装版运行目录相对命令的当前目录。移动整个源码目录后不需要修改盘符或用户名。不要把自己的绝对媒体路径写入共享配置。

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install .
python -m cvalarm demo --profile v1 --out runs/v1
```

离线时可直接运行源码。完整 ZIP 交付包附带通用 wheel；GitHub 源码仓库的 dist 不跟踪构建产物，先在构建机运行 python -m pip wheel . --no-deps -w dist，再把 wheel 带到离线环境：
```bash
python -m pip install --no-index --no-deps dist/cvalarm-1.1.0-py3-none-any.whl
```

wheel 已包含默认配置、规则和首版档案。状态和结果不写入 site-packages。详细说明见 [复现指南](docs/复现指南.md)。

## 模型接入边界

| 环节 | 默认实现 | 已提供的外部接口 |
|---|---|---|
| 检测 | 合成帧检测数据 | JSONL 检测结果回放；自定义 FrameSource |
| 跟踪 | 本工程两级关联与卡尔曼参考跟踪器 | 不宣称等同官方 ByteTrack |
| 定位 | 启发式打分 + Kadane | 外部分数文件；带图像的 HTTP 时序评分协议 |
| 核验 | 规则对照 | 支持 image_url 和 JSON Schema 的兼容 chat/completions 服务 |
| 授权 | 合成演示许可 | 明确声明完整性的外部授权 JSON |
| 复核 | 静态报告 / 本地服务看板 | 绑定 run_id + alarm_id 的反馈 API |

详见 [适配指南](docs/适配指南.md) 和 [示例配置](config/model_services.example.json)。HTTP 定位协议由本工程定义，需要另外部署模型适配服务；它不是 VideoJev 官方 HTTP API。仅填模型名称不会自动加载权重。

## 评测与溯源

- 匹配同时检查机位、事件类别、ROI，并一对一分配；确证优先，重复告警单列。
- deadline_recall 的分母为全部真事件，漏检也计入；未标注、无正例或无有效时长的未定义指标为 null。
- holdout 的事件、帧级 AUC、有效时长、候选量和调用量只用测试段；审计拒识率单独标为开发段。
- 标定与输入内容、模型配置、场景和划分绑定；模型或输入变化不能沿用旧标定。冻结清单含实际加载的规则和标定。
- VLM 接收真实图像，保留模型事实、结论和不确定性；服务失败、虚构帧引用、模型与规则冲突均转人工。
- run_meta.json 保存有效配置、规则快照、输入文件摘要、环境版本和运行 ID；告警 ID 不同运行之间不重复。
- 合成时延、处理耗时、资源估算分开记录。没有浏览器显示回执，因此不宣称实测端到端显示时延。GPU 未测，费用与人工负担是估算。
- 演示许可不能用于真实回放；授权记录缺失或不完整时不确认“未授权”违规。

## 文档

- [项目明细与待完成事项](项目明细.md)

- [修改清单与交付边界](修改清单.md)
- [复现指南](docs/复现指南.md)
- [模型与数据适配](docs/适配指南.md)
- [与汇报稿要求的对应](docs/工程方向对齐说明.md)
- [功能说明](功能说明.md)

包内不附旧 runs/state；每次复现自行生成。保留源码、配置、数据/权重摘要和运行产物，才能比较实验。真实检测质量、VideoJev/Qwen 推理质量、GPU/显存/吞吐和现场实时告警仍需以后用真实资源验收。
