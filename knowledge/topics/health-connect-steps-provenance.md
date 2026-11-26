# 手机与手表的步数为何对不上

适用于已授权取得的 Android Health Connect 步数明细、平台聚合结果或其导出。手机与手表在同一时间都记了步数时，先确定题目问的是某个来源记录了多少，还是平台当日显示了多少。两者需要不同证据。

| 要回答的问题 | 核对位置和操作 | 可支持的结论 |
| --- | --- | --- |
| 步数覆盖哪一段时间？ | 在对应的 `StepsRecord` 找 `count`、`startTime`、`endTime` 和起止时区偏移。保留原值，统一到同一时区后对齐区间。另列 `metadata.lastModifiedTime`。 | 步数属于一个区间。最后修改时间可反映创建或更新。仅凭这个字段无法定位人迈步的时刻。跨午夜的记录应单列，缺少更细粒度数据时，按分钟均摊会引入估计。 |
| 手表测得、人工填写，还是应用导入？ | 对照 `metadata.dataOrigin`、`device`、`recordingMethod` 和配套 App 的同时间段记录。区分自动采集、主动启动活动、手工输入与未知。 | 来源信息有助于定位写入链。设备类别和记录方式由客户端提供，单凭“手表”标签无法确认具体佩戴者或传感器实测。 |
| 为什么逐行求和比平台高？ | 保留各来源明细，标出相交区间。另记平台聚合指标 `StepsRecord.COUNT_TOTAL` 的起止范围、时区、来源筛选、用户应用优先级及取得时间。 | 对活动类数据，Health Connect 聚合会按用户设置的来源优先级处理重复数据。不能把多个 App 的原始步数直接相加当作平台值，也不能仅凭两段时间重叠就删掉整行。 |

如果只有平台截图，可以记录画面显示的数值、日期与界面来源。若要解释数值差额，还需同一范围的来源明细与优先级。若只有明细，保留分来源结果和重叠范围，将历史界面总数列为待复核。优先级可变，今天读取的设置不能独自证明过去的显示结果。

**适用范围与验证。** 依据 AndroidX Health Connect 客户端记录与聚合接口说明。具体设备型号、固件、系统及客户端安装版本未知。文档中的对象字段需要先与实际导出结构对应。本次为官方文档核对，无个人健康数据、设备采集、API 实测或原始检材复验。

**来源。** Google / Android Developers，检索于 2026-11-26。

- 步数写入示例、来源设备与记录方式、时间偏移。页面更新于 2026-10-21。[Write data](https://developer.android.com/health-and-fitness/health-connect/write-data)
- 步数聚合与用户设置的应用优先级。首次发布日期未知。[Read aggregated data](https://developer.android.com/health-and-fitness/health-connect/aggregate-data)
- 记录来源、记录标识、最后修改时间及记录方式。页面更新于 2026-10-26。[Metadata](https://developer.android.com/reference/androidx/health/connect/client/records/metadata/Metadata)
