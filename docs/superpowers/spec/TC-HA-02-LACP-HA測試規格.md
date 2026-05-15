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

> **重要**：當執行 bond0（管理網路）相關故障測試時，所有驗證指令（如 `pvecm status`、`ha-manager status`、`corosync-cmapctl`）必須從**其他健康節點**執行，而非從被測試節點執行。這是因為本機管理網路可能已中斷，無法正常執行 Cluster 管理指令。
>
> 驗證方式：從 nic0 SSH 到其他節點（如 `ssh root@172.23.0.172` 或 `ssh root@172.23.0.173`）

### 4.1 測試情境（bond0 管理網路）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 | 備註 |
|----------|----------|----------|----------|--------|------|
| bond0 單鏈路故障 | nic2 (bond0) | 不應觸發 HA | `ip link set down nic2`; SSH 驗證 | P1 | 流量切換至 nic3 |
| bond0 單鏈路故障 | nic3 (bond0) | 不應觸發 HA | `ip link set down nic3`; SSH 驗證 | P1 | 流量切換至 nic2 |
| bond0 雙鏈路故障 | nic2 + nic3 | Quorate 維持（ring1 備援），不應觸發 HA | `ip link set down nic2; ip link set down nic3`; SSH 驗證 | P1 | 因 ring1 備援不觸發 HA |
| **【新】雙 Ring 同步中斷** | bond0 + bond2 | **應觸發 HA 或叢集失效** | SSH 驗證 | P1 | 真正測試 HA 觸發 |
| Corosync ring0 隔離 | 172.19.0.172 (iptables) | Quorate 維持（ring1 備援） | `iptables`; SSH 驗證 | P1 | 預期不同於原始 spec |
| **【新】Corosync ring0+ring1 同步隔離** | 172.19.0.172 + 10.23.0.172 | **應觸發 HA** | `iptables`; SSH 驗證 | P1 | 真正測試 HA 觸發 |

### 4.2 測試情境（bond2 儲存網路）

> **注意**：bond2 故障測試可本地驗證（不涉及管理網路中斷）

| 測試情境 | 測試對象 | 預期行為 | 驗證方式 | 優先序 | 備註 |
|----------|----------|----------|----------|--------|------|
| bond2 單鏈路故障 | nic4 (bond2) | 不應觸發 HA | `ip link set down nic4`; iperf3 驗證 | P1 | 流量切換至 nic5 |
| bond2 單鏈路故障 | nic5 (bond2) | 不應觸發 HA | `ip link set down nic5`; iperf3 驗證 | P1 | 流量切換至 nic4 |
| bond2 雙鏈路故障 | nic4 + nic5 | 儲存 I/O 中斷，VM 可能凍住 | `ip link set down nic4; ip link set down nic5` | P2 | 觀察 VM I/O 行 |

---

## 5. 可重複執行測試計劃

### 5.1 測試設計原則

| 原則 | 說明 |
|------|------|
| **冪等性 (Idempotent)** | 測試可以安全地重複執行，結果一致 |
| **可復原 (Recoverable)** | 失敗後可清理並重新執行 |
| **隔離性 (Isolated)** | 每個測試獨立，不依賴其他測試結果 |
| **可追蹤 (Traceable)** | 所有操作都有日誌記錄 |

### 5.2 執行流程

```
┌─────────────────────────────────────────────────────────────┐
│                    測試執行流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [0. 清理/重置] → [1. 健康檢查] → [2. 執行測試]              │
│         ↑                ↓                                  │
│         │                ↓                                  │
│         └──── 失敗 → [3. 診斷] → [4. 修復] ──┘              │
│                                     ↓                        │
│                               [5. 重新執行]                  │
│                                     ↓                        │
│                               [6. 完成/報告]                │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 清理/重置腳本（執行前必備）

```bash
#!/bin/bash
# cleanup_before_test.sh - 測試前清理與重置

echo "=== 測試前清理開始: $(date) ==="

# 1. 確保所有網路介面已恢復
ip link set up nic2 2>/dev/null || true
ip link set up nic3 2>/dev/null || true
ip link set up nic4 2>/dev/null || true
ip link set up nic5 2>/dev/null || true

# 2. 清除 iptables 規則
iptables -F 2>/dev/null || true
iptables -X 2>/dev/null || true

# 3. 等待網路穩定
sleep 5

# 4. 驗證網路狀態
echo "--- 網路狀態檢查 ---"
cat /proc/net/bonding/bond0 | grep "MII Status"
cat /proc/net/bonding/bond2 | grep "MII Status"

# 5. 驗證 Cluster 狀態
echo "--- Cluster 狀態檢查 ---"
pvecm status 2>/dev/null || echo "WARN: pvecm 失敗"

# 6. 清除之前的測試日誌
rm -f /tmp/nic*_before /tmp/ha_status_* /tmp/pvecm_* /tmp/iperf_*.json 2>/dev/null || true

echo "=== 清理完成: $(date) ==="
```

### 5.4 健康檢查清單

```bash
#!/bin/bash
# health_check.sh - 測試前健康檢查

CHECK_PASS=true

echo "=== 健康檢查開始: $(date) ==="

# 檢查 1: Cluster Quorate
echo -n "1. Cluster Quorate: "
if pvecm status 2>/dev/null | grep -q "Quorate: Yes"; then
    echo "PASS"
else
    echo "FAIL"
    CHECK_PASS=false
fi

# 檢查 2: HA 服務運行
echo -n "2. HA Manager: "
if ha-manager status 2>/dev/null | grep -q "HA  MANAGER: running"; then
    echo "PASS"
else
    echo "FAIL"
    CHECK_PASS=false
fi

# 檢查 3: bond0 狀態
echo -n "3. bond0 狀態: "
BOND0_UP=$(cat /proc/net/bonding/bond0 2>/dev/null | grep "MII Status: up" | wc -l)
if [ "$BOND0_UP" -ge 2 ]; then
    echo "PASS ($BOND0_UP/2 links up)"
else
    echo "FAIL ($BOND0_UP/2 links up)"
    CHECK_PASS=false
fi

# 檢查 4: bond2 狀態
echo -n "4. bond2 狀態: "
BOND2_UP=$(cat /proc/net/bonding/bond2 2>/dev/null | grep "MII Status: up" | wc -l)
if [ "$BOND2_UP" -ge 2 ]; then
    echo "PASS ($BOND2_UP/2 links up)"
else
    echo "FAIL ($BOND2_UP/2 links up)"
    CHECK_PASS=false
fi

# 檢查 5: VM 105 運行
echo -n "5. VM 105 狀態: "
if qm status 105 2>/dev/null | grep -q "status: running"; then
    echo "PASS"
else
    echo "FAIL"
    CHECK_PASS=false
fi

# 檢查 6: Corosync members 完整
echo -n "6. Corosync members: "
MEMBERS=$(corosync-cmapctl 2>/dev/null | grep "runtime.config.active members" | wc -l)
if [ "$MEMBERS" -ge 1 ]; then
    echo "PASS"
else
    echo "FAIL"
    CHECK_PASS=false
fi

# 檢查 7: SSH 到其他節點
echo -n "7. SSH 連線 (172.23.0.172): "
if ssh -o ConnectTimeout=5 root@172.23.0.172 "echo ok" 2>/dev/null | grep -q "ok"; then
    echo "PASS"
else
    echo "FAIL"
    CHECK_PASS=false
fi

echo "=== 健康檢查完成: $(date) ==="

if [ "$CHECK_PASS" = false ]; then
    echo "警告: 健康檢查有失敗項目，請確認後再執行測試"
    exit 1
else
    echo "所有檢查通過，可以執行測試"
    exit 0
fi
```

### 5.5 測試執行包裝腳本

```bash
#!/bin/bash
# run_test.sh - 單一測試執行包裝

TEST_NAME=$1
TEST_CMD=$2
EXPECTED=$3

LOG_FILE="/tmp/test_result_$(date +%Y%m%d_%H%M%S).log"

echo "=== 執行測試: $TEST_NAME ==="
echo "時間: $(date)" | tee -a $LOG_FILE

# 執行測試指令
eval "$TEST_CMD" 2>&1 | tee -a $LOG_FILE
EXIT_CODE=${PIPESTATUS[0]}

# 等待一段時間讓系統反應
sleep 5

# 驗證結果
echo "" | tee -a $LOG_FILE
echo "=== 驗證結果 ===" | tee -a $LOG_FILE

# SSH 到其他節點驗證
ssh root@172.23.0.172 "pvecm status" 2>&1 | tee -a $LOG_FILE
ssh root@172.23.0.173 "ha-manager status" 2>&1 | tee -a $LOG_FILE

echo "" | tee -a $LOG_FILE
echo "測試結束: $(date)" | tee -a $LOG_FILE
echo "Log file: $LOG_FILE"

return $EXIT_CODE
```

### 5.6 失敗處理與重試流程

```bash
#!/bin/bash
# retry_test.sh - 失敗時重試機制

MAX_RETRIES=3
RETRY_DELAY=30

run_test_with_retry() {
    local TEST_NAME=$1
    local TEST_CMD=$2
    local RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "=== 嘗試執行 ($((RETRY_COUNT + 1))/$MAX_RETRIES): $TEST_NAME ==="

        # 執行清理
        bash cleanup_before_test.sh

        # 執行測試
        if run_test.sh "$TEST_NAME" "$TEST_CMD"; then
            echo "測試通過: $TEST_NAME"
            return 0
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "測試失敗，正在診斷..."

            # 診斷
            echo "=== 診斷資訊 ===" | tee -a /tmp/diagnosis.log
            date | tee -a /tmp/diagnosis.log
            ssh root@172.23.0.172 "pvecm status; corosync-cmapctl | grep members" 2>&1 | tee -a /tmp/diagnosis.log

            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo "等待 $RETRY_DELAY 秒後重試..."
                sleep $RETRY_DELAY
            fi
        fi
    done

    echo "測試失敗，已達最大重試次數: $MAX_RETRIES"
    return 1
}
```

### 5.7 完整測試執行腳本

```bash
#!/bin/bash
# full_test_run.sh - 完整測試計劃執行

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="/tmp/test_report_$TIMESTAMP.txt"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $REPORT_FILE
}

log "========== 開始完整測試執行 =========="
log "報告檔案: $REPORT_FILE"

# 階段 0: 清理
log "--- 階段 0: 清理與重置 ---"
bash cleanup_before_test.sh

# 階段 1: 健康檢查
log "--- 階段 1: 健康檢查 ---"
if ! bash health_check.sh; then
    log "錯誤: 健康檢查失敗，請先修復問題"
    exit 1
fi

# 測試矩陣
TESTS=(
    "bond0_nic2_down:ip link set down nic2:nic2 should recover"
    "bond0_nic3_down:ip link set down nic3:nic3 should recover"
    "bond0_dual_down:ip link set down nic2 && ip link set down nic3:both should recover"
    "bond2_nic4_down:ip link set down nic4:nic4 should recover"
    "bond2_nic5_down:ip link set down nic5:nic5 should recover"
)

# 階段 2: 執行測試
log "--- 階段 2: 執行測試 ---"
PASSED=0
FAILED=0

for test_spec in "${TESTS[@]}"; do
    IFS=':' read -r name cmd expected <<< "$test_spec"

    log "執行: $name"
    log "指令: $cmd"

    # 先清理
    bash cleanup_before_test.sh

    # 執行
    eval "$cmd"

    # 等待觀察
    sleep 10

    # 驗證
    if ssh root@172.23.0.172 "pvecm status" 2>/dev/null | grep -q "Quorate: Yes"; then
        log "結果: PASS"
        PASSED=$((PASSED + 1))
    else
        log "結果: FAIL"
        FAILED=$((FAILED + 1))
        # 重試
        log "重試測試: $name"
        bash retry_test.sh "$name" "$cmd"
    fi

    # 恢復
    ip link set up nic2 2>/dev/null || true
    ip link set up nic3 2>/dev/null || true
    ip link set up nic4 2>/dev/null || true
    ip link set up nic5 2>/dev/null || true
    sleep 5
done

# 階段 3: 最終驗證
log "--- 階段 3: 最終驗證 ---"
bash health_check.sh

# 階段 4: 生成報告
log "========== 測試執行完成 =========="
log "通過: $PASSED"
log "失敗: $FAILED"
log "報告: $REPORT_FILE"
```

### 5.8 測試結果追蹤表

```bash
# test_status_tracker.sh - 追蹤測試狀態

TRACKER_FILE="/tmp/test_status_tracker.txt"

init_tracker() {
    echo "=== 測試狀態追蹤 ===" > $TRACKER_FILE
    echo "建立時間: $(date)" >> $TRACKER_FILE
    echo "" >> $TRACKER_FILE
    echo "| 測試情境 | 執行次數 | 通過次數 | 失敗次數 | 最後執行時間 | 狀態 |" >> $TRACKER_FILE
    echo "|----------|----------|----------|----------|--------------|------|" >> $TRACKER_FILE
}

update_status() {
    local TEST_NAME=$1
    local RESULT=$2
    local RUNS=1
    local PASSES=0
    local FAILS=0

    if [ "$RESULT" = "PASS" ]; then
        PASSES=1
    else
        FAILS=1
    fi

    echo "| $TEST_NAME | $RUNS | $PASSES | $FAILS | $(date) | $RESULT |" >> $TRACKER_FILE
}

show_status() {
    cat $TRACKER_FILE
}
```

### 5.9 常見問題與解決方式

| 問題 | 可能原因 | 解決方式 |
|------|----------|----------|
| `pvecm status` 無回應 | bond0 雙鏈路中斷 | SSH 到其他節點檢查 |
| HA 誤觸發 | Corosync deadtime 過短 | 調整至 10s |
| 網路無法恢復 | bond 卡住 | `ip link set down && up` 重新觸發 LACP |
| 成員消失但 quorum 還在 | ring1 備援生效 | 正常，檢查 ring0 狀態 |
| Fence 一直觸發 | 網路持續不穩定 | 暫停測試，檢查交換機 |

### 5.10 執行檢查清單

```bash
# 測試執行前檢查清單
CHECKLIST="

□ 1. 通知團隊即將執行測試（高風險）
□ 2. 確認 VM 快照已建立
□ 3. 確認其餘節點 SSH 可達
□ 4. 確認監控系統已開啟
□ 5. 記錄測試開始時間
□ 6. 執行 cleanup_before_test.sh
□ 7. 執行 health_check.sh
□ 8. 確認所有檢查通過
□ 9. 開始執行測試
□ 10. 執行後還原網路設定
□ 11. 執行 health_check.sh 確認恢復
□ 12. 記錄測試結果

"
echo "$CHECKLIST"
```

---

## 7. 測試步驟

### 7.1 準備階段

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

### 7.2 執行測試 — bond0 單鏈路故障（nic2）

```bash
# 記錄測試前基數
ip -s link show nic2 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic2_before
ip -s link show nic3 | grep -A 1 'TX:' | tail -1 | awk '{print $1}' > /tmp/nic3_before
ssh root@172.23.0.172 "ha-manager status" > /tmp/ha_status_before

# 執行故障模擬
echo "=== 測試開始: $(date) ==="
ip link set down nic2

# 預期輸出：無錯誤訊息，命令直接返回

# 檢查 bond0 狀態（本地）
cat /proc/net/bonding/bond0 | grep -A 10 "Slave Interface: nic2"
# 預期輸出：
# Slave Interface: nic2
# MII Status: down
# Link Failure Count: X (增加 1)

# 檢查流量是否切換至 nic3
watch -n 1 'ip -s link show nic3 | grep TX'
# 預期：nic3 TX 流量增加

# =============================================
# 重要：從其他健康節點驗證 Cluster 狀態
# 原因：nic2 斷線可能影響 Corosync 穩定性
# =============================================
sleep 10

# SSH 到 sd-sandbox-pve02 (172.23.0.172) 檢查 cluster 狀態
ssh root@172.23.0.172 "pvecm status"
# 預期：Quorate: Yes，三節點仍在 cluster 中

ssh root@172.23.0.172 "corosync-cmapctl | grep members"
# 預期：三個節點都仍在 members 中

ssh root@172.23.0.172 "ha-manager status"
# 預期：不應有 VM 被遷移或重啟，狀態應為 active 或 standby

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 交叉驗證
ssh root@172.23.0.173 "pvecm status"
ssh root@172.23.0.173 "ha-manager status"

# 本地檢查 VM 是否持續運行
qm status 105
# 預期：status: running

# 恢復網路
ip link set up nic2
cat /proc/net/bonding/bond0 | grep "MII Status"
# 預期：MII Status: up（兩個 Slave 都 up）

# 再次從其他節點驗證恢復
ssh root@172.23.0.172 "pvecm status"
```

### 7.3 執行測試 — bond0 雙鏈路故障

```bash
# 模擬 bond0 完全斷線
ip link set down nic2
ip link set down nic3

# =============================================
# 重要：本機已無法執行 Cluster 管理指令
# 必須從其他健康節點驗證！
# =============================================
echo "雙鏈路已中斷: $(date)"

# SSH 到 sd-sandbox-pve02 (172.23.0.172) 檢查 cluster 狀態
ssh root@172.23.0.172 "pvecm status"
# 可能的輸出：
# - Quorate: Yes（因 ring1 備援，叢集仍正常）
# - 或 Quorate: No（若 ring1 也受影響）

ssh root@172.23.0.172 "corosync-cmapctl | grep members"
# 預期：sd-sandbox-pve01 可能從 members 中消失（若完全隔離）

ssh root@172.23.0.172 "ha-manager status"
# 可能的輸出：fence 機制觸發，VM 被標記為 fenced

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 交叉驗證
ssh root@172.23.0.173 "pvecm status"
ssh root@172.23.0.173 "ha-manager status"

# 檢查 VM 105 狀態（從 172.23.0.173 檢查）
ssh root@172.23.0.173 "qm status 105"
# 可能的輸出：status: running 或 stopped

# 恢復網路
ip link set up nic2
ip link set up nic3
sleep 5

# 從其他節點驗證恢復
ssh root@172.23.0.172 "pvecm status"
# 預期：Quorate: Yes，三節點恢復
```

### 7.4 執行測試 — Corosync 管理網路隔離

```bash
# 使用 iptables 阻斷與另一節點的通訊（模擬網路分割）
# 測試隔離 sandbox-pve02 (172.19.0.172)

# 記錄測試前狀態（從其他節點）
ssh root@172.23.0.173 "pvecm status" > /tmp/pvecm_before_isolation
ssh root@172.23.0.173 "ha-manager status" > /tmp/ha_before_isolation

# 執行隔離
iptables -A INPUT -s 172.19.0.172 -j DROP
echo "隔離開始: $(date)"

# =============================================
# 重要：從未隔離的節點驗證隔離效果
# =============================================

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 檢查 cluster 狀態
# 此時 172.23.0.173 仍可見 172.19.0.172（因為隔離只影響本機）
ssh root@172.23.0.173 "corosync-cmapctl | grep members"
# 預期：172.19.0.172 仍可能在 members 中（視隔離方向）

ssh root@172.23.0.173 "pvecm status"
# 預期：Quorate 應仍為 Yes（因為剩餘 2+ 票）

ssh root@172.23.0.173 "ha-manager status"
# 預期：不應有 VM 被遷移（因為 quorum 仍存在）

# 從本機檢查（本機已隔離 172.19.0.172）
corosync-cmapctl | grep members
# 預期：172.19.0.172 從 members 中消失

# 恢復網路
iptables -D INPUT -s 172.19.0.172 -j DROP
sleep 5

# 從其他節點驗證恢復
ssh root@172.23.0.173 "pvecm status"
# 預期：三節點恢復
```

### 7.5 執行測試 — 雙 Ring 同步中斷（真正 HA 測試）

```bash
# 同步阻斷 ring0 (172.19.0.x) 和 ring1 (10.23.0.x) 與 172.19.0.172 的通訊
# 此測試會隔離 sandbox-pve02，觸發真正的 HA 條件

# =============================================
# 重要：從健康節點記錄測試前狀態
# =============================================
ssh root@172.23.0.173 "ha-manager status" > /tmp/ha_status_before_full
ssh root@172.23.0.173 "pvecm status" > /tmp/pvecm_before_full

# 執行同步隔離（本機隔離 172.19.0.172 的兩個 ring）
iptables -A INPUT -s 172.19.0.172 -j DROP
iptables -A INPUT -s 10.23.0.172 -j DROP
echo "雙 Ring 隔離開始: $(date)"

# 等待 15 秒（考慮 deadtime）
sleep 15

# =============================================
# 重要：從未隔離的節點驗證 HA 觸發
# =============================================

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 檢查 cluster 狀態
ssh root@172.23.0.173 "corosync-cmapctl | grep members"
# 預期：172.19.0.172 從 members 中消失（因雙 ring 都被隔離）

ssh root@172.23.0.173 "pvecm status"
# 預期：
# - Quorate: No（只剩 2 票，低於 expected 3）
# - 或叢集分割

ssh root@172.23.0.173 "ha-manager status"
# 預期：
# - Fence 機制觸發
# - VM105 被標記為 starting/migrating/fenced

# SSH 到 sd-sandbox-pve03 檢查 VM 狀態
ssh root@172.23.0.173 "qm status 105"
# 可能的輸出：status: running（HA 已遷移）或 stopped（待啟動）

# 恢復網路
iptables -D INPUT -s 172.19.0.172 -j DROP
iptables -D INPUT -s 10.23.0.172 -j DROP
sleep 10

# 從健康節點驗證恢復
ssh root@172.23.0.173 "pvecm status"
# 預期：Quorate: Yes，三節點恢復
```

---

## 8. 驗證步驟

### 8.1 檢查 bond 狀態

```bash
# 驗證 bond0 流量分散
watch -n 1 'ip -s link show nic2 | grep TX; ip -s link show nic3 | grep TX'
# 預期：恢復後兩條鏈路都有流量（若有多個連接）

# 驗證 bond0 狀態
cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave Interface|Link Failure"
# 預期：MII Status: up, 兩個 Slave Link Failure Count 不再增加
```

### 8.2 檢查 VM 連線

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

### 8.3 檢查 Corosync 狀態

```bash
# =============================================
# 重要：故障測試後從健康節點驗證
# =============================================

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 驗證 corosync 成員完整
ssh root@172.23.0.173 "corosync-cmapctl runtime.config.active | grep members"
# 預期：三個節點都在 members 中

# 檢查 corosync 日誌（是否有錯誤）
ssh root@172.23.0.173 "journalctl -u corosync --since '5 min ago' | grep -i 'error\|warn\|fail'"
# 預期：無錯誤或僅有預期的 "link down" 訊息
```

### 8.4 檢查 HA 狀態

```bash
# =============================================
# 重要：從健康節點驗證 HA 未非預期觸發
# =============================================

# SSH 到 sd-sandbox-pve03 (172.23.0.173) 驗證 HA 狀態
ssh root@172.23.0.173 "ha-manager status"
# 預期：active 或 standby，無 "fenced" 或 "restarting" 狀態

# 檢查 HA 日誌
ssh root@172.23.0.173 "journalctl -u pve-ha-lrm --since '5 min ago' | grep -i 'error\|restart\|migrate'"
# 預期：無非預期的 VM restart 或 migrate 紀錄
```

---

## 9. 交換機重啟模擬（使用 ip link down 雙鏈路）

### 9.1 測試情境

由於無 Switch 管理權限，使用 `ip link set down` 模擬交換機重啟（雙鏈路同時斷線）。

### 9.2 測試步驟

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

### 9.3 驗證步驟

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
ssh root@172.23.0.172 "pvecm status"
# 預期：Quorate: Yes
```

---

## 10. HA 敏感度調整建議

### 10.1 若 HA 非預期觸發

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

### 10.2 建議配置

| 參數 | 預設值 | 保守值 | 說明 |
|------|--------|--------|------|
| deadtime | 1s | 10s | 認定節點死亡前的等待時間 |
| token | 1000ms | 5000ms | 單一 token 循環時間 |
| token_retransmits_before_loss_const | 4 | 10 | 重傳次數後判定 loss |

### 10.3 Corosync 流量移至專用網段

**狀態：已實現**

 Corosync 已經配置雙 ring：
 - ring0: 172.19.0.x (管理網路，經由 vmbr0.19)
 - ring1: 10.23.0.x (儲存網路，經由 bond2)

 此設計提供網路備援，單一 ring 故障不會導致叢集失效。

 **建議：** 未來規劃時應考慮此雙 ring 設計的備援特性。

---

## 11. 測試結論

### 11.1 測試結果（2026-05-15 更新）

| 測試情境 | 通過/失敗 | HA 觸發 | 驗證方式 | 說明 |
|----------|----------|---------|----------|------|
| bond0 nic2 down | Pass | 否 | SSH 到 172.23.0.172 驗證 | LACP 正常切換 |
| bond0 nic3 down | Pass | 否 | SSH 到 172.23.0.172 驗證 | LACP 正常切換 |
| bond0 雙鏈路 down | Pass | 否 | SSH 到 172.23.0.172/173 驗證 | ring1 備援生效 |
| 雙 Ring 同步中斷 | 待測試 | - | SSH 到 172.23.0.173 驗證 | 需執行 |
| bond2 nic4 down | Pass | 否 | 本地驗證 | LACP 正常切換 |
| bond2 nic5 down | Pass | 否 | 本地驗證 | LACP 正常切換 |
| Corosync ring0 隔離 | Pass | 否 | SSH 到 172.23.0.173 驗證 | ring1 備援生效 |
| Corosync 雙 Ring 隔離 | 待測試 | - | SSH 到 172.23.0.173 驗證 | 需執行 |

> **注意**：所有涉及 bond0（管理網路）故障的測試，驗證指令必須從其他健康節點（如 172.23.0.172 或 172.23.0.173）執行，因為本機管理網路可能已中斷。

### 11.2 關鍵發現

1. **Corosync 雙 ring 設計正確運作**：ring1 (10.23.0.x) 為 ring0 (172.19.0.x) 提供備援
2. **LACP 單鏈路故障**：切換時間 <0.2s，0 丟包，符合 SLA
3. **bond0 雙鏈路故障**：不會導致叢集失效（因 ring1 備援）
4. **真正 HA 測試**：需同步阻斷 ring0 + ring1

### 11.3 後續行動

- [ ] 執行「雙 Ring 同步中斷」測試以驗證 HA 觸發
- [ ] 更新相關風險評估矩陣
- [ ] 將測試結果同步至 AGENTS.md

---

**測試員簽名**：\_\_\_\_\_\_\_\_\_\_\_  
**日期**：\_\_\_\_\_\_\_\_\_\_\_  
**主管核可**：\_\_\_\_\_\_\_\_\_\_\_
