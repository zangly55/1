# 2025 数证杯 K8s 与龙信杯 ESXi 取证 WP 选读

2026-11-23 核对两篇公开赛后题解的服务器章节。题解作者报告了竞赛检材的操作与结果，当前记录为阅读摘要，未取得原始检材独立复验。页面首次发布日期未核实。

## Kubernetes｜2025 第二届数证杯初赛

服务器章节署名 NoahTie。原文的「服务器重建」段展示了同一组检材的静态分析与赛后仿真思路。 [XD Forensics Wiki 原文](https://forensics.xidian.edu.cn/writeups/Shuzheng2025Preliminary/#_5)

- 检材入口为多份 E01。作者先查看网络配置，辨认控制面、两个工作节点及独立数据库服务器，再用仿真环境中的节点清单交叉核对。Q02 可用来练习区分工作节点数与全部服务器数。
- Q07–Q10 涉及容器镜像、容器 ID、缓存服务和代码目录。重建段示范从 Pod 定位实际运行节点并查容器日志，也从 PV 的 NFS 配置定位后端目录，在单独的服务器镜像上继续查证。
- 作者报告比赛时使用静态方法检查 Docker OverlayFS，赛后才以仿真补充。OverlayFS 路径及对象对应方式取决于本题使用的运行时、存储驱动和配置。PV 配置能定位声明的存储，判断目录是否存在或为何缺失仍需后端镜像或日志支持。

## VMware ESXi｜2025 第三届龙信杯

服务器章节作者 NoahTie。原文展示用火眼解析 ESXi 检材的 VMFS，再导出两台虚拟机文件，将 VMDK 加作新检材后分析。 [XD Forensics Wiki 原文](https://forensics.xidian.edu.cn/writeups/Longxin2025/#vmware-esxi)

- Q01–Q03 适合作为入门顺序。安装时间来自 ESXi 平台的解析结果，ISO 文件来自虚拟机数据存储中的目录，Samba 版本线索来自 NAS 虚拟磁盘内的包管理缓存。三题分别落在宿主平台、数据存储和来宾系统。
- Q01 原文展示了火眼的时区标注。已有案件记录发现，原始安装字段未带时区，转换口径仍待复核。Q02 应回到原始字节数并确认 GB/GiB 与舍入规则。Q03 要确证事发时实际安装的版本，可将包缓存与目标系统的包数据库、安装记录交叉核对。
- 相关案件与安装时间边界见[既有 ESXi 取证记录](20261021162519O-esxi-server.md)及[安装时间专题](../topics/esxi-install-time.md)。本文补充公开参考来源。

两份材料的证据路径分别为「镜像 → 节点 → Pod / 容器 / 持久卷」和「镜像 → VMFS → VMDK → 来宾系统」。参见 [Kubernetes 与 VMware ESXi 取证入门](../topics/kubernetes-esxi-forensics.md)。
