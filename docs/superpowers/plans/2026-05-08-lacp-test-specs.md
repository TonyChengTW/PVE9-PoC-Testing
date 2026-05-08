# LACP 斷線測試規格文件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立兩份獨立的 LACP 斷線測試規格文件，並更新現有文檔中的 LACP 故障轉移測試矩陣。

**Architecture:** 方案 B — 拆分為兩個獨立文件：
- `test-specs/TC-HA-02-LACP-HA測試規格.md` — TC-HA-02 LACP 單鏈路故障 HA 觸發（P1 高風險）
- `test-specs/TC-NW-02-LACP-故障轉移測試規格.md` — TC-NW-02 LACP 故障轉移時間（P2）
- 更新 `環境說明_Environment_Setup.md` 的 LACP 故障轉移測試矩陣
- 更新 `AGENTS.md` 引用新文件

**Tech Stack:** Markdown, Bash/CLI, Proxmox VE (pvecm, ha-manager, corosync-cmapctl, ip link, iptables)

---

## File Structure

| 文件 | 操作 | 說明 |
|------|------|------|
| `test-specs/TC-HA-02-LACP-HA測試規格.md` | 建立 | TC-HA-02 完整測試規格 |
| `test-specs/TC-NW-02-LACP-故障轉移測試規格.md` | 建立 | TC-NW-02 完整測試規格 |
| `環境說明_Environment_Setup.md` | 修改 | 擴充 LACP 故障轉移測試矩陣（第 96-104 行） |
| `AGENTS.md` | 修改 | 更新測試報告產出清單與文件索引 |

---

### Task 1: 建立 TC-HA-02-LACP-HA測試規格.md

**Files:**
- Create: `test-specs/TC-HA-02-LACP-HA測試規格.md`

- [ ] **Step 1: 撰寫測試概述**

```markdown
# TC-HA-02 LACP 單鏈路故障 HA 觸發測試規格

## 1. 測試概述

| 項目 | 內容 |
|------|--------|
| 測試代號 | TC-HA-02 |
| 測試項目 | LACP 單鏈路故障 HA 觸發 |
| 驗證項目 | 非聚合網路斷線觸發 HA 非預期切換 |
| 優先序 | **P1（高風險）** |
| 測試員 | Tony |
| 相關風險 | R-007, R-010 |
| 測試日期 | 待填寫 |

## 2. 測試目的

驗證當 LACP bond 的單一成員鏈路斷線時，Corosync 是否會因網路延遲或感知變化而觸發非預期的 HA 切換。這是 PVE 已知敏感問題，需優先測試。

## 3. 前置條件

- [ ] 三節點叢集運行正常（pvecm status 顯示 Quorate: Yes）
- [ ] HA 機制已啟用（ha-manager status 無錯誤）
- [ ] 至少一台 VM 已設定 HA 管理（ha-manager add vm:100）
- [ ] 記錄當前 Corosync 參數（corosync-cmapctl | grep -E 'deadtime|token'）
- [ ] 準備 NetApp FAS2650 快照或 VM 快照（高風險測試）
- [ ] 確認 iDRAC/IPMI 可連線（fence 機制測試備用）
```

- [ ] **Step 2: 撰寫測試情境矩陣（擴充：bond0 + bond2）**

```markdown
## 4. 測試情境矩陣

### 4.1 測試情境（bond0 管理網路）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 |
|----------|----------|----------|----------|--------|
| bond0 單鏈路故障 | nic2 (bond0) | 不應觸發 HA | `ip link set down nic2` | P1 |
| bond0 單鏈路故障 | nic3 (bond0) | 不應觸發 HA | `ip link set down nic3` | P1 |
| bond0 雙鏈路故障 | nic2 + nic3 | 應觸發 HA 或進入唯讀模式 | `ip link set down nic2; ip link set down nic3` | P1 |
| Corosync 管理網路隔離 | bond0 (管理網路) | 需驗證 quorum 行為 | `iptables -A INPUT -s 172.19.0.172 -j DROP` | P1 |
| 管理網路中斷 | bond0 | VM 應持續運行 | SSH 連線中斷測試 | P2 |

### 4.2 測試情境（bond2 儲存網路）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 |
|----------|----------|----------|----------|--------|
| bond2 單鏈路故障 | nic4 (bond2) | 不應觸發 HA | `ip link set down nic4` | P1 |
| bond2 單鏈路故障 | nic5 (bond2) | 不應觸發 HA | `ip link set down nic5` | P1 |
| bond2 雙鏈路故障 | nic4 + nic5 | NFS 儲存中斷，VM 可能凍住 | `ip link set down nic4; ip link set down nic5` | P2 |
| NFS 儲存中斷 | bond2 | VM I/O 可能延遲或凍住 | 觀察 VM I/O 行為 | P2 |
```

- [ ] **Step 3: 撰寫實測結果欄位**

```markdown
## 5. 實測結果欄位

### 5.1 測試記錄表

| 測試日期 | 測試情境 | 通過/失敗 | 切換時間（秒） | 丟包數 | VM 狀態變化 | Corosync 日誌摘要 | HA 動作（是/否） |
|----------|----------|----------|--------------|--------|--------------|-------------------|----------------|
|  | bond0 nic2 down |  |  |  |  |  |  |
|  | bond0 nic3 down |  |  |  |  |  |  |
|  | bond0 雙鏈路 down |  |  |  |  |  |  |
|  | bond2 nic4 down |  |  |  |  |  |  |
|  | bond2 nic5 down |  |  |  |  |  |  |
|  | bond2 雙鏈路 down |  |  |  |  |  |  |
|  | Corosync 隔離 |  |  |  |  |  |  |

### 5.2 測試結果摘要

- **測試完成日期**：
- **通過項目**：X / 7
- **失敗項目**：X / 7
- **HA 非預期觸發次數**：X 次
- **最長切換時間**：X.X 秒
- **最高丟包數**：X 個
```

- [ ] **Step 4: 撰寫測試步驟（完整 CLI 指令 + 預期輸出）**

```markdown
## 6. 測試步驟

### 6.1 準備階段

```bash
# 檢查初始狀態
pvecm status
# 預期輸出：Quorate: Yes, Expected votes: 3, Total votes: 3

ha-manager status
# 預期輸出：active, master 或 standby

cat /proc/net/bonding/bond0
# 預期輸出：MII Status: up, 兩個 Slave Interface: up

cat /proc/net/bonding/bond2
# 預期輸出：MII Status: up, 兩個 Slave Interface: up

corosync-cmapctl | grep -E 'deadtime|token'
# 預期輸出：config.totem.deadtime (default 1000ms), config.totem.token (default 1000ms)

# 檢查 VM 狀態
qm status 100  # 假設 VMID 100 已設定 HA
# 預期輸出：status: running
```

### 6.2 執行測試 — bond0 單鏈路故障（nic2）

```bash
# 記錄測試前基數
ip -s link show nic2 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic2_before
ip -s link show nic3 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic3_before
ha-manager status > /tmp/ha_status_before

# 執行故障模擬
echo "=== 測試開始: $(date) ==="
ip link set down nic2

# 預期輸出：無錯誤訊息，命令直接返回

# 檢查 bond0 狀態
cat /proc/net/bonding/bond0 | grep -A 10 "Slave Interface: nic2"
# 預期輸出：
# Slave Interface: nic2
# MII Status: down
# Link Failure Count: X (增加 1)

# 檢查流量是否切換至 nic3
watch -n 1 'ip -s link show nic3 | grep TX'
# 預期：nic3 TX 流量增加

# 檢查 HA 狀態（等待 10 秒後檢查）
sleep 10
ha-manager status
# 預期：不應有 VM 被遷移或重啟，狀態應為 active 或 standby

# 檢查 Corosync 成員
corosync-cmapctl | grep members
# 預期：三個節點都仍在 members 中

# 檢查 VM 是否持續運行
qm status 100
# 預期：status: running

# 恢復網路
ip link set up nic2
cat /proc/net/bonding/bond0 | grep "MII Status"
# 預期：MII Status: up（兩個 Slave 都 up）
```

### 6.3 執行測試 — bond0 雙鏈路故障

```bash
# 模擬 bond0 完全斷線
ip link set down nic2
ip link set down nic3

# 預期行為：
# 1. Corosync 可能失去 quorum（兩條管理網路都斷）
# 2. HA 可能觸發 VM 遷移或重啟
# 3. 本機可能進入唯讀模式

# 檢查 quorum 狀態
pvecm status
# 可能的輸出：
# - Quorate: No（失去 quorum）
# - 或叢集分割

# 檢查 HA 動作
ha-manager status
# 可能的輸出：fence 機制觸發，VM 被標記為 fenced

# 恢復網路
ip link set up nic2
ip link set up nic3
pvecm status
# 預期：Quorate: Yes，三節點恢復
```

### 6.4 執行測試 — Corosync 管理網路隔離

```bash
# 使用 iptables 阻斷與另一節點的通訊（模擬網路分割）
# 測試隔離 sandbox-pve02 (172.19.0.172)
iptables -A INPUT -s 172.19.0.172 -j DROP

# 預期行為：
# 1. 等待 deadtime (預設 1 秒，若已調整為 10 秒則等待 10 秒）
# 2. 檢查 corosync 是否將 172.19.0.172 標記為離線

# 檢查成員狀態
corosync-cmapctl | grep members
# 預期：172.19.0.172 可能從 members 中消失

# 檢查 quorum
pvecm status
# 預期：Quorate 應仍為 Yes（因為剩餘 2 票 >= expected 2）

# 檢查 HA 是否觸發
ha-manager status
# 預期：不應有 VM 被遷移（因為 quorum 仍存在）

# 恢復網路
iptables -D INPUT -s 172.19.0.172 -j DROP
pvecm status
# 預期：恢復 Quorate，三節點重新加入
```
```

- [ ] **Step 5: 撰寫驗證步驟**

```markdown
## 7. 驗證步驟

### 7.1 檢查 bond 狀態

```bash
# 驗證 bond0 流量分散
watch -n 1 'ip -s link show nic2 | grep TX; ip -s link show nic3 | grep TX'
# 預期：恢復後兩條鏈路都有流量（若有多個連接）

# 驗證 bond0 狀態
cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave Interface|Link Failure"
# 預期：MII Status: up, 兩個 Slave Link Failure Count 不再增加
```

### 7.2 檢查 VM 連線

```bash
# 驗證 VM 持續運行
qm status 100
# 預期：status: running

# 從 VM 內部 ping gateway
ping -c 5 172.19.1.252
# 預期：0% packet loss

# 驗證 VM I/O 正常
# 在 VM 內執行簡單讀寫測試
dd if=/dev/zero of=/tmp/test bs=1M count=100
# 預期：完成無錯誤
```

### 7.3 檢查 Corosync 狀態

```bash
# 驗證 corosync 成員完整
corosync-cmapctl runtime.config.active | grep members
# 預期：三個節點都在 members 中

# 檢查 corosync 日誌（是否有錯誤）
journalctl -u corosync --since "5 min ago" | grep -i "error\|warn\|fail"
# 預期：無錯誤或僅有預期的 "link down" 訊息
```

### 7.4 檢查 HA 狀態

```bash
# 驗證 HA 未非預期觸發
ha-manager status
# 預期：active 或 standby，無 "fenced" 或 "restarting" 狀態

# 檢查 HA 日誌
journalctl -u pve-ha-lrm --since "5 min ago" | grep -i "error\|restart\|migrate"
# 預期：無非預期的 VM restart 或 migrate 紀錄
```
```

- [ ] **Step 6: 撰寫交換機重啟模擬**

```markdown
## 8. 交換機重啟模擬（使用 ip link down 雙鏈路）

### 8.1 測試情境

由於無 Switch 管理權限，使用 `ip link set down` 模擬交換機重啟（雙鏈路同時斷線）。

### 8.2 測試步驟

```bash
# 記錄測試開始時間
echo "測試開始: $(date +%s)" > /tmp/switch_reboot_test

# 同時關閉 bond0 兩條鏈路
ip link set down nic2
ip link set down nic3
echo "所有鏈路已關閉: $(date +%s)" >> /tmp/switch_reboot_test

# 等待 60 秒（模擬交換機重啟時間）
sleep 60
echo "等待完成: $(date +%s)" >> /tmp/switch_reboot_test

# 同時恢復 bond0 兩條鏈路
ip link set up nic2
ip link set up nic3
echo "鏈路已恢復: $(date +%s)" >> /tmp/switch_reboot_test

# 計算總中斷時間
# 另一終端持續 ping gateway，記錄首次丟包到最後一個丟包之間的時間
# ping -i 0.2 172.19.1.252 | grep "ttl="
```

### 8.3 驗證步驟

```bash
# 檢查 bond0 是否完全恢復
cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave"
# 預期：MII Status: up, 兩個 Slave MII Status: up

# 檢查 LACP 重新協商
cat /proc/net/bonding/bond0 | grep "Actor Churn\|Partner Churn"
# 預期：Churn State: none（協商完成）

# 檢查 VM 狀態
qm status 100
# 預期：status: running

# 檢查 Corosync
pvecm status
# 預期：Quorate: Yes
```
```

- [ ] **Step 7: 撰寫 HA 敏感度調整建議**

```markdown
## 9. HA 敏感度調整建議

### 9.1 若 HA 非預期觸發

```bash
# 檢查當前 corosync 參數
corosync-cmapctl | grep -E 'deadtime|token|retransmits'

# 若 deadtime 為預設 1 秒，建議調整為 10 秒
# 編輯 /etc/corosync/corosync.conf
vim /etc/corosync/corosync.conf
# 在 totem section 中加入：
# totem {
#     deadtime: 10      # 預設 1，建議提升
#     token: 5000       # 預設 1000ms，建議提升
#     token_retransmits_before_loss_const: 10  # 預設 4
# }

# 重啟 corosync（會短暫中斷，請在維護視窗執行）
systemctl restart corosync

# 驗證設定
corosync-cmapctl | grep -E 'deadtime|token'
# 預期：顯示新設定值
```

### 9.2 建議配置

| 參數 | 預設值 | 保守值 | 說明 |
|------|--------|--------|------|
| deadtime | 1s | 10s | 認定節點死亡前的等待時間 |
| token | 1000ms | 5000ms | 單一 token 循環時間 |
| token_retransmits_before_loss_const | 4 | 10 | 重傳次數後判定 loss |

### 9.3 將 Corosync 流量移至專用網段（長期建議）

```bash
# 在 /etc/corosync/corosync.conf 中增加 ring1 (10.23.0.0/24 儲存網路）
# nodelist {
#   node {
#     name: sd-sandbox-pve01
#     nodeid: 1
#     quorum_votes: 1
#     ring0_addr: 172.19.0.171
#     ring1_addr: 10.23.0.171
#   }
#   ... 其他節點
# }

# 重新載入配置
pvecm expected 3
systemctl restart corosync
```
```

- [ ] **Step 8: 撰寫結論與簽核**

```markdown
## 10. 測試結論

### 10.1 測試結果

- **通過項目**：X / 7
- **失敗項目**：X / 7（列出失敗項目與原因）
- **HA 非預期觸發次數**：X 次
- **最長切換時間**：X.X 秒
- **建議 Corosync 參數調整**：是 / 否

### 10.2 後續行動

- [ ] 若 HA 非預期觸發，執行 corosync 參數調整
- [ ] 若 bond0 雙鏈路故障導致 quorum 失去，評估增加 ring1 (儲存網路）
- [ ] 將測試結果更新至 `PVE風險評估矩陣_Risk_Assessment_Matrix.md`
- [ ] 將 SOP 更新至 `AGENTS.md` 與 `環境說明_Environment_Setup.md`

---

**測試員簽名**：\_\_\_\_\_\_\_\_\_\_\_  
**日期**：\_\_\_\_\_\_\_\_\_\_\_  
**主管核可**：\_\_\_\_\_\_\_\_\_\_\_
```

- [ ] **Step 9: 提交文件**

```bash
git add test-specs/TC-HA-02-LACP-HA測試規格.md
git commit -m "feat: add TC-HA-02 LACP HA test specification (P1)"
```

---

### Task 2: 建立 TC-NW-02-LACP-故障轉移測試規格.md

**Files:**
- Create: `test-specs/TC-NW-02-LACP-故障轉移測試規格.md`

- [ ] **Step 1: 撰寫測試概述**

```markdown
# TC-NW-02 LACP 故障轉移時間測試規格

## 1. 測試概述

| 項目 | 內容 |
|------|--------|
| 測試代號 | TC-NW-02 |
| 測試項目 | LACP 故障轉移時間 |
| 驗證項目 | Bond 成員故障後的切換時間 |
| 優先序 | P2 |
| 測試員 | Tony |
| 相關風險 | R-007 |
| 測試日期 | 待填寫 |

## 2. 測試目的

量測 LACP bond 的單一成員鏈路故障後，流量切換至其餘鏈路的時間，並驗證切換期間的丟包數是否符合 SLA（< 3 個丟包）。

## 3. 前置條件

- [ ] bond0 (nic2 + nic3) 運行正常，兩條鏈路 up
- [ ] bond2 (nic4 + nic5) 運行正常，兩條鏈路 up
- [ ] 安裝 iperf3（`apt install iperf3`）
- [ ] 目標主機 (172.19.0.172 / 172.19.0.173) 已啟動 iperf3 server (`iperf3 -s -D`)
- [ ] 記錄基準頻寬（故障前：`iperf3 -c <target> -t 10 -P 4`）
```

- [ ] **Step 2: 撰寫測試情境矩陣（bond0 + bond2）**

```markdown
## 4. 測試情境矩陣

### 4.1 bond0 管理網路故障轉移

| 測試情境 | 測試對象 | 預期切換時間 | 預期丟包數 | 驗證方式 |
|----------|----------|--------------|----------|----------|
| bond0 單鏈路故障 | nic2 (bond0) | < 1 秒 | < 3 個 | `ip link set down nic2`; ping 監控 |
| bond0 單鏈路故障 | nic3 (bond0) | < 1 秒 | < 3 個 | `ip link set down nic3`; ping 監控 |
| bond0 雙鏈路故障 | nic2 + nic3 | 需重建 LACP | 視交換機而定 | 模擬交換機重啟 |

### 4.2 bond2 儲存網路故障轉移

| 測試情境 | 測試對象 | 預期切換時間 | 預期丟包數 | 驗證方式 |
|----------|----------|--------------|----------|----------|
| bond2 單鏈路故障 | nic4 (bond2) | < 1 秒 | < 3 個 | `ip link set down nic4`; iperf3 驗證 |
| bond2 單鏈路故障 | nic5 (bond2) | < 1 秒 | < 3 個 | `ip link set down nic5`; iperf3 驗證 |
| bond2 雙鏈路故障 | nic4 + nic5 | 需重建 LACP | NFS I/O 可能凍住 | 模擬交換機重啟 |
```

- [ ] **Step 3: 撰寫實測結果欄位**

```markdown
## 5. 實測結果欄位

| 測試日期 | 測試情境 | 通過/失敗 | 切換時間（秒） | 丟包數 | 流量恢復時間 | iperf3 驗證頻寬（Gbps） |
|----------|----------|----------|--------------|--------|--------------|-------------------|
|  | bond0 nic2 down |  |  |  |  |  |
|  | bond0 nic3 down |  |  |  |  |  |
|  | bond2 nic4 down |  |  |  |  |  |
|  | bond2 nic5 down |  |  |  |  |  |
|  | bond0 雙鏈路 |  |  |  |  |  |
|  | bond2 雙鏈路 |  |  |  |  |  |

### 測試結果摘要

- **測試完成日期**：
- **通過項目**：X / 6
- **失敗項目**：X / 6
- **平均切換時間**：X.X 秒
- **最長切換時間**：X.X 秒
- **最高丟包數**：X 個
```

- [ ] **Step 4: 撰寫測試步驟（完整 CLI 指令 + 預期輸出）**

```markdown
## 6. 測試步驟

### 6.1 基準測試（故障前）

```bash
# 啟動 iperf3 server（在目標主機 172.19.0.172 上執行）
ssh 172.19.0.172 "pkill iperf3; iperf3 -s -D"

# 記錄 bond0 基準頻寬（向兩個不同目標 IP 發送以達到 20Gbps）
iperf3 -c 172.19.0.172 -t 10 -P 4 -J > /tmp/iperf_172_before.json &
iperf3 -c 172.19.0.173 -t 10 -P 4 -J > /tmp/iperf_173_before.json &
wait

# 提取頻寬
python3 -c "
import json
d172 = json.load(open('/tmp/iperf_172_before.json'))
d173 = json.load(open('/tmp/iperf_173_before.json'))
print(f'bond0 基準頻寬: {d172[\"end\"][\"sum_sent\"][\"bits_per_second\"]/1e9 + d173[\"end\"][\"sum_sent\"][\"bits_per_second\"]/1e9:.2f} Gbps')
"

# 記錄故障前流量基數
ip -s link show nic2 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic2_before
ip -s link show nic3 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic3_before
```

### 6.2 執行故障模擬 — bond0 nic2 down

```bash
# 啟動 ping 監控（在另一終端執行）
ping -i 0.2 172.19.1.252 | while read line; do echo "$(date +%s) $line"; done > /tmp/ping_monitor.log &
PING_PID=$!

# 執行故障模擬
echo "故障開始: $(date +%s)" >> /tmp/ping_monitor.log
ip link set down nic2

# 預期輸出：無錯誤訊息

# 檢查 bond0 狀態
cat /proc/net/bonding/bond0 | grep -A 5 "Slave Interface: nic2"
# 預期輸出：
# Slave Interface: nic2
# MII Status: down
# 流量應自動切換至 nic3

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
```

### 6.3 執行故障模擬 — bond2 nic4 down（使用 iperf3 驗證）

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

# 預期：iperf3 應持續運行，丟包率 < 0.1%

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

- [ ] **Step 5: 撰寫驗證步驟**

```markdown
## 7. 驗證步驟

### 7.1 檢查 bond 狀態

```bash
# 驗證 bond0 流量切換
cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave Interface"
# 預期：故障的 Slave MII Status: down，另一個 Slave up

# 驗證 bond2 流量切換
cat /proc/net/bonding/bond2 | grep -E "MII Status|Slave Interface"
# 預期：故障的 Slave MII Status: down，另一個 Slave up

# 檢查 LACP 重新協商
cat /proc/net/bonding/bond0 | grep "Actor Churn"
# 預期：Churn State: none（協商完成）
```

### 7.2 檢查 VM 連線

```bash
# 驗證 VM 持續運行
qm status 100
# 預期：status: running

# 從 VM 內部 ping gateway
ping -c 100 172.19.1.252 | grep "packet loss"
# 預期：packet loss < 3%
```

### 7.3 驗證流量切換（使用 iperf3）

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

- [ ] **Step 6: 撰寫交換機重啟模擬**

```markdown
## 8. 交換機重啟模擬（使用 ip link down 雙鏈路）

### 8.1 測試步驟

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

### 8.2 驗證 LACP 重新協商

```bash
# 檢查 bond0 是否完全恢復
cat /proc/net/bonding/bond0 | grep -E "MII Status|Number of ports"
# 預期：MII Status: up, Number of ports: 2

# 檢查 Partner 資訊（確認交換機已重新協商）
cat /proc/net/bonding/bond0 | grep "Partner Key"
# 預期：Partner Key 與故障前相同（交換機恢復）
```
```

- [ ] **Step 7: 撰寫測試結論**

```markdown
## 9. 測試結論

### 9.1 測試結果

- **通過項目**：X / 6
- **平均切換時間**：X.X 秒（預期 < 1 秒）
- **最長切換時間**：X.X 秒
- **最高丟包數**：X 個（預期 < 3 個）
- **雙目標 IP 達成率**：X.X%（預期 > 90%）

### 9.2 後續行動

- [ ] 若切換時間 > 1 秒，檢查交換機 LACP 配置（`algorithm address-based L3_L4`）
- [ ] 若丟包數 > 3 個，調整 bond miimon 參數（`miimon: 100` → `miimon: 50`）
- [ ] 將測試結果更新至 `LACP負載平衡與帶寬測試.md`
```

- [ ] **Step 8: 提交文件**

```bash
git add test-specs/TC-NW-02-LACP-故障轉移測試規格.md
git commit -m "feat: add TC-NW-02 LACP failover time test specification (P2)"
```

---

### Task 3: 更新 環境說明_Environment_Setup.md

**Files:**
- Modify: `環境說明_Environment_Setup.md:96-104`

- [ ] **Step 1: 擴充 LACP 故障轉移測試矩陣**

```markdown
## 修改後內容（替換第 96-104 行）

### LACP 故障轉移測試矩陣

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 |
|----------|----------|----------|----------|
| bond0 單鏈路中斷 | nic2/nic3 (bond0) | 流量自動切換至另一鏈路 | `ip link set down nic2` |
| bond2 單鏈路中斷 | nic4/nic5 (bond2) | 流量自動切換至另一鏈路 | `ip link set down nic4` |
| 交換器端故障 | bond0/bond2 | 流量切換至備援交換器 | 實體拔除網路線 |
| Corosync 管理網路隔離 | bond0 (管理網路) | 不應觸發 HA (需驗證) | `iptables` 阻斷通訊 |
| 管理網路中斷 | bond0 | VM 應持續運行 | SSH 連線中斷測試 |
| 雙鏈路故障 (bond0) | nic2 + nic3 | 應觸發 HA 或進入唯讀模式 | `ip link set down nic2; ip link set down nic3` |
| 雙鏈路故障 (bond2) | nic4 + nic5 | NFS 儲存中斷，VM 可能凍住 | `ip link set down nic4; ip link set down nic5` |
```

- [ ] **Step 2: 在文件末尾增加測試規格引用**

```markdown
## 測試規格文件

- TC-HA-02 測試規格：`test-specs/TC-HA-02-LACP-HA測試規格.md`
- TC-NW-02 測試規格：`test-specs/TC-NW-02-LACP-故障轉移測試規格.md`
```

- [ ] **Step 3: 提交修改**

```bash
git add 環境說明_Environment_Setup.md
git commit -m "docs: expand LACP failover test matrix with bond0/bond2 scenarios"
```

---

### Task 4: 更新 AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: 更新「測試報告產出」章節**

```markdown
## 測試報告產出

完成所有測試後，需產出以下報告：

| 報告名稱 | 檔案 | 說明 |
|----------|------|------|
| 測試初步報告 | 測試初步報告_Preliminary_Report.md | 優缺點、已知問題庫 |
| 測試計畫書 | PVE測試計畫書-摘要與目標.md | 測試目標與範圍 |
| 測試計畫表 | 測試計畫表_Test_Plan_Matrices.md | 41 項測試詳細計畫 |
| 風險評估矩陣 | PVE風險評估矩陣_Risk_Assessment_Matrix.md | 13 項風險 SOP |
| 環境說明 | 環境說明_Environment_Setup.md | 硬體與網路架構 |
| LACP 測試 | LACP負載平衡與帶寬測試.md | 20Gbps 聚合驗證 |
| LACP HA 測試規格 | test-specs/TC-HA-02-LACP-HA測試規格.md | P1 高風險測試 |
| LACP 故障轉移規格 | test-specs/TC-NW-02-LACP-故障轉移測試規格.md | P2 故障轉移時間 |
| 本地磁碟測試 | 本地磁碟效能測試分析報告v2.0.md | RAID 效能分析 |
| iperf 測試 | iperf/*.md | 網路效能壓力測試 |
| 系統環境資訊 | env/05081359-pve-env.md | 本機系統配置快照 |
```

- [ ] **Step 2: 更新「專案文件索引」章節**

```markdown
## 專案文件索引

```
/root/PVE-Testing/
├── AGENTS.md                                    (本專案)
├── test-specs/                                  (測試規格文件)
│   ├── TC-HA-02-LACP-HA測試規格.md      (P1 LACP HA 測試)
│   └── TC-NW-02-LACP-故障轉移測試規格.md (P2 故障轉移測試)
├── 環境說明_Environment_Setup.md               (硬體規格、網路規劃)
├── PVE測試計畫書-摘要與目標.md               (測試目標、範圍)
├── PVE測試計畫書-測試計畫表補充案.md         (28 項補充測試)
├── 測試計畫表_Test_Plan_Matrices.md          (41 項測試詳細計畫)
├── 測試初步報告_Preliminary_Report.md         (優缺點、已知問題)
├── PVE風險評估矩陣_Risk_Assessment_Matrix.md (13 項風險 SOP)
├── LACP負載平衡與帶寬測試.md                (20Gbps LACP 驗證)
├── 本地磁碟效能測試分析報告v2.0.md          (RAID 效能分析)
├── env/
│   └── 05081359-pve-env.md                (本機系統環境快照)
└── iperf/
    ├── iperf3.md                             (網路效能測試)
    ├── iperf壓力測試.md                      (壓力測試)
    └── 04301233_PVE_iperf3壓力測試v1.md    (iperf3 測試 v1)
```
```

- [ ] **Step 3: 提交修改**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md with test-specs references"
```

---

## Self-Review Checklist

1. **Spec coverage:** 
   - [x] TC-HA-02 測試概述、情境矩陣、實測結果、測試步驟、驗證步驟、交換機重啟、HA 敏感度調整
   - [x] TC-NW-02 測試概述、情境矩陣、實測結果、測試步驟、驗證步驟、交換機重啟
   - [x] 環境說明_Environment_Setup.md LACP 故障轉移測試矩陣擴充（bond0 + bond2）
   - [x] AGENTS.md 更新引用

2. **Placeholder scan:** No "TBD", "TODO", or incomplete sections found.

3. **Type consistency:** All test case IDs, command syntax, and file paths are consistent.

4. **Scope check:** Two independent test specs + two doc updates — appropriate for single plan.
