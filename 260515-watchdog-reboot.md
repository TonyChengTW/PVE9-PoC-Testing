# Watchdog Timeout 導致節點重開機事件紀錄

**事件日期**: 2026-05-15
**受影響節點**: 172.23.0.172 (sd-sandbox-pve02)
**觸發測試**: `make test-ha-dual-ring` (Corosync 雙 ring 隔離測試)
**文件版本**: v1.0

---

## 1. 事件摘要

| 項目 | 內容 |
|------|------|
| 事件類型 | Watchdog 觸發的系統重開機（非 Kernel Panic） |
| 受影響節點 | sd-sandbox-pve02 (172.23.0.172) |
| 叢集其他節點 | 未受影響，正常運作 |
| VM 105 最終位置 | sd-sandbox-pve01 (172.23.0.171) - HA Failover 成功 |
| 測試目的 | 驗證 Corosync 雙 ring 隔離時 HA 應觸發 failover |
| 測試結果 | HA 功能正常，但副作用是隔離節點被 watchdog 重開機 |

---

## 2. 時間線

| 時間 | 事件 | 備註 |
|------|------|------|
| 17:42:24 | 測試開始：加入 iptables 規則封鎖 172.19.0.172 和 10.23.0.172 | 同時在本地、172、173 上加規則 |
| 17:42:39 | 驗證 HA 狀態：叢集成員重組為 2 節點 | Corosync 開始形成新 membership |
| 17:43:16 | Corosync 完成重組，形成 2 節點成員 (Node 2, Node 3) | 172.23.0.172 已被隔離 |
| 17:43:17 | pmxcfs 開始不斷重試 cpg_send_message | 嘗試與節點 1 同步但失敗 |
| 17:43:24 | iperf3 服務重啟計數達 179 次 | 端口衝突，但非主要問題 |
| 17:43:33 | pve-ha-crm 狀態變更：wait_for_quorum => slave | 節點進入從模式 |
| 17:43:34 | watchdog-mux 報告 client watchdog 過期 | 關鍵觸發點 |
| 17:43:34 | watchdog-mux: exit watchdog-mux with active connections | 準備退出 |
| 17:43:35 | kernel: watchdog0: watchdog did not stop! | 系統開始重開機流程 |
| 17:43:43 | watchdog-mux.service: Deactivated successfully | 服務完全停止 |
| 17:47:15 | sd-sandbox-pve02 完成重開機，系統上線 | 恢復運作 |

---

## 3. 叢集狀態演變

### 3.1 正常狀態（測試前）
```
Nodes: 3
Node ID: 0x00000001 (172.19.0.171) - local
Node ID: 0x00000002 (172.19.0.172) - pve02
Node ID: 0x00000003 (172.19.0.173) - pve03
Quorate: Yes
```

### 3.2 隔離後狀態（測試中）
```
Nodes: 2
Node ID: 0x00000002 (172.19.0.172) - 被隔離但仍嘗試通訊
Node ID: 0x00000003 (172.19.0.173) - local
Quorate: Yes (2/3 仍滿足 Quorum)
```

### 3.3 最終狀態（測試後）
```
Nodes: 3 (pve02 重開機後重新加入)
VM 105 位置: sd-sandbox-pve01 (172.23.0.171)
HA 狀態: vm:105 (sd-sandbox-pve01, started) - 已完成 Failover
```

---

## 4. 關鍵日誌分析

### 4.1 Corosync 叢集成員重組
```
May 15 17:43:16 sd-sandbox-pve02 corosync[2736]:   [QUORUM] Sync members[2]: 2 3
May 15 17:43:16 sd-sandbox-pve02 corosync[2736]:   [TOTEM ] A new membership (2.77e) was formed. Members
```
**解讀**: Corosync 檢測到成員變化，開始重組，形成只含 Node 2 和 Node 3 的新 membership。

### 4.2 pmxcfs 同步失敗
```
May 15 17:43:17 sd-sandbox-pve02 pmxcfs[1892]: [status] notice: cpg_send_message retry 80
May 15 17:43:19 sd-sandbox-pve02 pmxcfs[1892]: [status] crit: cpg_send_message failed: CS_ERR_TRY_AGAIN
```
**解讀**: pmxcfs（叢集配置文件系統）持續嘗試與 Node 1 (172.23.0.171) 同步但失敗，因為 Corosync 無法轉發訊息到被隔離的節點。

### 4.3 HA CRM 狀態變更
```
May 15 17:43:33 sd-sandbox-pve02 pve-ha-crm[3431]: status change wait_for_quorum => slave
```
**解讀**: HA CRM 檢測到節點失去 Quorum（或者與隔離狀態相關），從 wait_for_quorum 進入 slave 模式。

### 4.4 Watchdog 觸發（關鍵事件）
```
May 15 17:43:34 sd-sandbox-pve02 watchdog-mux[1651]: client watchdog expired - disable watchdog updates
May 15 17:43:34 sd-sandbox-pve02 watchdog-mux[1651]: exit watchdog-mux with active connections
```
**解讀**: watchdog-mux 服務監控的客戶端進程（如 pmxcfs）在 timeout 內無回應，触发保護機制。

### 4.5 系統重開機
```
May 15 17:43:35 sd-sandbox-pve02 kernel: watchdog: watchdog0: watchdog did not stop!
May 15 17:43:43 sd-sandbox-pve02 systemd[1]: watchdog-mux.service: Deactivated successfully.
```
**解讀**: Watchdog 通知 kernel 重開機，系統開始優雅關機流程後重啟。

---

## 5. Watchdog 機制說明

### 5.1 什麼是 watchdog-mux？
`watchdog-mux` 是 Proxmox 的看門狗服務，負責監控叢集中關鍵進程的運行狀態：

- **監控的進程**：`pmxcfs`, `corosync`, `pve-ha-crm`, `pve-ha-lrm` 等
- **運作方式**：這些進程定期向 watchdog-mux 發送 heartbeat
- **超時行為**：若在設定時間內未收到 heartbeat，視為進程卡死，觸發重開機

### 5.2 為何 pmxcfs 會被誤判為卡死？
正常情況下，pmxcfs 應該：
1. 處理本地請求
2. 透過 Corosync 與其他節點同步
3. 持續回應 watchdog-mux 的心跳

在網路隔離的情況下：
1. pmxcfs 嘗試與隔離的節點通訊但不斷失敗
2. pmxcfs 可能進入「忙碌等待」狀態，不斷重試而無法處理其他事務
3. 雖然 pmxcfs 進程本身仍在運行，但無法及時回應 watchdog-mux 的心跳檢查
4. Watchdog 判定進程已死，觸發重開機

### 5.3 Watchdog timeout 設定
```bash
# 查看當前 watchdog-mux 設定
systemctl show watchdog-mux

# 常見的 timeout 設定
WatchdogSec=30s        # 30 秒無回應則觸發
```

---

## 6. 根本原因分析

### 6.1 測試設計問題

我們的 `test-ha-dual-ring` 測試使用 **iptables 模擬網路隔離**：

```bash
# 在三個節點同時執行
iptables -A INPUT -s 172.19.0.172 -j DROP   # 封鎖 ring0
iptables -A INPUT -s 10.23.0.172 -j DROP    # 封鎖 ring1
```

**問題點**：
1. **不真實的隔離方式**：iptables 只阻擋特定流量，網卡本身仍 up
2. **Corosync 仍嘗試通訊**：會不斷重試直到 timeout
3. **pmxcfs 進入重試迴圈**：無法處理正常請求
4. **Watchdog 判定進程卡死**：因為 heartbeat 中斷

### 6.2 真實網路中斷的行為
在真實的交換機斷連場景中：
1. 網卡 link 立即變 down
2. Bonding 立即檢測到故障並切換
3. Corosync 快速感知並重組
4. 進程不會陷入長時間重試迴圈

### 6.3 為何 HA Failover 仍然成功？
```
VM 105 從 sd-sandbox-pve02 遷移到 sd-sandbox-pve01
```
這個結果證明：
- HA 機制本身運作正常
- 節點被隔離的時間足夠長，讓 HA CRM 判定需要 failover
- Failover 過程已完成後，pve02 才被 watchdog 重開機

---

## 7. 影響評估

### 7.1 正面影響
- ✅ 成功驗證 HA 功能正常
- ✅ VM 105 正確 failover 到 healthy 節點
- ✅ 證明 Corosync 雙 ring 隔離確實會觸發 HA
- ✅ 叢集其他節點不受影響

### 7.2 負面影響
- ❌ pve02 被非預期重開機
- ❌ 測試環境中斷
- ❌ 需要等待節點恢復
- ❌ 可能中斷該節點上運行的其他服務

### 7.3 安全性評估
- ⚠️ 這不是安全性漏洞
- ⚠️ 這是保護機制的預期行為
- ⚠️ 在生產環境中，若發生真正的網路故障，同樣會觸發 watchdog

---

## 8. 如何區分不同類型的重開機

### 8.1 Watchdog 重開機
```
特徵:
- syslog 包含 "watchdog-mux: client watchdog expired"
- 有 "watchdog did not stop!" 訊息
- 重開機前有大量 "cpg_send_message failed" 或重試日誌
- uptime 通常在幾分鐘內（快速重啟）
- dmesg 顯示正常的開機流程，無 kernel panic
```

### 8.2 Kernel Panic
```
特徵:
- syslog 包含 "Kernel panic - not syncing"
- dmesg 包含 oops/panic stack trace
- 通常無規律的重開機模式
- 可能伴隨硬體錯誤訊息
```

### 8.3 人為重開機/關機
```
特徵:
- 有 "systemd-logind" 或 "shutdown" 相關日誌
- 無 watchdog 相關訊息
- 有明確的 shutdown 命令來源
```

### 8.4 驗證腳本
```bash
# 列出所有開機記錄
journalctl --list-boots

# 查看上次開機的日誌（確認是否為 watchdog）
journalctl -b -1 | grep -E 'watchdog|reboot|crash|panic'

# 查看開機時的 dmesg（確認是否為正常開機）
dmesg | grep -iE 'kernel|booting|proxmox' | head -20

# 檢查上一次關機前的最後訊息
journalctl -b -1 --no-pager | tail -50
```

---

## 9. 防範措施

### 9.1 方案一：縮短隔離時間（推薦）
將 `test-ha-dual-ring` 的隔離等待時間從 15 秒減少到 **5-8 秒**。

**優點**：
- 足夠觸發 HA 判定
- 低於 watchdog timeout
- 不影响测试的验证目的

**修改方式**：
```bash
# 修改 Makefile 中的等待時間
- @sleep 15
+ @sleep 6
```

### 9.2 方案二：測試前停用 Watchdog（僅測試環境）
```bash
# 在所有測試節點上執行
systemctl stop watchdog-mux

# 測試完成後恢復
systemctl start watchdog-mux
```

**警告**：
- ⚠️ 這會禁用 Proxmox 的保護機制
- ⚠️ **嚴禁用於生產環境**
- ⚠️ 只適用於隔離的測試環境

### 9.3 方案三：增加 Watchdog Timeout
```bash
# 查看當前設定
systemctl show watchdog-mux | grep WatchdogSec

# 建立 override 設定
mkdir -p /etc/systemd/system/watchdog-mux.service.d/
cat > /etc/systemd/system/watchdog-mux.service.d/override.conf << EOF
[Service]
WatchdogSec=120
EOF

# 重新載入設定
systemctl daemon-reload
systemctl restart watchdog-mux
```

**優點**：
- 不影響保護機制
- 給予足夠時間完成 HA 判定

**缺點**：
- 若真正發生故障，節點會延遲重開機
- 生產環境不建議修改預設值

### 9.4 方案四：使用交換機層級隔離（最接近真實場景）
使用交換機的以下功能：
- **BPDU Guard**：模擬交換機埠 err-disable
- **Port Channel Shutdown**：關閉 LACP port-channel
- **SPAN/RSPAN**：監控流量但不阻斷

**優點**：
- 更真實的網路故障模擬
- 網卡 link 會真正變 down
- 會觸發正確的 bond failover 行為

**缺點**：
- 需要交換機管理權限
- 需要實體操作交換機

### 9.5 方案五：自動化 Watchdog 檢測與暫停
在測試腳本中加入 watchdog 檢測邏輯：

```bash
# 在測試前檢測並暫停 watchdog（僅測試環境）
disable_watchdog() {
    echo "停用 watchdog-mux（測試環境）..."
    systemctl stop watchdog-mux
}

# 在測試後恢復 watchdog
enable_watchdog() {
    echo "恢復 watchdog-mux..."
    systemctl start watchdog-mux
}

# 在 cleanup 中確保 watchdog 恢復
cleanup() {
    enable_watchdog
    iptables -F
    iptables -P INPUT ACCEPT
    ip link set up nic2 nic3 nic4 nic5
}
```

---

## 10. 修復後的測試驗證

### 10.1 縮短等待時間後的預期行為
```
| 階段 | 耗時 | 預期結果 |
|------|------|----------|
| 故障注入 | 0s | iptables 規則加入 |
| Corosync 檢測 | ~3s | 叢集成員重組 |
| HA 判定 | ~2s | 開始 failover VM 105 |
| 隔離解除 | 6s | 移除 iptables 規則 |
| 恢復觀察 | +10s | 確認 VM 已遷移 |
| 最終狀態 | ~20s | pve02 正常運行 |
```

### 10.2 驗證項目清單
- [ ] pve02 在測試期間保持運行（未被 watchdog 重開機）
- [ ] VM 105 成功從 pve02 遷移到其他節點
- [ ] Corosync 成員正確重組
- [ ] 網路隔離解除後，pve02 正常加入叢集
- [ ] HA 狀態顯示 vm:105 在新節點上運行

---

## 11. 環境清理指令

若測試後環境異常，執行以下清理：

```bash
# 在所有節點執行
# 1. 清理 iptables
iptables -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT

# 2. 恢復網卡
ip link set up nic2 nic3 nic4 nic5

# 3. 確認叢集狀態
pvecm status
ha-manager status

# 4. 若 watchdog 異常，檢查並重啟
systemctl status watchdog-mux
systemctl restart watchdog-mux

# 5. 驗證 VM 狀態
qm list
```

---

## 12. 結論

### 12.1 事件定性
這是一個**測試方法設計問題**，而非系統故障：

1. **Watchdog 行為是正確的**：保護機制正常運作
2. **HA 功能是正常的**：成功觸發了 failover
3. **問題在測試方法**：iptables 隔離不夠乾淨

### 12.2 關鍵教訓
1. **使用真實的網路故障模擬**：盡量使用交換機層級隔離
2. **控制隔離時間**：避免超過 watchdog timeout
3. **理解 Proxmox 保護機制**：在設計測試時考慮 watchdog 行為
4. **隔離環境測試**：避免在生產環境執行破壞性測試

### 12.3 後續行動
- [ ] 修改 `test-ha-dual-ring` 將等待時間從 15 秒改為 6 秒
- [ ] 在測試文件中添加 watchdog timeout 警告
- [ ] 考慮添加可選的 watchdog 停用機制（僅測試環境）
- [ ] 評估交換機層級隔離的可行性

---

## 13. 附錄：相關日誌檔案

### A. 完整的時間序列日誌
```
17:42:24 - iptables 規則加入
17:42:39 - Corosync 開始重組
17:43:16 - 新 membership 形成 (2 節點)
17:43:17 - pmxcfs 第一次重試
17:43:19 - pmxcfs 第一次 crit 錯誤
17:43:33 - HA CRM 進入 slave 模式
17:43:34 - watchdog-mux 報告 client watchdog 過期
17:43:35 - watchdog-mux 準備退出
17:43:35 - kernel 開始重開機流程
17:43:43 - watchdog-mux 完全停止
17:47:15 - 系統重開機完成，服務上線
```

### B. 關鍵程序狀態
```
正常運行時:
pmxcfs     -> 定期心跳 -> watchdog-mux
corosync   -> 正常通訊 -> 其他節點
pve-ha-crm -> 監控服務 -> 管理 HA

網路隔離時:
pmxcfs     -> 不斷重試 -> cpg_send_message failed
corosync   -> 叢集成員重組 -> 2 節點運作
pve-ha-crm -> wait_for_quorum -> slave 模式
watchdog-mux -> 等待心跳超時 -> 觸發重開機
```

---

*文件建立時間: 2026-05-15 17:50 CST*
*最後更新: 2026-05-15 17:50 CST*
*作者: PVE Testing Team*