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

- [ ] 三節點叢集運行正常（`pvecm status` 顯示 Quorate: Yes）
- [ ] HA 機制已啟用（`ha-manager status` 無錯誤）
- [ ] 至少一台 VM 已設定 HA 管理（`ha-manager add vm:105`）
- [ ] 記錄當前 Corosync 參數（`corosync-cmapctl | grep -E 'deadtime|token'`）
- [ ] 準備 NetApp FAS2650 快照或 VM 快照（高風險測試）
- [ ] 確認 iDRAC/IPMI 可連線（fence 機制測試備用）

---

## 4. 測試情境矩陣

### 4.1 測試情境（bond0 管理網路）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 | 備註 |
|----------|----------|----------|----------|--------|------|
| bond0 單鏈路故障 | nic2 (bond0) | 不應觸發 HA | `ip link set down nic2` | P1 | 流量切換至 nic3 |
| bond0 單鏈路故障 | nic3 (bond0) | 不應觸發 HA | `ip link set down nic3` | P1 | 流量切換至 nic2 |
| bond0 雙鏈路故障 | nic2 + nic3 | Quorate 維持（ring1 備援），不應觸發 HA | `ip link set down nic2; ip link set down nic3` | P1 | 需更新：因 ring1 備援不觸發 HA |
| **【新】雙 Ring 同步中斷** | bond0 + bond2 | **應觸發 HA 或叢集失效** | `ip link set down nic2; ip link set down nic3; ip link set down nic4; ip link set down nic5` | P1 | 新增：真正測試 HA 觸發 |
| Corosync ring0 隔離 | 172.19.0.172 (iptables) | Quorate 維持（ring1 備援） | `iptables -A INPUT -s 172.19.0.172 -j DROP` | P1 | 需更新：預期不同於原始 spec |
| **【新】Corosync ring0+ring1 同步隔離** | 172.19.0.172 + 10.23.0.172 | **應觸發 HA** | `iptables -A INPUT -s 172.19.0.172 -j DROP; iptables -A INPUT -s 10.23.0.172 -j DROP` | P1 | 新增：真正測試 HA 觸發 |

### 4.2 測試情境（bond2 儲存網路）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 | 備註 |
|----------|----------|----------|----------|--------|------|
| bond2 單鏈路故障 | nic4 (bond2) | 不應觸發 HA | `ip link set down nic4` | P1 | 流量切換至 nic5 |
| bond2 單鏈路故障 | nic5 (bond2) | 不應觸發 HA | `ip link set down nic5` | P1 | 流量切換至 nic4 |
| bond2 雙鏈路故障 | nic4 + nic5 | 儲存 I/O 中斷，VM 可能凍住 | `ip link set down nic4; ip link set down nic5` | P2 | 觀察 VM I/O 行 |

---

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

---

## 6. 測試步驟

### 6.1 準備階段

```bash
# 檢查初始狀態
pvecm status
# 預期輸出：Quorate: Yes, Expected votes: 3, Total votes: 3

ha-manager status
# 預期輸出：active 或 standby

cat /proc/net/bonding/bond0
# 預期輸出：MII Status: up; 兩個 Slave Interface: up

cat /proc/net/bonding/bond2
# 預期輸出：MII Status: up; 兩個 Slave Interface: up

corosync-cmapctl | grep -E 'deadtime|token'
# 預期輸出：config.totem.deadtime (default 1000ms), config.totem.token (default 1000ms)

# 檢查 VM 狀態
qm status 105
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

# 檢查 Corosync 狀態
corosync-cmapctl | grep members
# 預期：三個節點都仍在 members 中

# 檢查 VM 是否持續運行
qm status 105
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

### 6.5 執行測試 — 雙 Ring 同步中斷（真正 HA 測試）

```bash
# 同步阻斷 ring0 (172.19.0.x) 和 ring1 (10.23.0.x) 與 172.19.0.172 的通訊
# 此測試會隔離 sandbox-pve02，觸發真正的 HA 條件

# 記錄測試前狀態
ha-manager status > /tmp/ha_status_before_full
pvecm status > /tmp/pvecm_before_full

# 執行同步隔離
iptables -A INPUT -s 172.19.0.172 -j DROP
iptables -A INPUT -s 10.23.0.172 -j DROP
echo "雙 Ring 隔離開始: $(date)"

# 等待 15 秒（考慮 deadtime）
sleep 15

# 檢查 Corosync 成員狀態
corosync-cmapctl | grep members

# 檢查 quorum
pvecm status
# 預期：
# - Quorate: No 或叢集分割
# - 172.19.0.172 應從 members 中消失

# 檢查 HA 是否觸發
ha-manager status
# 預期：
# - Fence 機制觸發
# - VM 被標記為 starting/migrating/fenced

# 恢復網路
iptables -D INPUT -s 172.19.0.172 -j DROP
iptables -D INPUT -s 10.23.0.172 -j DROP
pvecm status
# 預期：Quorate: Yes，三節點恢復
```

---

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

```bash#
# 驗證 VM 持續運行#
qm status 105#
# 預期：status: running#

# 從 VM 105 內部 ping gateway（透過 expect + script + qm terminal）
# 建立 expect 腳本（timeout 10 秒）
cat > /tmp/vm105_ping.exp << 'EXPECT_EOF'
set timeout 10
spawn script -q -c "qm terminal 105"
expect {
    "login:" { send "ubuntu\r"; exp_continue }
    "Password:" { send "1qaz@WSX\r"; exp_continue }
    "~$" { send "ping -c 5 172.24.253.1\r" }
    timeout { puts "Timeout"; exit 1 }
}
expect eof
EXPECT_EOF

expect /tmp/vm105_ping.exp 2>&1 | grep -E "packet|loss|rtt"
# 預期：0% packet loss#

# 驗證 VM I/O 正常（透過 expect + script + qm terminal）
cat > /tmp/vm105_io.exp << 'EXPECT_EOF'
set timeout 10
spawn script -q -c "qm terminal 105"
expect {
    "login:" { send "ubuntu\r"; exp_continue }
    "Password:" { send "1qaz@WSX\r"; exp_continue }
    "~$" { send "dd if=/dev/zero of=/tmp/test bs=1M count=100\r" }
    timeout { puts "Timeout"; exit 1 }
}
expect eof
EXPECT_EOF

expect /tmp/vm105_io.exp 2>&1 | tail -5
# 預期：完成無錯誤（100+0 records in/out）
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

---

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
# 另一終端持續 ping gateway，記錄第一個丟包到最後一個丟包之間的時間
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
qm status 105
# 預期：status: running

# 檢查 Corosync
pvecm status
# 預期：Quorate: Yes
```

---

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
#     ...
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

### 9.3 Corosync 流量移至專用網段

**狀態：已實現**

 Corosync 已經配置雙 ring：
 - ring0: 172.19.0.x (管理網路，經由 vmbr0.19)
 - ring1: 10.23.0.x (儲存網路，經由 bond2)

 此設計提供網路備援，單一 ring 故障不會導致叢集失效。

 **建議：** 未來規劃時應考慮此雙 ring 設計的備援特性。

---

## 10. 測試結論

### 10.1 測試結果（2026-05-15 更新）

| 測試情境 | 通過/失敗 | HA 觸發 | 說明 |
|----------|----------|---------|------|
| bond0 nic2 down | Pass | 否 | LACP 正常切換 |
| bond0 nic3 down | Pass | 否 | LACP 正常切換 |
| bond0 雙鏈路 down | Pass | 否 | ring1 備援生效 |
| 雙 Ring 同步中斷 | 待測試 | - | 需執行 |
| bond2 nic4 down | Pass | 否 | LACP 正常切換 |
| bond2 nic5 down | Pass | 否 | LACP 正常切換 |
| Corosync ring0 隔離 | Pass | 否 | ring1 備援生效 |
| Corosync 雙 Ring 隔離 | 待測試 | - | 需執行 |

### 10.2 關鍵發現

1. **Corosync 雙 ring 設計正確運作**：ring1 (10.23.0.x) 為 ring0 (172.19.0.x) 提供備援
2. **LACP 單鏈路故障**：切換時間 <0.2s，0 丟包，符合 SLA
3. **bond0 雙鏈路故障**：不會導致叢集失效（因 ring1 備援）
4. **真正 HA 測試**：需同步阻斷 ring0 + ring1

### 10.3 後續行動

- [ ] 執行「雙 Ring 同步中斷」測試以驗證 HA 觸發
- [ ] 更新相關風險評估矩陣
- [ ] 將測試結果同步至 AGENTS.md

---

**測試員簽名**：\_\_\_\_\_\_\_\_\_\_\_  
**日期**：\_\_\_\_\_\_\_\_\_\_\_  
**主管核可**：\_\_\_\_\_\_\_\_\_\_\_
