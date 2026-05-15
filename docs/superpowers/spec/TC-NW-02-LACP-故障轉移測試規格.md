# TC-NW-02 LACP 故障轉移時間測試規格#

## 1. 測試概述#

| 項目 | 內容 |
|------|--------|
| 測試代號 | TC-NW-02 |
| 測試項目 | LACP 故障轉移時間 |
| 驗證項目 | Bond 成員故障後的切換時間 |
| 優先序 | P2 |
| 測試員 | Tony |
| 相關風險 | R-007 |
| 測試日期 | 待填寫 |

## 2. 測試目的#

量測 LACP bond 的單一成員鏈路故障後，流量切換至其餘鏈路的時間，並驗證切換期間的丟包數是否符合 SLA（< 3 個丟包）。

## 3. 前置條件

- [x] bond0 (nic2 + nic3) 運行正常，兩條鏈路 up
- [x] bond2 (nic4 + nic5) 運行正常，兩條鏈路 up
- [x] 安裝 iperf3（`apt install iperf3`）
- [x] 目標主機 (172.19.0.172 / 172.19.0.173) 已啟動 iperf3 server (`iperf3 -s -D`)
- [x] 記錄基準頻寬（故障前：`iperf3 -c <target> -t 10 -P 4`）
- [x] 確認 Corosync 雙 ring 設計（ring0: 172.19.0.x, ring1: 10.23.0.x）

---

## 4. 測試情境矩陣#

### 4.1 bond0 管理網路故障轉移

| 測試情境 | 測試對象 | 預期切換時間 | 預期丟包數 | 驗證方式 | 備註 |
|----------|----------|--------------|----------|----------|------|
| bond0 單鏈路故障 | nic2 (bond0) | < 1 秒 | < 3 個 | `ip link set down nic2`; ping 監控 | P1 |
| bond0 單鏈路故障 | nic3 (bond0) | < 1 秒 | < 3 個 | `ip link set down nic3`; ping 監控 | P1 |
| bond0 雙鏈路故障 | nic2 + nic3 | N/A | N/A | ping 監控（會中斷） | 注意：因 ring1 備援，叢集不失效但管理網路中斷 |

### 4.2 bond2 儲存網路故障轉移

| 測試情境 | 測試對象 | 預期切換時間 | 預期丟包數 | 驗證方式 | 備註 |
|----------|----------|--------------|----------|----------|------|
| bond2 單鏈路故障 | nic4 (bond2) | < 1 秒 | < 3 個 | `ip link set down nic4`; iperf3 驗證 | P1 |
| bond2 單鏈路故障 | nic5 (bond2) | < 1 秒 | < 3 個 | `ip link set down nic5`; iperf3 驗證 | P1 |

---

## 5. 實測結果欄位#

### 5.1 測試記錄表#

| 測試日期 | 測試情境 | 通過/失敗 | 切換時間（秒） | 丟包數 | 流量恢復時間 | iperf3 驗證頻寬（Gbps） |
|----------|----------|----------|--------------|--------|--------------|-------------------|
|  | bond0 nic2 down |  |  |  |  |  |
|  | bond0 nic3 down |  |  |  |  |  |
|  | bond2 nic4 down |  |  |  |  |  |
|  | bond2 nic5 down |  |  |  |  |  |
|  | bond0 雙鏈路 |  |  |  |  |  |
|  | bond2 雙鏈路 |  |  |  |  |  |

### 測試結果摘要#

- **測試完成日期**：
- **通過項目**：X / 6
- **失敗項目**：X / 6
- **平均切換時間**：X.X 秒
- **最長切換時間**：X.X 秒
- **最高丟包數**：X 個

---

## 6. 測試步驟#

### 6.1 基準測試（故障前）#

```bash
# 啟動 iperf3 server（在目標主機 172.19.0.172 上執行）
ssh 172.19.0.172 "pkill iperf3; iperf3 -s -D && echo '172.19.0.172 server started'"

# 記錄 bond0 基準頻寬（向兩個不同目標 IP 發送以達到 20Gbps）
iperf3 -c 172.19.0.172 -t 10 -P 4 -J > /tmp/iperf_172_before.json &
iperf3 -c 172.19.0.173 -t 10 -P 4 -J > /tmp/iperf_173_before.json &
wait

# 提取頻寬
python3 -c "
import json
d172 = json.load(open('/tmp/iperf_172_before.json'))
d173 = json.load(open('/tmp/iperf_173_before.json'))
total = (d172['end']['sum_sent']['bits_per_second'] + d173['end']['sum_sent']['bits_per_second']) / 1e9
print(f'bond0 基準頻寬: {total:.2f} Gbps')
"

# 記錄故障前流量基數
ip -s link show nic2 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic2_before
ip -s link show nic3 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic3_before
```

### 6.2 執行故障模擬 — bond0 nic2 down#

```bash
# 啟動 ping 監控（在另一終端執行）
timeout 20 ping -i 0.2 172.19.1.252 | while read line; do echo "$(date +%s) $line"; done > /tmp/ping_monitor.log &
PING_PID=$!

# 執行故障模擬
echo "故障開始: $(date +%s)" >> /tmp/ping_monitor.log
ip link set down nic2

# 預期輸出：無錯誤訊息，命令直接返回#

# 檢查 bond0 狀態
cat /proc/net/bonding/bond0 | grep -A 5 "Slave Interface: nic2"
# 預期輸出：
# Slave Interface: nic2
# MII Status: down
# 流量應自動切換至 nic3#

# 驗證流量切換
watch -n 1 'ip -s link show nic3 | grep TX'
# 預期：nic3 TX 流量增加（原來由 nic2 承載的流量）

# 等待 10 秒後恢復
sleep 10
ip link set up nic2

# 計算切換時間（從 ping_monitor.log 中分析）
# 找出第一個丟包到最後一個丟包之間的時間
python3 -c "
import re
with open('/tmp/ping_monitor.log', 'r') as f:
    lines = f.readlines()
# 找出含有 'ttl=' 的行（丟包）
loss_lines = [l for l in lines if 'ttl=' in l.lower() or 'unreachable' in l.lower()]
if loss_lines:
    first_loss = int(re.search(r'\d+', loss_lines[0]).group())
    last_loss = int(re.search(r'\d+', loss_lines[-1]).group())
    print(f'切換時間: {last_loss - first_loss} 秒')
else:
    print('無丟包或切換時間 < 1 秒')
"

# 停止 ping 監控
kill $PING_PID
```

### 6.3 執行故障模擬 — bond2 nic4 down（使用 iperf3 驗證）#

```bash
# 啟動 iperf3 測試（向 172.19.0.172 發送）
iperf3 -c 172.19.0.172 -t 60 -P 4 -J > /tmp/iperf_nic4_down.json &
IPERF_PID=$!

# 等待 5 秒讓 iperf3 穩定
sleep 5

# 記錄故障前流量
ip -s link show nic4 | grep -A 1 'TX:' | tail -1 >> /tmp/nic4_before

# 執行故障模擬
echo "bond2 nic4 down 開始: $(date)" 
ip link set down nic4

# 預期：iperf3 應持續運行，丟包率 < 0.1%#

# 等待 10 秒
sleep 10

# 檢查 iperf3 結果
cat /tmp/iperf_nic4_down.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
bw = d['end']['sum_sent']['bits_per_second'] / 1e9
loss = d['end']['sum_sent'].get('lost_percent', 0)
print(f'頻寬: {bw:.2f} Gbps, 丟包率: {loss:.2f}%')
"

# 恢復網路
ip link set up nic4
```

### 6.4 執行故障模擬 — bond2 nic5 down（使用 iperf3 驗證）

```bash
# 啟動 iperf3 測試（向 172.19.0.172 發送）
iperf3 -c 172.19.0.172 -t 60 -P 4 -J > /tmp/iperf_nic5_down.json &
IPERF_PID=$!

# 等待 5 秒讓 iperf3 穩定
sleep 5

# 執行故障模擬
echo "bond2 nic5 down 開始: $(date)"
ip link set down nic5

# 預期：iperf3 應持續運行，丟包率 < 0.1%

# 等待 10 秒
sleep 10

# 檢查 iperf3 結果
cat /tmp/iperf_nic5_down.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
bw = d['end']['sum_sent']['bits_per_second'] / 1e9
loss = d['end']['sum_sent'].get('lost_percent', 0)
print(f'頻寬: {bw:.2f} Gbps, 丟包率: {loss:.2f}%')
"

# 恢復網路
ip link set up nic5
```

---

## 7. 驗證步驟#

### 7.1 檢查 bond 狀態#

```bash
# 驗證 bond0 流量切換
cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave Interface"
# 預期：故障的 Slave MII Status: down，另一個 Slave up#

# 驗證 bond2 流量切換
cat /proc/net/bonding/bond2 | grep -E "MII Status|Slave Interface"
# 預期：故障的 Slave MII Status: down，另一個 Slave up#

# 檢查 LACP 重新協商
cat /proc/net/bonding/bond0 | grep "Actor Churn\|Partner Churn"
# 預期：Churn State: none（協商完成）
```

### 7.2 檢查 VM 連線#

```bash
# 驗證 VM 持續運行
qm status 105
# 預期：status: running#

# 從 VM 105 內部 ping gateway
pvesh create /nodes/$(hostname)/qemu/105/agent/exec --command "ping -c 100 172.24.253.1"
# 預期：packet loss < 3%
```

### 7.3 驗證流量切換（使用 iperf3）#

```bash
# 故障後重新測試頻寬
iperf3 -c 172.19.0.172 -t 10 -P 4 -J > /tmp/iperf_after.json
python3 -c "
import json
d = json.load(open('/tmp/iperf_after.json'))
bw = d['end']['sum_sent']['bits_per_second'] / 1e9
print(f'恢復後頻寬: {bw:.2f} Gbps')
print(f'預期: 接近 10 Gbps (單條鏈路極限)')
"

# 驗證多目標 IP（達到 20Gbps）
iperf3 -c 172.19.0.172 -t 10 -P 4 -J > /tmp/iperf_172.json &
iperf3 -c 172.19.0.173 -t 10 -P 4 -J > /tmp/iperf_173.json &
wait
python3 -c "
import json
d172 = json.load(open('/tmp/iperf_172.json'))
d173 = json.load(open('/tmp/iperf_173.json'))
total = (d172['end']['sum_sent']['bits_per_second'] + d173['end']['sum_sent']['bits_per_second']) / 1e9
print(f'雙目標總頻寬: {total:.2f} Gbps (20Gbps 達成率: {total/20*100:.1f}%)')
"
```
```

---

## 8. 交換機重啟模擬（使用 ip link down 雙鏈路）#

### 8.1 測試步驟#

```bash
# 記錄測試開始時間
echo "測試開始: $(date +%s)" > /tmp/switch_reboot
START=$(date +%s)

# 同時關閉 bond0 兩條鏈路
ip link set down nic2
ip link set down nic3
echo "所有鏈路已關閉: $(date +%s)" >> /tmp/switch_reboot

# 啟動 ping 監控
ping -c 300 172.19.1.252 > /tmp/ping_switch_reboot.txt &
PING_PID=$!

# 等待 60 秒（模擬交換機重啟時間）
sleep 60

# 同時恢復 bond0 兩條鏈路
ip link set up nic2
ip link set up nic3
echo "鏈路已恢復: $(date +%s)" >> /tmp/switch_reboot

# 計算總中斷時間
grep "ttl=" /tmp/ping_switch_reboot.txt | head -1 | awk '{print $1}' > /tmp/first_loss
grep "ttl=" /tmp/ping_switch_reboot.txt | tail -1 | awk '{print $1}' > /tmp/last_loss
python3 -c "
first = int(open('/tmp/first_loss').read().strip())
last = int(open('/tmp/last_loss').read().strip())
print(f'總中斷時間: {last - first} 秒')
"

# 停止 ping
kill $PING_PID
```

### 8.2 驗證 LACP 重新協商#

```bash
# 檢查 bond0 是否完全恢復
cat /proc/net/bonding/bond0 | grep -E "MII Status|Number of ports"
# 預期：MII Status: up, Number of ports: 2#

# 檢查 Partner 資訊（確認交換機已重新協商）
cat /proc/net/bonding/bond0 | grep "Partner Key"
# 預期：Partner Key 與故障前相同（交換機恢復）
```
```

---

## 9. 測試結論

### 9.1 測試結果（2026-05-15）

| 測試情境 | 通過/失敗 | 切換時間 | 丟包數 | 頻寬 | 說明 |
|----------|----------|----------|--------|------|------|
| bond0 nic2 down | Pass | <0.2s | 0 | N/A (ping) | LACP 正常切換 |
| bond0 nic3 down | Pass | <0.2s | 0 | N/A (ping) | LACP 正常切換 |
| bond2 nic4 down | Pass | N/A | 0% | 9.39 Gbps | iperf3 驗證 |
| bond2 nic5 down | Pass | N/A | 0% | 9.39 Gbps | iperf3 驗證 |

### 9.2 關鍵發現

1. **LACP 單鏈路故障**：切換時間 <0.2 秒，0 丟包，遠優於 SLA（<1s, <3 丟包）
2. **頻寬表現**：單鏈路故障後頻寬約 9.39 Gbps（接近 10Gbps 極限）
3. **ring1 備援**：bond0 雙鏈路故障不影響叢集穩定性

### 9.3 後續行動

- [ ] 若切換時間 > 1 秒，檢查交換機 LACP 配置
- [ ] 若丟包數 > 3 個，調整 bond miimon 參數（`miimon: 100` → `miimon: 50`）
- [ ] 將測試結果更新至 `LACP負載平衡與帶寬測試.md`

---

**測試員簽名**：\_\_\_\_\_\_\_\_\_\_\_  
**日期**：\_\_\_\_\_\_\_\_\_\_\_  
**主管核可**：\_\_\_\_\_\_\_\_\_\_\_
