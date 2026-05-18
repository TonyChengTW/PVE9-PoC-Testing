# AGENTS.md - PVE-Testing

This repository contains test plans and automation for Proxmox VE (PVE) network performance validation.

## Core Infrastructure
- **Local Host**: `172.23.0.171` (nic0, Debug/AI Agent 用)
- **Target Host 1**: `172.23.0.173` (nic0, 與本機相同配置)
- **Target Host 2**: `172.23.0.172` (nic0, 與本機相同配置)
- **Cluster 網段**: `172.19.0.x` (LACP/bond0/bond1 故障轉移測試區)

## SSH Access
- `ssh root@172.23.0.172` - 可連線
- `ssh root@172.23.0.173` - 可連線
- 驗證網卡狀態: `ssh root@172.23.0.173 "ip a show nic0"`

### LACP/Bond 斷線測試期間的通訊
**重要**：nic0 (172.23.0.x) **不參與** PVE Cluster 或 LACP/bond0/bond1 故障轉移，純粹用於 Debug 與 AI Agent 溝通。

LACP/bond0/bond1 斷線測試在集群網段 (172.19.0.x) 進行。測試期間，所有節點仍可透過 nic0 (172.23.0.x) 正常溝通，可透過 SSH 執行遠端指令查看 Cluster 節點狀況。

## Essential Commands
- **Basic Network Stress Test** (to 172.23.0.173):
  `bash /root/PVE-Testing/iperf/iperf-test.sh`
- **20Gbps Validation** (to 172.23.0.173):
  `bash /root/PVE-Testing/iperf/iperf20g-test.sh`

## Testing Framework (Makefile)

全面的自動化測試框架，支援 TC-HA-02 (HA 觸發) 和 TC-NW-02 (故障轉移) 測試規格。

### 快速開始
```bash
cd /root/PVE-Testing
make help                    # 查看所有可用目標
make health-check            # 執行 9 項健康檢查
make fully-test              # 執行完整測試流程
make report                  # 生成 Markdown 報告
```

### 網路安全要求 (重要)
**nic0 (172.23.0.x) 嚴禁中斷** - 此網路用於 Debug/AI Agent 溝通，測試期間不可變更任何配置。

**iptables INPUT Policy 必須保持 ACCEPT**：
- `iptables -F` 會清除所有規則，若此時預設 Policy 為 DENY，會導致 SSH 連線中斷
- 所有測試腳本在執行 `iptables -F` 前會先執行 `iptables -P INPUT ACCEPT`
- 建議在測試前確認：`iptables -L -n` 查看 Policy 狀態

**Corosync Ring 隔離測試**：
- `test-ha-ring0-isolate` 和 `test-ha-dual-ring` 使用 iptables 模擬網路隔離
- 這些測試需要在 INPUT Policy 為 ACCEPT 的狀態下執行
- 生產環境建議使用交換機埠隔離而非 host 層級 iptables

### Watchdog 導致節點重開機問題 (重要)

**問題描述**：
執行 `test-ha-dual-ring`（Corosync 雙 ring 隔離）時，若隔離時間超過閾值，節點會被 watchdog 機制重開機。這不是 kernel panic 或硬體故障，是 Proxmox 的保護機制。

**觀測到的事件時間線**（2026-05-15 17:43）：

| 時間 | 事件 |
|------|------|
| 17:43:16 | Corosync 開始重組，形成 2 節點成員 |
| 17:43:17-43:35 | `pmxcfs` 服務不斷重試訊息發送（cpg_send_message）均失敗 |
| 17:43:24 | iperf3 服務重啟計數已達 179 次 |
| 17:43:34 | `watchdog-mux` 報告 client watchdog 過期 |
| 17:43:35 | watchdog 進程退出，journal 同步完成 |
| 17:43:43 | 系統被 watchdog 機制重開機 |

**日誌關鍵片段**：
```
May 15 17:43:29 sd-sandbox-pve02 pmxcfs[1892]: [status] crit: cpg_send_message failed: CS_ERR_TRY_AGAIN
May 15 17:43:33 sd-sandbox-pve02 pve-ha-crm[3431]: status change wait_for_quorum => slave
May 15 17:43:34 sd-sandbox-pve02 watchdog-mux[1651]: client watchdog expired - disable watchdog updates
May 15 17:43:34 sd-sandbox-pve02 watchdog-mux[1651]: exit watchdog-mux with active connections
May 15 17:43:35 sd-sandbox-pve02 kernel: watchdog: watchdog0: watchdog did not stop!
May 15 17:43:43 sd-sandbox-pve02 systemd[1]: watchdog-mux.service: Deactivated successfully.
```

**根本原因**：
1. `test-ha-dual-ring` 在本地和遠端同時加 iptables 規則，封鎖 172.19.0.172 和 10.23.0.172
2. 這導致 Corosync 完全無法通訊，叢集成員只能維持 2 節點
3. `pmxcfs`（叢集配置文件系統）持續嘗試同步但失敗
4. Proxmox 的 watchdog-mux 服務監控關鍵進程（pmxcfs, corosync 等）
5. 當進程在設定時間內無回應，watchdog 觸發系統重開機

**影響範圍**：
- 受影響節點：172.23.0.172（sd-sandbox-pve02）
- 叢集其他節點不受影響，仍維持運作
- **正向觀察**：VM 105 確實因 HA 機制Failover 到 172.23.0.171（pve01），證明 HA 功能正常

**防範措施**：

1. **縮短隔離時間**
   - 將 `test-ha-dual-ring` 的隔離等待時間從 15 秒減少到 **5-8 秒**
   - 足夠觸發 HA 判定但不超過 watchdog timeout

2. **測試前停用 watchdog（不建議在生產環境）**
   ```bash
   systemctl stop watchdog-mux
   ```

3. **增加 watchdog timeout**
   ```bash
   # 查看當前設定
   systemctl show watchdog-mux
   # 或修改 /etc/systemd/system/watchdog-mux.service.d/override.conf
   ```

4. **改用交換機層級隔離**
   - 避免在 host 層級使用 iptables 模擬網路隔離
   - 使用交換機的 SPAN/RSPAN 或 BPDU Guard 功能更接近真實故障場景

**如何區分 Watchdog 重開機 vs Kernel Panic**：

| 特徵 | Watchdog 重開機 | Kernel Panic |
|------|----------------|--------------|
| syslog 最後訊息 | `watchdog-mux: client watchdog expired` | `Kernel panic - not syncing` |
| uptime | 通常幾分鐘內（因為迅速重啟） | 可能是任何時間 |
| dmesg | 正常開機流程（bonding 初始化等） | 會有 oops/panic stack trace |
| 重開機頻率 | 每次觸發條件相同都會 | 通常只一次（除非持續問題）|

**驗證方法**：
```bash
# 列出開機記錄
journalctl --list-boots

# 查看上次開機的日誌（確認是否為 watchdog）
journalctl -b -1 | grep -E 'watchdog|reboot'

# 查看叢集狀態
pvecm status
ha-manager status
```

### 健康檢查 (9 項)
```bash
make health-check
```
檢查項目：
1. Cluster Quorate 狀態
2. HA Manager 運行狀態
3. VM 105 運行狀態
4. VM 105 HA 管理狀態
5. bond0 狀態 (nic2+nic3)
6. bond2 狀態 (nic4+nic5)
7. SSH 連線 (172.23.0.172)
8. SSH 連線 (172.23.0.173)
9. Corosync 成員狀態

### HA 測試 (TC-HA-02)
```bash
make test-ha-nic2           # bond0 nic2 故障 - 不應觸發 HA
make test-ha-nic3           # bond0 nic3 故障 - 不應觸發 HA
make test-ha-bond0-dual     # bond0 雙鏈路故障 - Quorate 應維持
make test-ha-ring0-isolate  # Corosync ring0 隔離 - Quorate 應維持
make test-ha-dual-ring      # Corosync 雙 ring 隔離 - **應觸發 HA**
```

### 頻寬測試 (TC-NW-02)
```bash
make test-bw-bond0-ping        # bond0 ping 監控 (nic2)
make test-bw-bond0-ping-nic3   # bond0 ping 監控 (nic3)
make test-bw-nic4              # bond2 nic4 iperf3 測試
make test-bw-nic5              # bond2 nic5 iperf3 測試
make test-switch-reboot        # 60 秒中斷模擬
```

### 重置/回滾
```bash
make reset              # 恢復所有網卡 + 清理 iptables
make rollback           # 緊急回滾
make cleanup            # 清理 iperf3 程序
make force-recover      # 強制恢復 (解決卡住)
```

### 回滾到特定階段
```bash
make rollback-to-phase1   # 回滾到 Phase 1 (健康檢查)
make rollback-to-phase2   # 回滾到 Phase 2 (HA 測試)
make rollback-to-phase3   # 回滾到 Phase 3 (頻寬測試)
```

### 狀態/報告
```bash
make status              # 查看當前狀態 (JSON)
make history             # 查看測試歷史
make report              # 生成 Markdown 報告
```

### 完整測試流程
```bash
make fully-test          # 執行 TC-HA-02 + TC-NW-02 全部 10 項測試
```

### 測試矩陣

| # | 測試代碼 | 測試目標 | 預期行為 |
|---|---------|---------|---------|
| 1 | test-ha-nic2 | bond0 nic2 | 不應觸發 HA |
| 2 | test-ha-nic3 | bond0 nic3 | 不應觸發 HA |
| 3 | test-ha-bond0-dual | bond0 nic2+nic3 | Quorate 維持 |
| 4 | test-ha-ring0-isolate | 172.19.0.172 isolated | Quorate 維持 |
| 5 | test-ha-dual-ring | both rings isolated | **HA 觸發** |
| 6 | test-bw-bond0-ping | nic2 ping | <1s switch |
| 7 | test-bw-bond0-ping-nic3 | nic3 ping | <1s switch |
| 8 | test-bw-nic4 | bond2 nic4 | ~9Gbps |
| 9 | test-bw-nic5 | bond2 nic5 | ~9Gbps |
| 10 | test-switch-reboot | nic2+nic3 60s | 60s後恢復 |

### 狀態追蹤
- **狀態文件**: `~/pve-test-status.json`
- **日誌目錄**: `/tmp/pve-test-logs/`
- **報告輸出**: `~/pve-test-report-<timestamp>.md`

## Workflow & Verification
- **Execution**: Scripts run `iperf3` on the local host against targets.
- **Output**: JSON raw data is saved to timestamped directories in `$HOME`; summary Markdown reports are generated in `$HOME`.

## Key Documentation
- **Test Plans**: `docs/codimd/`
- **Test Specs**: `docs/superpowers/spec/`
- **Environment Setup**: `docs/codimd/環境說明_Environment_Setup.md`