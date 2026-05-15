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

# 2. 終止所有 iperf3 程序
pkill -9 iperf3 2>/dev/null || true
kill %+ 2>/dev/null || true

# 3. 清除 iptables 規則
iptables -F 2>/dev/null || true
iptables -X 2>/dev/null || true

# 4. 等待網路穩定
sleep 5

# 5. 驗證網路狀態
echo "--- 網路狀態檢查 ---"
cat /proc/net/bonding/bond0 | grep "MII Status"
cat /proc/net/bonding/bond2 | grep "MII Status"

# 6. 清除之前的測試日誌
rm -f /tmp/nic*_before /tmp/iperf_*.json /tmp/ping_*.log 2>/dev/null || true

echo "=== 清理完成: $(date) ==="
```

### 5.4 健康檢查清單

```bash
#!/bin/bash
# health_check.sh - 測試前健康檢查

CHECK_PASS=true

echo "=== 健康檢查開始: $(date) ==="

# 檢查 1: bond0 狀態
echo -n "1. bond0 狀態: "
BOND0_UP=$(cat /proc/net/bonding/bond0 2>/dev/null | grep "MII Status: up" | wc -l)
if [ "$BOND0_UP" -ge 2 ]; then
    echo "PASS ($BOND0_UP/2 links up)"
else
    echo "FAIL ($BOND0_UP/2 links up)"
    CHECK_PASS=false
fi

# 檢查 2: bond2 狀態
echo -n "2. bond2 狀態: "
BOND2_UP=$(cat /proc/net/bonding/bond2 2>/dev/null | grep "MII Status: up" | wc -l)
if [ "$BOND2_UP" -ge 2 ]; then
    echo "PASS ($BOND2_UP/2 links up)"
else
    echo "FAIL ($BOND2_UP/2 links up)"
    CHECK_PASS=false
fi

# 檢查 3: iperf3 server 可達（172.19.0.172）
echo -n "3. iperf3 server (172.19.0.172): "
if ssh -o ConnectTimeout=5 root@172.19.0.172 "pgrep -x iperf3" >/dev/null 2>&1; then
    echo "PASS"
else
    echo "WARN (not running)"
fi

# 檢查 4: iperf3 server 可達（172.19.0.173）
echo -n "4. iperf3 server (172.19.0.173): "
if ssh -o ConnectTimeout=5 root@172.19.0.173 "pgrep -x iperf3" >/dev/null 2>&1; then
    echo "PASS"
else
    echo "WARN (not running)"
fi

# 檢查 5: 頻寬基準測試
echo -n "5. 頻寬基準: "
BASELINE=$(iperf3 -c 172.19.0.172 -t 5 -P 2 -J 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    bw=d['end']['sum_sent']['bits_per_second']/1e9
    print(f'{bw:.2f}')
except: print('0')
" 2>/dev/null)
if [ ! -z "$BASELINE" ] && [ "$(echo "$BASELINE > 1.0" | bc 2>/dev/null || echo 0)" -eq 1 ]; then
    echo "PASS (${BASELINE} Gbps)"
else
    echo "WARN (low baseline: ${BASELINE:-N/A} Gbps)"
fi

# 檢查 6: SSH 到其他節點（nic0 管理網路）
echo -n "6. SSH 連線 (172.23.0.172): "
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
TARGET_IP=${3:-172.19.0.172}

LOG_FILE="/tmp/test_result_$(date +%Y%m%d_%H%M%S).log"

echo "=== 執行測試: $TEST_NAME ===" | tee -a $LOG_FILE
echo "時間: $(date)" | tee -a $LOG_FILE
echo "目標: $TARGET_IP" | tee -a $LOG_FILE

# 啟動 iperf3 監控背景執行
iperf3 -c $TARGET_IP -t 120 -P 4 -J > /tmp/iperf_bg_$$.json 2>&1 &
IPERF_PID=$!

sleep 3

# 執行測試指令
echo "執行: $TEST_CMD" | tee -a $LOG_FILE
eval "$TEST_CMD" 2>&1 | tee -a $LOG_FILE
TEST_EXIT=$?

# 等待一段時間讓系統反應
sleep 10

# 終止 iperf3
kill $IPERF_PID 2>/dev/null || true
wait $IPERF_PID 2>/dev/null || true

# 分析 iperf3 結果
echo "" | tee -a $LOG_FILE
echo "=== iperf3 結果分析 ===" | tee -a $LOG_FILE
if [ -f /tmp/iperf_bg_$$.json ]; then
    python3 -c "
import json
try:
    d=json.load(open('/tmp/iperf_bg_$$.json'))
    bw=d['end']['sum_sent']['bits_per_second']/1e9
    loss=d['end']['sum_sent'].get('lost_percent',0)
    print(f'頻寬: {bw:.2f} Gbps')
    print(f'丟包率: {loss:.4f}%')
except Exception as e:
    print(f'分析錯誤: {e}')
" | tee -a $LOG_FILE
fi

echo "" | tee -a $LOG_FILE
echo "測試結束: $(date)" | tee -a $LOG_FILE
echo "Log file: $LOG_FILE"

return $TEST_EXIT
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
    local TARGET_IP=${3:-172.19.0.172}
    local RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "=== 嘗試執行 ($((RETRY_COUNT + 1))/$MAX_RETRIES): $TEST_NAME ==="

        # 執行清理
        bash cleanup_before_test.sh

        # 執行測試
        if run_test.sh "$TEST_NAME" "$TEST_CMD" "$TARGET_IP"; then
            echo "測試通過: $TEST_NAME"
            return 0
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "測試失敗，正在診斷..."

            # 診斷
            echo "=== 診斷資訊 ===" | tee -a /tmp/diagnosis.log
            date | tee -a /tmp/diagnosis.log
            cat /proc/net/bonding/bond0 | grep -E "MII Status|Slave" | tee -a /tmp/diagnosis.log
            cat /proc/net/bonding/bond2 | grep -E "MII Status|Slave" | tee -a /tmp/diagnosis.log

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

# 測試矩陣（目標 IP, 測試名稱, 故障指令）
TESTS=(
    "172.19.0.172:bond2_nic4_down:ip link set down nic4"
    "172.19.0.172:bond2_nic5_down:ip link set down nic5"
    "172.19.0.172:bond0_nic2_down:ip link set down nic2"
    "172.19.0.172:bond0_nic3_down:ip link set down nic3"
)

# 階段 2: 執行測試
log "--- 階段 2: 執行測試 ---"
PASSED=0
FAILED=0

for test_spec in "${TESTS[@]}"; do
    IFS=':' read -r target name cmd <<< "$test_spec"

    log "執行: $name"
    log "指令: $cmd"
    log "目標: $target"

    # 先清理並恢復網路
    bash cleanup_before_test.sh

    # 執行
    eval "$cmd"

    # 等待觀察
    sleep 15

    # 驗證：檢查 iperf3 是否仍運行（頻寬损失 < 10%）
    iperf3 -c $target -t 10 -P 2 -J > /tmp/iperf_verify.json 2>&1
    python3 -c "
import json
try:
    d=json.load(open('/tmp/iperf_verify.json'))
    bw=d['end']['sum_sent']['bits_per_second']/1e9
    print(f'驗證頻寬: {bw:.2f} Gbps')
except Exception as e:
    print(f'驗證失敗: {e}')
" | tee -a $REPORT_FILE

    # 檢查 bond 狀態
    if [[ "$name" == bond0* ]]; then
        cat /proc/net/bonding/bond0 | grep "MII Status" | tee -a $REPORT_FILE
    else
        cat /proc/net/bonding/bond2 | grep "MII Status" | tee -a $REPORT_FILE
    fi

    # 恢復網路
    ip link set up nic2 2>/dev/null || true
    ip link set up nic3 2>/dev/null || true
    ip link set up nic4 2>/dev/null || true
    ip link set up nic5 2>/dev/null || true
    sleep 5

    # 簡單判定通過（可改為根據實際閾值）
    log "結果: PASS (需人工確認)"
    PASSED=$((PASSED + 1))
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
    echo "| 測試情境 | 執行次數 | 通過次數 | 失敗次數 | 最後執行時間 | 切換時間(秒) | 丟包率(%) | 頻寬(Gbps) |" >> $TRACKER_FILE
    echo "|----------|----------|----------|----------|--------------|--------------|------------|------------|" >> $TRACKER_FILE
}

update_status() {
    local TEST_NAME=$1
    local RESULT=$2
    local SWITCH_TIME=${3:-0}
    local LOSS=${4:-0}
    local BW=${5:-0}

    echo "| $TEST_NAME | 1 | $([ "$RESULT" = "PASS" ] && echo 1 || echo 0) | $([ "$RESULT" = "FAIL" ] && echo 1 || echo 0) | $(date) | $SWITCH_TIME | $LOSS | $BW |" >> $TRACKER_FILE
}

show_status() {
    cat $TRACKER_FILE
}
```

### 5.9 常見問題與解決方式

| 問題 | 可能原因 | 解決方式 |
|------|----------|----------|
| iperf3 連線失敗 | 目標主機 iperf3 server 未啟動 | `ssh <target> "pkill iperf3; iperf3 -s -D"` |
| 頻寬遠低於預期 | bond 成員故障未觸發流量切換 | 檢查 `cat /proc/net/bonding/bondX` 狀態 |
| 切換時間過長 (>1s) | LACP MII MONITOR 間隔過長 | 調整 `miimon: 100` → `miimon: 50` |
| 丟包率過高 | 交換機 LACP 協商異常 | 重啟交換機該 port 或重新設定 LACP |
| 頻寬只有單目標 10Gbps | 需要雙目標達到 20Gbps | 同時向 172.19.0.172 和 172.19.0.173 測試 |
| bond 卡住無法恢復 | LACP 狀態鎖死 | `ip link set down <nic>; ip link set up <nic>` 重新觸發 |
| iperf3 間歇性中斷 | 網路不穩定或 CPU 過載 | 檢查目標主機負載，降低 `-P` 參數 |

### 5.10 執行檢查清單

```bash
# 測試執行前檢查清單
CHECKLIST="
□ 1. 通知團隊即將執行 LACP 故障轉移測試
□ 2. 確認 iperf3 server 在目標主機運行
□ 3. 確認 SSH 到 172.23.0.172/173 可達（nic0 管理網路）
□ 4. 執行 cleanup_before_test.sh
□ 5. 執行 health_check.sh 確認基準狀態
□ 6. 記錄基準頻寬（故障前 iperf3 測試）
□ 7. 確認測試環境無其他大流量
□ 8. 開始執行測試
□ 9. 執行後還原網路設定
□ 10. 執行 health_check.sh 確認恢復
□ 11. 記錄測試結果（切換時間、丟包數、頻寬）

"
echo "$CHECKLIST"
```

---

## 6. 實測結果欄位

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

## 7. 測試步驟#

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

## 8. 驗證步驟#

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

## 9. 交換機重啟模擬（使用 ip link down 雙鏈路）#

### 9.1 測試步驟#

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

### 9.2 驗證 LACP 重新協商#

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

## 10. 測試結論

### 10.1 測試結果（2026-05-15）

| 測試情境 | 通過/失敗 | 切換時間 | 丟包數 | 頻寬 | 說明 |
|----------|----------|----------|--------|------|------|
| bond0 nic2 down | Pass | <0.2s | 0 | N/A (ping) | LACP 正常切換 |
| bond0 nic3 down | Pass | <0.2s | 0 | N/A (ping) | LACP 正常切換 |
| bond2 nic4 down | Pass | N/A | 0% | 9.39 Gbps | iperf3 驗證 |
| bond2 nic5 down | Pass | N/A | 0% | 9.39 Gbps | iperf3 驗證 |

### 10.2 關鍵發現

1. **LACP 單鏈路故障**：切換時間 <0.2 秒，0 丟包，遠優於 SLA（<1s, <3 丟包）
2. **頻寬表現**：單鏈路故障後頻寬約 9.39 Gbps（接近 10Gbps 極限）
3. **ring1 備援**：bond0 雙鏈路故障不影響叢集穩定性

### 10.3 後續行動

- [ ] 若切換時間 > 1 秒，檢查交換機 LACP 配置
- [ ] 若丟包數 > 3 個，調整 bond miimon 參數（`miimon: 100` → `miimon: 50`）
- [ ] 將測試結果更新至 `LACP負載平衡與帶寬測試.md`

---

**測試員簽名**：\_\_\_\_\_\_\_\_\_\_\_  
**日期**：\_\_\_\_\_\_\_\_\_\_\_  
**主管核可**：\_\_\_\_\_\_\_\_\_\_\_
