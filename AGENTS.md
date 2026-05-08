# AGENTS.md - PVE 9.1 測試專案

## 專案概述

Proxmox VE v9.1 生產環境可行性驗證測試，測試期間 2026/01/20 - 2026/09/30，共 **41 項測試**。

| 項目 | 內容 |
|------|--------|
| 測試標的 | Proxmox VE v9.1 |
| 主測單位 | 系統服務處 平台服務部 虛擬化架構課 |
| 協測單位 | 系統服務處 基礎架構部 網路架構課 |
| 主測同仁 | Tony / Andy |
| 假想敵對 | VMware VCF 8.0u3 |

---

## 環境資訊

### 測試節點

| 節點名稱 | 管理 IP (VLAN 19) | 儲存 IP | iDRAC IP | 備註 |
|----------|-----------------|---------|----------|------|
| sandbox-pve01 | 172.19.0.171 | 10.23.0.171 | 10.0.4.91 | 本機 |
| sandbox-pve02 | 172.19.0.172 | 10.23.0.172 | 10.0.4.92 | - |
| sandbox-pve03 | 172.19.0.173 | 10.23.0.173 | 10.0.4.93 | - |

### 叢集資訊

```
Cluster Name: sandbox-cluster
Config Version: 3
Transport: knet
Quorum: 3 節點，需 2 票
```

### 網路架構 (本機 sandbox-pve01)

| 介面 | 類型 | 成員 | IP 位址 | 用途 |
|------|------|------|---------|------|
| bond0 | LACP 802.3ad | nic2 + nic3 (10G) | - | 管理網路 |
| bond2 | LACP 802.3ad | nic4 + nic5 (10G) | 10.23.0.171/24 | 儲存網路 |
| vmbr0 | Bridge | bond0 | - | VM 橋接器 |
| vmbr0.19 | VLAN | vmbr0 | 172.19.0.171/16 | 管理 VLAN 19 |
| tap100i0~106i0 | VM tap | - | - | VM 虛擬介面 |

**LACP 關鍵配置**:
- 傳輸哈希策略: `layer3+4` (伺服器端) / `L3_L4` (交換機端)
- 交換機: Extreme X670v
- **重要發現**: 單一目標 IP 測試僅達 47.3% (9.15 Gbps)，同時向兩個不同目標 IP 可達 **98.3% (19.66 Gbps)**

### 儲存配置

| 儲存 ID | 類型 | 伺服器 | 掛載點 |
|----------|------|--------|----------|
| local | dir | localhost | /var/lib/vz |
| local-lvm | lvmthin | localhost | pve/data |
| pve2650-nodeA-vol1 | nfs | 10.23.0.12 | /mnt/pve/pve2650-nodeA-vol1 |
| pve2650-nodeA-vol2 | nfs | 10.23.0.12 | /mnt/pve/pve2650-nodeA-vol2 |
| pve2650-nodeB-vol1 | nfs | 10.23.0.13 | /mnt/pve/pve2650-nodeB-vol1 |
| pve2650-nodeB-vol2 | nfs | 10.23.0.13 | /mnt/pve/pve2650-nodeB-vol2 |

**NFS 掛載選項**: `rw,bg,soft,noatime,nodiratime,proto=tcp,timeo=600,rsize=262144,wsize=262144,nointr,vers=3`

### 磁碟效能結論

**推薦配置: RAID6 + xfs** (加權評分 0.9286 最高)
- 延遲最低 (83.37 ms)
- 利用率最佳 (61.09%，落在 50-70% 理想區間)
- RAID6 提供 2 磁碟容錯，可用容量 75% (N-2)

| 排名 | RAID | FS | 加權分數 | 平均延遲 | 平均 IOPS |
|------|------|----|----------|----------|-----------|
| 🥇 | RAID6 | xfs | **0.9286** | 83.37 ms | 81k |
| 🥈 | RAID5 | xfs | 0.8384 | 85.59 ms | 78k |
| 🥉 | RAID6 | ext4 | 0.7032 | 135.75 ms | 71k |

---

## 測試項目總表 (41 項)

### 1. 環境建置測試 (7 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 測試員 |
|------|----------|----------|----------|--------|
| 1.1 | TC-ENV-01 | 軟體取得 | 管道便利性 | Andy |
| 1.2 | TC-ENV-02 | 虛擬層單機安裝 | 巢狀安裝測試 | Andy |
| 1.3 | TC-ENV-03 | 虛擬層叢集安裝 | 叢集網路部署 | Andy |
| 1.4 | TC-ENV-04 | 虛擬層叢集設定 | 叢集管理設定 | Andy |
| 1.5 | TC-ENV-05 | 實體機單機安裝 | 硬體相容性測試 | Tony |
| 1.6 | TC-ENV-06 | 實體機叢集安裝 | 實體叢集部署 | Tony |
| 1.7 | TC-ENV-07 | 實體機叢集設定 | 實體環境配置 | Tony |

### 2. 功能測試 (3 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 測試員 |
|------|----------|----------|----------|--------|
| 2.1 | TC-FUNC-01 | ext4/xfs on LVM-thin | 效能差異 | Andy |
| 2.2 | TC-FUNC-02 | ext4/xfs on LVM-thin | HA 差異 | Andy |
| 2.3 | TC-FUNC-03 | ext4/xfs on LVM-thin | 修復差異 | Andy |
| 2.4 | TC-FUNC-06 | 管理網路 LACP | 網路功能影響 | Tony |
| 2.5 | TC-FUNC-07 | 服務網路 LACP | 業務網路影響 | Tony |

### 3. 系統穩定性測試 (4 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 方法 | 優先序 |
|------|----------|----------|----------|------|--------|
| 3.1 | TC-SYS-01 | Kernel 版本穩定性驗證 | Kernel 6.8 freeze | 48h stress test | P1 |
| 3.2 | TC-SYS-02 | Kernel 降級驗證 | 降級至 6.5 LTS | 切換 kernel 重啟 | P2 |
| 3.3 | TC-SYS-03 | CPU C-State 穩定性 | max_cstate=1 效果 | 修改 GRUB 參數 | P2 |
| 3.4 | TC-SYS-04 | 記憶體錯誤檢測 | ECC/非ECC 穩定度 | mcelog, edac-util | P2 |

### 4. HA 機制驗證測試 (4 項) - **高風險優先**

| 項次 | 代號 | 測試項目 | 驗證項目 | 方法 | 優先序 |
|------|----------|----------|----------|------|--------|
| 3.5 | TC-HA-01 | Corosync 敏感度測試 | 網路延遲導致 HA 誤觸發 | tc 注入 500ms 延遲 | P1 |
| 3.6 | TC-HA-02 | LACP 單鏈路故障 HA 觸發 | 非聚合網路斷線觸發 HA | ip link set down | **P1** |
| 3.7 | TC-HA-03 | Corosync Split-Brain 模擬 | 節點隔離後的 quorum 行為 | iptables DROP | **P1** |
| 3.8 | TC-HA-04 | HA Manager Lock 遷移 | 服務重啟後的資源鎖定 | systemctl restart | P2 |

### 5. 儲存風險測試 (7 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 優先序 |
|------|----------|----------|----------|--------|
| 3.9 | TC-ST-01 | LVM-Thin RAW 效能測試 | RAW 磁碟 I/O 基準 | P2 |
| 3.10 | TC-ST-02 | NetApp NFS QCOW2 效能測試 | QCOW2 效能損耗 | P2 |
| 3.11 | TC-ST-03 | LVM-Thin Pool 空間耗盡 | Metadata 空間對 I/O 影響 | **P1** |
| 3.12 | TC-ST-04 | QCOW2 vs RAW 效能差異 | 儲存格式對 I/O 效能影響 | P2 |
| 3.13 | TC-ST-05 | NFS Snapshot 作業時間 | NFS 環境 QCOW2 Snapshot 延遲 | P2 |
| 3.14 | TC-ST-06 | LVM-Thin Snapshot 效能影響 | Snapshot 數量對 I/O 影響 | P2 |
| 3.15 | TC-ST-07 | RAID 6 雙碟故障容錯 | 硬碟雙故障後的資料完整性 | P2 |

### 6. 網路故障測試 (3 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 優先序 |
|------|----------|----------|----------|--------|
| 3.16 | TC-NW-01 | LACP 負載平衡與頻寬測試 | Bond 吞吐量驗證 | P2 |
| 3.17 | TC-NW-02 | LACP 故障轉移時間 | Bond 成員故障後的切換時間 | P2 |
| 3.18 | TC-NW-03 | 管理網路與 Corosync 網路分離 | 網路分流的穩定性 | P2 |

### 7. Backup/Replication 測試 (5 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 優先序 |
|------|----------|----------|----------|--------|
| 3.19 | TC-BR-01 | Proxmox Backup Server (PBS) 整合 | PBS 與 PVE 9.1 整合度 | P2 |
| 3.20 | TC-BR-02 | VM 增量備份驗證 | 增量備份機制正確性 | P2 |
| 3.21 | TC-BR-03 | VM 備份還原驗證 | 備份還原完整性 | P2 |
| 3.22 | TC-BR-04 | VM Replication 跨節點複製 | ZFS/LVM-Thin 複製機制 | P2 |
| 3.23 | TC-BR-05 | 備份工作排程驗證 | 自動化備份排程正確性 | P2 |

### 8. LVM-Thin Snapshot 專項測試 (4 項)

> **注意**: 本區域僅針對 LVM-Thin 格式的 VM

| 項次 | 代號 | 測試項目 | 驗證項目 | 優先序 |
|------|----------|----------|----------|--------|
| 3.24 | TC-LVMSP-01 | LVM-Thin Snapshot 建立 | Snapshot 建立速度與可行性 | P2 |
| 3.25 | TC-LVMSP-02 | LVM-Thin Snapshot 還原 | Snapshot 還原正確性 | P2 |
| 3.26 | TC-LVMSP-03 | LVM-Thin Snapshot 刪除 | Snapshot 刪除對效能影響 | P2 |
| 3.27 | TC-LVMSP-04 | LVM-Thin Snapshot 數量上限 | Snapshot 數量對效能影響 | P2 |

### 9. 版本升級測試 (4 項)

| 項次 | 代號 | 測試項目 | 驗證項目 | 優先序 |
|------|----------|----------|----------|--------|
| 3.28 | TC-UPG-01 | PVE 8 → 9 離線升級 | 離線升級流程正確性 | P2 |
| 3.29 | TC-UPG-02 | 升級後服務啟動驗證 | 核心服務正常運行 | P2 |
| 3.30 | TC-UPG-03 | 升級後 VM 運行驗證 | VM 不受升級影響 | P2 |
| 3.31 | TC-UPG-04 | 升級回滾演練 | 升級失敗的復原能力 | P2 |

---

## 已知高風險問題 (P1)

| 風險 ID | 風險描述 | 發生機率 | 影響程度 | 相關測試 |
|---------|----------|----------|----------|----------|
| R-001 | Kernel 6.8 Freeze 導致系統無回應 | 中 | 高 | TC-SYS-01 |
| R-003 | LVM-Thin Pool 空間耗盡 | 中 | 高 | TC-ST-03 |
| R-007 | LACP 單鏈路故障觸發 HA 切換 | 高 | 高 | TC-HA-02 |
| R-009 | Corosync Split-Brain 導致資料不一致 | 中 | 高 | TC-HA-03 |
| R-010 | HA 過於敏感導致非預期 VM 重啟 | 高 | 高 | TC-HA-01 |

### HA 敏感度調整建議

```bash
# 查看當前設定
corosync-cmapctl | grep -E 'deadtime|token'

# 建議參數 (降低敏感度)
# /etc/corosync/corosync.conf
totem {
    deadtime: 10      # 預設 1s，建議提升
    token: 5000       # 預設 1000ms，建議提升
}
```

---

## 常用測試指令

### 網路測試 (LACP/Bond)

```bash
# 查看 bond 狀態
cat /proc/net/bonding/bond0
cat /proc/net/bonding/bond2

# 查看橋接狀態
brctl show

# 查看叢集狀態
pvecm status

# LACP 頻寬測試 (關鍵腳本)
# 單一目標 IP (僅達 47.3%)
iperf3 -c 172.19.0.173 -t 10 -P 8

# 多目標 IP (可達 98.3%!)
iperf3 -c 172.19.0.172 -t 10 -P 4 &
iperf3 -c 172.19.0.173 -t 10 -P 4 &
wait

# 監控流量分布
watch -n 1 'ip -s link show nic2 | grep TX; ip -s link show nic3 | grep TX'
```

### 系統穩定性測試

```bash
# Kernel freeze 測試
vmstat 1
dmesg -w

# 記憶體測試
mcelog --client
edac-util -v
memtester 4096M 1

# CPU C-State 測試
# 修改 /etc/default/grub
# GRUB_CMDLINE_LINUX="processor.max_cstate=1"
update-grub && reboot
```

### 儲存測試

```bash
# LVM-Thin 監控
lvs -o lv_name,data_percent,metadata_percent pve

# 儲存狀態
pvesm status

# FIO 測試 (參考 本地磁碟效能測試分析報告v2.0.md)
# RAID6 + xfs 為推薦配置

# NFS 掛載選項檢查
mount | grep nfs
```

### HA 測試

```bash
# HA 狀態
ha-manager status

# Corosync 成員
corosync-cmapctl | grep members

# 模擬網路隔離
iptables -A INPUT -s <node_ip> -j DROP

# 模擬單鏈路故障
ip link set down nic2  # bond0 成員
ip link set up nic2
```

---

## 測試報告產出

完成所有測試後，需產出以下報告：

| 報告名稱 | 檔案 | 說明 |
|----------|------|------|
| 測試初步報告 | 測試初步報告_Preliminary_Report.md | 優缺點、已知問題庫 |
| 測試計畫書 | PVE測試計劃書-摘要與目標.md | 測試目標與範圍 |
| 測試計畫表 | 測試計畫表_Test_Plan_Matrices.md | 41 項測試詳細計畫 |
| 風險評估矩陣 | PVE風險評估矩陣_Risk_Assessment_Matrix.md | 13 項風險 SOP |
| 環境說明 | 環境說明_Environment_Setup.md | 硬體與網路架構 |
| LACP 測試 | LACP負載平衡與帶寬測試.md | 20Gbps 聚合驗證 |
| 本地磁碟測試 | 本地磁碟效能測試分析報告v2.0.md | RAID 效能分析 |
| iperf 測試 | iperf/*.md | 網路效能壓力測試 |
| 系統環境資訊 | env/05081359-pve-env.md | 本機系統配置快照 |

---

## 專案文檔索引

```
/root/PVE-Testing/
├── AGENTS.md                                    (本檔案)
├── 環境說明_Environment_Setup.md               (硬體規格、網路規劃)
├── PVE測試計劃書-摘要與目標.md               (測試目標、範圍)
├── PVE測試計劃書-測試計劃表補充案.md         (28 項補充測試)
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

---

## 執行優先序建議

| 階段 | 測試類別 | 天數 | 優先測試項目 |
|------|----------|------|----------|
| Phase 1 | 環境建置 | 15 天 | TC-ENV-05 ~ TC-ENV-07 |
| Phase 2 | 功能測試 | 30 天 | TC-FUNC-01 ~ TC-FUNC-07 |
| Phase 3 | 系統穩定性 | 15 天 | **TC-SYS-01** (Kernel freeze) |
| Phase 4 | HA 機制 | 15 天 | **TC-HA-02, TC-HA-03** (高風險) |
| Phase 5 | 儲存風險 | 15 天 | **TC-ST-03** (LVM-Thin 耗盡) |
| Phase 6 | 網路故障 | 15 天 | TC-NW-01 ~ TC-NW-03 |
| Phase 7 | Backup/Replication | 5 天 | TC-BR-01 ~ TC-BR-05 |
| Phase 8 | LVM-Thin Snapshot | 3 天 | TC-LVMSP-01 ~ TC-LVMSP-04 |
| Phase 9 | 版本升級 | 5 天 | TC-UPG-01 ~ TC-UPG-04 |

---

## 重要提醒

1. **高風險測試前務必建立快照**: NetApp FAS2650 快照或 VM 快照
2. **iDRAC/IPMI 備用連線**: Kernel freeze 測試必備
3. **Corosync 配置備份**: `/etc/corosync/corosync.conf` 和 `/etc/pve`
4. **LACP 測試關鍵**: 單一目標 IP 無法達成 20Gbps，需同時向多個 IP 發送
5. **RAID 配置**: 新環境建議 RAID6 + xfs (效能與可靠性最佳平衡)

---

**最後更新**: 2026-05-08  
**AGENTS.md 版本**: 1.0
