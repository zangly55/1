# Kubernetes 与 VMware ESXi 取证入门

- 核对日期：2026-11-23。来源为 Kubernetes 项目文档和 VMware by Broadcom 知识库。
- 适用范围：Kubernetes 控制面与 Linux 节点、VMware ESXi 主机及可选的 vCenter。受管集群和不同版本的日志入口、策略、路径及保留期以实际环境为准。
- 核验状态：官方文档核对。下文场景为示例，未连接环境或复验检材。

Kubernetes 管理 Pod 和容器的部署与调度。ESXi 在物理主机上运行虚拟机。两者可以叠在一起，例如一个 Kubernetes Worker Node 本身就是 ESXi 上的虚拟机。参见 [Kubernetes 概述](https://kubernetes.io/docs/concepts/overview/) 和 [VMware 虚拟化架构](https://www.vmware.com/topics/hypervisor)。

## Kubernetes：API 请求、节点执行和存储状态

| 要回答的问题 | 首选证据 | 核对要点 |
| --- | --- | --- |
| 哪个账号创建或修改了工作负载？ | `kube-apiserver` 审计，或受管平台提供的控制面审计 | 按 `auditID` 串联同一请求的各阶段，核对 `user`、`impersonatedUser`（如有）、`verb`、`objectRef` 或 `requestURI` 与 `responseStatus`。先确认审计策略、后端和覆盖时段。 |
| 容器实际在哪运行、为何退出？ | Pod 对象、节点的 kubelet / 容器运行时日志、容器及集中日志 | 留存 `namespace`、Pod UID、`spec.nodeName`、容器 ID、镜像 ID 及终止时间和退出原因。同名 Pod 在重建后可能对应不同 UID，应按事发时对象核对。 |
| 当时有哪些对象或业务数据？ | 已有 etcd 快照、资源导出、独立的 PV 或存储系统快照 | etcd 快照用于核对采集时点的集群对象，可能含敏感数据。业务数据要跟随 PVC → PV → 后端存储定位。 |

审计的 `RequestReceived` 表明 API 已收到请求。要判断资源变更是否成功，应结合后续审计阶段、响应状态和对象变化。审计中的服务账号代表请求身份，归因到个人需另查身份平台、CI/CD 或访问代理。`sourceIPs` 可能包括客户端提供的转发头，宜与可信链路记录核对。`pods/exec` 审计可定位 API 请求，交互会话内的逐条命令还需会话审计或宿主侧记录。参见 [Kubernetes 审计](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/) 和 [审计字段](https://kubernetes.io/docs/reference/config-api/apiserver-audit.v1/)。

Linux 节点通常从 `/var/log/pods` 查容器标准输出和错误输出，systemd 环境从 journal 查 kubelet 和运行时。`kubectl logs` 只提供相应实例最新的一份轮转日志。`--previous` 可读仍保留的上一次容器实例日志。`Events` 的保留有限，主要用于补充调度和状态变化。证据保全优先覆盖集中审计、节点与应用日志、轮转文件和事发时资源标识。参见 [日志架构](https://kubernetes.io/docs/concepts/cluster-administration/logging/)、[Events](https://kubernetes.io/docs/reference/kubernetes-api/events/) 和 [etcd 快照](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/#backing-up-an-etcd-cluster)。

### kubectl 的安装与取证查询

Windows 可用 `winget install -e --id Kubernetes.kubectl` 安装，或从官网按架构下载 `kubectl.exe`。将文件所在目录加入 `PATH`，或在该目录用 PowerShell 运行 `.\kubectl.exe version --client`。版本核对时，客户端与目标 API Server 应在一个 Kubernetes 次版本的差距内。参见 [Windows 安装](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) 和 [版本兼容策略](https://kubernetes.io/releases/version-skew-policy/#kubectl)。

`kubectl` 按 kubeconfig 选定的集群与身份向 Kubernetes API Server 发请求，查询取决于 API 可达性和权限。`kubectl get nodes` 查看节点清单，`kubectl get pods -A -o wide` 查看 Pod 与节点的对应，`kubectl get pv` 查看持久卷，`kubectl logs` 查看指定容器的可用日志。只有 E01 磁盘镜像时，从镜像副本检查配置、日志及运行时文件。若已授权重建，则在隔离的仿真环境中采集查询输出，并记录仿真状态和命令。参见 [kubectl 命令参考](https://kubernetes.io/docs/reference/kubectl/)。

## ESXi：主机、vCenter、虚拟机与来宾系统

| 要回答的问题 | 首选证据 | 核对要点 |
| --- | --- | --- |
| 有人经 SSH 或控制台操作了 ESXi？ | 主机 `auth.log`、`shell.log` | 按同一台主机、时间窗和 Shell 会话的 World ID 关联认证与输入命令，再查管理或系统日志核对操作结果。 |
| 哪个账号或任务重置、关机或迁移了虚拟机？ | vCenter Tasks & Events、`vpxd.log`、ESXi `hostd.log`、目标 VM 的 `vmware.log` | 核对目标 VM 标识、任务发起者、结果和日志中的状态转换。若虚拟机迁移过，定位事发时的 ESXi 主机。独立 ESXi 从本机记录入手。 |
| 主机或底层存储是否异常？ | `vmkernel.log`、`vobd.log`、`vmksummary.log`、远程 syslog | 区分主机启动、VM 电源事件和来宾系统重启，查看存储或网络告警是否同期影响多台 VM。 |
| 虚拟磁盘里有什么？ | `.vmx`、VMDK 描述文件及数据文件，存在快照时加 `.vmsd` 和相关增量文件 | 以常见 VMFS 盘为例，从 `.vmx` 引用的磁盘定位对应链，按 `parentFileNameHint`、`CID` / `parentCID` 核对父子关系与对应数据文件，结合 `vmware.log` 佐证。只读分析副本。 |

主机日志常从 `/var/run/log` 查找，并核对持久化及远程转发配置。若有 `vSphere Client → Export System Logs` 权限，可按范围导出 ESXi 诊断包并选择纳入 vCenter 日志。检查包内实际覆盖的文件和时间段。RAMDisk 上的日志可能随重启丢失。来宾系统内部动作通常还要从虚拟磁盘副本或来宾日志查证。参见 [ESXi 日志](https://knowledge.broadcom.com/external/article/306962)、[Shell 关联](https://knowledge.broadcom.com/external/article/321910)、[vCenter 日志](https://knowledge.broadcom.com/external/article/312194)、[诊断包](https://knowledge.broadcom.com/external/article/326299)、[日志持久化](https://knowledge.broadcom.com/external/article/317690)、[快照结构](https://knowledge.broadcom.com/external/article?legacyId=1015180) 和 [VMDK 字段](https://knowledge.broadcom.com/external/article/327862)。

## 跨层示例：多个 Pod 同时掉线

1. 从监控、Pod UID、节点记录和控制面审计确定事发时 Pod 所在节点，并核对是否发生发布、删除、容器退出或节点心跳中断。
2. 用事发时的资产清单将 Node 关联到具体 VM。有 `spec.providerID` 时验证其映射，再用 VM UUID、主机名等旁证交叉核对。当时的 IP 和名称可辅助定位。
3. 比对 VM 的 `vmware.log` 及轮转文件、来宾系统启动记录、vCenter 任务和当时所在 ESXi 主机的日志。可能出现的证据链包括：发布变更后旧 Pod 退出，VM 运行连续；vCenter 有目标 VM 重置任务且 VM 与来宾日志吻合，随后节点心跳中断；来宾系统自行重启，vCenter 无相符任务但 VM 与来宾日志有直接线索。
4. 统一比较时区，保留原始时间戳并记录可能的时钟偏差。节点变为不可达说明控制面失去连通或心跳，原因仍需查节点、网络和虚拟化证据。

参见 [Node 字段](https://kubernetes.io/docs/reference/kubernetes-api/core/node-v1/)、[节点心跳](https://kubernetes.io/docs/concepts/architecture/nodes/#node-heartbeats) 和 [VM 电源变化归因](https://knowledge.broadcom.com/external/article/339691)。ESXi 系统盘镜像中的安装时间另见 [既有安装时间专题](esxi-install-time.md)，其中原始字段的时区歧义仍待复核。
