# 2025 数证杯 K8s 与龙信杯 ESXi 取证 WP 选读

2026-11-23 核对两篇公开赛后题解的服务器章节。题解作者报告了竞赛检材的操作与结果，当前记录为阅读摘要，未取得原始检材独立复验。页面首次发布日期未核实。

## Kubernetes｜2025 第二届数证杯初赛

服务器章节署名 NoahTie。原文的「服务器重建」段展示了同一组检材的静态分析与赛后仿真思路。 [XD Forensics Wiki 原文](https://forensics.xidian.edu.cn/writeups/Shuzheng2025Preliminary/#_5)

- 检材入口为多份 E01。作者先查看网络配置，辨认控制面、两个工作节点及独立数据库服务器，再用仿真环境中的节点清单交叉核对。Q02 可用来练习区分工作节点数与全部服务器数。
- Q07–Q10 涉及容器镜像、容器 ID、缓存服务和代码目录。重建段示范从 Pod 定位实际运行节点并查容器日志，也从 PV 的 NFS 配置定位后端目录，在单独的服务器镜像上继续查证。
- 作者报告比赛时使用静态方法检查 Docker OverlayFS，赛后才以仿真补充。OverlayFS 路径及对象对应方式取决于本题使用的运行时、存储驱动和配置。PV 配置能定位声明的存储，判断目录是否存在或为何缺失仍需后端镜像或日志支持。

- `dujiaoka` 是“独角数卡”一类的数字商品自动售货系统。它面向卡密、兑换码或充值码等数字商品，通常包括商品、订单、卡密库存、支付和自动交付功能，不是实体银行卡发卡。该项目公开仓库将其标为“自动售货系统”，并使用 `faka` 等主题标签。[项目说明](https://github.com/assimon/dujiaoka)

- WP 中作者先看到的是持久卷名称 `dujiaoka`，随后用 `kubectl describe pv` 看到它的 NFS 来源为 `192.168.50.83:/data/k8s_data/default/dujiaoka`。这只能证明集群把一个持久存储资源命名为 `dujiaoka`，所以作者当时写“疑似”。更强的交叉证据来自控制节点上的 Nginx、PVC、Supervisor 等网站配置，以及 04 号镜像中的网站源码压缩包、`Dockerfile` 和 PHP-Nginx 镜像。数据库里出现 MySQL 或 Redis只能说明数据库角色，不能单独证明应用就是独角数卡。 [WP 原文](https://forensics.xidian.edu.cn/writeups/Shuzheng2025Preliminary/#_6)

- 复核时依次查看 PV/PVC 的名称和挂载源、Deployment/Service/Pod 的标签与镜像、源码或容器配置中的应用名称和路由、数据库连接与数据表，再把这些证据按同一命名空间和时间范围关联。仅凭目录名或镜像名不要直接下最终结论。

- 04 号 E01 的原文截图已核对。第一张展示火眼 `Linux 基本信息 → 系统信息` 中的主机信息，第二张在火眼左侧解析树列出 `Redis解析` 和 `MySQL解析`，下级路径在图中截断。该截图支持镜像中有可被火眼识别的数据库数据；确认 04 本机实际安装或运行对应服务，还需核对已安装包、服务配置或运行日志。PV 的后端配置可辅助识别该机承担的存储角色。 [原文证据截图](https://forensics.xidian.edu.cn/assets/images/writeups/Shuzheng2025Preliminary/Pasted%20image%2020251104110015.png)

- 原文仿真截图显示 VMware Workstation 将 `VMnet8`（NAT）设为 `192.168.50.0/24`，接入了宿主机虚拟适配器，并启用了 VMware DHCP。若重建虚拟机接入同一 VMnet 并保留原来可用的固定地址，节点间通信及对 NFS 等后端的原地址引用可继续使用，减少重新配置。DHCP 是否实际分配该地址须查看来宾配置或租约。NAT 提供出网能力，虚拟机在同一 VMnet 子网内互访通常直接进行。取证仿真应在授权的网络隔离范围内重建通信并记录改动。 [WP 服务器重建](https://forensics.xidian.edu.cn/writeups/Shuzheng2025Preliminary/#_6) · [VMware 网络模式](https://knowledge.broadcom.com/external/article?articleNumber=309842)

## VMware ESXi｜2025 第三届龙信杯

服务器章节作者 NoahTie。原文展示用火眼解析 ESXi 检材的 VMFS，再导出两台虚拟机文件，将 VMDK 加作新检材后分析。 [XD Forensics Wiki 原文](https://forensics.xidian.edu.cn/writeups/Longxin2025/#vmware-esxi)

- Q01–Q03 适合作为入门顺序。安装时间来自 ESXi 平台的解析结果，ISO 文件来自虚拟机数据存储中的目录，Samba 版本线索来自 NAS 虚拟磁盘内的包管理缓存。三题分别落在宿主平台、数据存储和来宾系统。
- Q01 原文展示了火眼的时区标注。已有案件记录发现，原始安装字段未带时区，转换口径仍待复核。Q02 应回到原始字节数并确认 GB/GiB 与舍入规则。Q03 要确证事发时实际安装的版本，可将包缓存与目标系统的包数据库、安装记录交叉核对。
- 相关案件与安装时间边界见[既有 ESXi 取证记录](20261021162519O-esxi-server.md)及[安装时间专题](../topics/esxi-install-time.md)。本文补充公开参考来源。

两份材料的证据路径分别为「镜像 → 节点 → Pod / 容器 / 持久卷」和「镜像 → VMFS → VMDK → 来宾系统」。参见 [Kubernetes 与 VMware ESXi 取证入门](../topics/kubernetes-esxi-forensics.md)。
