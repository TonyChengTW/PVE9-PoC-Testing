# 測試計畫表 (Test Plan Matrices)

## 測試計畫表 (Test Plan Matrices)

### 環境建置 (Environment Deployment)

| 項次 | 測試代號  | 測試項目       | 驗證項目       | 方法                               | 結果                                                                         | 測試員 | 備註 |
| ---- | --------- | -------------- | -------------- |----------------------------------- | ---------------------------------------------------------------------------- | ------ | ---- |
| 1.1  | TC-ENV-01 | 軟體取得       | 管道便利性     | 雙管道取得並進行 checksum 驗證     | [PASS](https://codimd.104.com.tw/image/s3/key/h35xl7moqkus9i3w73r9hlmoi.png) | Andy   |      |
| 1.2  | TC-ENV-02 | 虛擬層單機安裝 | 巢狀安裝測試   | 於 VMware/PVE 叢集內安裝單機版     | [PASS](https://codimd.104.com.tw/image/s3/key/ecvgdtm8crosq9pa2hyd9pli1.png) | Andy   | 安裝簡易     |
| 1.3  | TC-ENV-03 | 虛擬層叢集安裝 | 叢集網路佈署   | 於虛擬環境內完成叢集安裝與網路配置 | [PASS](https://codimd.104.com.tw/image/s3/key/ecvgdtm8crosq9pa2hyd9pli1.png) | Andy   |      |
| 1.4  | TC-ENV-04 | 虛擬層叢集設定 | 叢集管理設定   | 完成叢集邏輯設定                   | [PASS](https://codimd.104.com.tw/image/s3/key/ecvgdtm8crosq9pa2hyd9pli1.png) | Andy   | CLI 設定簡易 |
| 1.5  | TC-ENV-05 | 實體機單機安裝 | 硬體相容性測試 | 在 **Dell R640/R750** 實施安裝     | PASS                                                                        | Tony   |      |
| 1.6  | TC-ENV-06 | 實體機叢集安裝 | 實體叢集佈署   | 在實體設備完成叢集安裝             |  PASS                                                                        | Tony   |      |
| 1.7  | TC-ENV-07 | 實體機叢集設定 | 實體環境配置   | 於實體機完成叢集參數設定           |  PASS                                                                        | Tony   |      |

### 功能測試 (Functional Tests)

| 項次 | 測試代號   | 測試項目      | 驗證項目     | 方法                                   | 結果 | 測試員 | 備註 |
| ---  | ---------- | ------------- | ------------ | -------------------------------------- | ---- | ------ | ---- |
| 2.1  | TC-FUNC-01 | ext4/xfs on LVM-thin    | 效能差異     | 比較 ext4 與 xfs 效能差異                       | 1. 分別安裝兩台 VM 各為 ext4 與 xfs，並安裝 fio軟體<br> 2. 執行 fio 隨機讀寫、循序讀寫測試 <br>3. 執行 Metadata 密集型測試 (例：創建/刪除 10 萬個小文件，計時)     | Andy    | |
| 2.2  | TC-FUNC-02 | ext4/xfs on LVM-thin    | HA差異       | 啟動 HA 是否會造成 ext4 or xfs 檔案系統毀損     | 1. 分別安裝兩台 VM 各為 ext4 與 xfs，並安裝 fio軟體<br> 2. 執行 fio 隨機讀寫、循序讀寫測試 <br> 3. 確保兩個 VM 已設定 HA 自動啟動。<br> 4. **強制關閉** 運行兩個 VM 的 PVE 節點電源。<br> 5. 觀察 VM 在其他健康節點上自動重啟。<br> 6. 登入 VM，檢查檔案系統狀態 (`mount` / `dmesg`), 預寫入數據完整性    | Andy    | |
| 2.3  | TC-FUNC-03 | ext4/xfs on LVM-thin    | 修復差異     | 無預警停機，是否會造成 ext4 or xfs 檔案系統毀損 | 1. 在 VM 中寫入測試數據並計算 MD5 hash 值。<br>2. VM 運行時，在 PVE 介面中選擇 **「停止 (Stop)」** 而不關機 (模擬突然斷電)。<br>3. VM 重新啟動後，觀察檔案系統檢查。<br>4. 手動執行 `fsck -fy /dev/vda1` (ext4) 或 `xfs_repair /dev/vda1` (xfs)。<br>5. 比較修復前後數據 MD5 hash 值。     | Andy    | |
| 2.4  | TC-FUNC-04 | ext4/xfs on LVM-thin    | 備份差異     | 備份 ext4 與 xfs 分割磁區差異                   | 1. 創建模擬 VM 並填充相同大小和類型的數據。<br>2. 在 PVE 上配置備份儲存。<br>3. 對兩個 VM 執行 `vzdump` 備份 (snapshot 模式)，記錄時間。<br>4. 將備份還原到**新的 VM**。<br>5. 啟動還原後的 VM，比較數據完整性 (MD5 hash)。     | Andy    | |
| 2.5  | TC-FUNC-05 | ext4/xfs on LVM-thin    | 還原差異     | 還原 ext4 與 xfs 分割磁區差異                   | 1. 對兩個 VM 進行一次完整備份。<br>2. **刪除原始的 VM** (模擬 VM 永久丟失)。<br>3. 從備份中，將兩個 VM **完整還原**到 PVE 叢集中的任一節點。<br>4. 啟用還原後的 VM，驗證 Guest OS 正常啟動，檢查應用服務、網路設定、數據完整性。      | Andy    |  |
| 2.6  | TC-FUNC-06 | 管理網路 LACP | 網路功能影響 | 測試開啟 LACP 與否對管理網路之影響              |      | Tony    |     |
| 2.7  | TC-FUNC-07 | 服務網路 LACP | 業務網路影響 | 測試開啟 LACP 與否對服務網路之影響              |      | Tony    |     |


---

### 系統穩定性測試 (System Stability Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.1 | TC-SYS-01 | Kernel 版本穩定性驗證 | Kernel 6.8 freeze 問題 | 長時間 stress test (48h)，監控 `vmstat 1`、`dmesg -w` |  | Tony | 需準備 iDRAC/IPMI 作為 fallback 連線 |
| 3.2 | TC-SYS-02 | Kernel 降級驗證 | 降級至 kernel 6.5 LTS 穩定性 | 切換預設 kernel，重啟後驗證 VM 正常運行 |  | Tony | 比較 6.5 vs 6.8 效能差異 |
| 3.3 | TC-SYS-03 | CPU C-State 穩定性 | `max_cstate=1` 參數效果 | 修改 GRUB 參數，長時間觀察主機穩定性 |  | Tony | 需與硬體供應商確認支援性 |
| 3.4 | TC-SYS-04 | 記憶體錯誤檢測 | ECC/非ECC 記憶體穩定度 | `mcelog`、`edac-util` 檢查記憶體錯誤 |  | Tony | 確認 Dell R640 iDRAC 日誌 |

### HA 機制驗證測試 (High Availability Mechanism Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.5 | TC-HA-01 | Corosync 敏感度測試 | 網路延遲導致 HA 誤觸發 | 使用 `tc` 注入 500ms 延遲，觀察 corosync 行為 |  | Tony | 需關閉防火牆或開啟對應 port |
| 3.6 | TC-HA-02 | LACP 單鏈路故障 HA 觸發 | 非聚合網路斷線觸發 HA | 實體拔除或 `ip link set down` 其中一條 Bond 成員 |  | Tony | 為已知敏感問題，優先測試 |
| 3.7 | TC-HA-03 | Corosync Split-Brain 模擬 | 節點隔離後的 quorum 行為 | `iptables -A INPUT -s <node_ip> -j DROP` 阻斷通訊 |  | Tony | 需準備快速恢復腳本 |
| 3.8 | TC-HA-04 | HA Manager Lock 遷移 | 服務重啟後的資源鎖定 | `systemctl restart pve-ha-crm`，檢查 `ha-manager status` |  | Tony | 需驗證 fencing 机制 |

### 儲存風險測試 (Storage Risk Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.9 | TC-ST-01 | LVM-Thin RAW 效能測試 | RAW 磁碟 I/O 基準 | FIO `rw=randrw`, `bs=4k`, `iodepth=64`, `direct=1` |  | Tony | 建立效能基準線 |
| 3.10 | TC-ST-02 | NetApp NFS QCOW2 效能測試 | QCOW2 效能損耗 | 對 NFS 上的 QCOW2 執行相同 FIO 測試 |  | Tony | 分析 Metadata 寫入影響 |
| 3.11 | TC-ST-03 | LVM-Thin Pool 空間耗盡 | Metadata 空間對 I/O 影響 | 持續寫入直到 thin pool 達 95%，觀察 I/O 行為 |  | Tony | 高風險測試，需 snapshot 保護 |
| 3.12 | TC-ST-04 | QCOW2 vs RAW 效能差異 | 儲存格式對 I/O 效能影響 | FIO 測試相同條件下 QCOW2 與 RAW 的 IOPS |  | Tony | 量化效能損耗比例 |
| 3.13 | TC-ST-05 | NFS Snapshot 作業時間 | NFS 環境 QCOW2 Snapshot 延遲 | 建立 50GB VM 的 QCOW2 snapshot，計時 |  | Tony | 已知問題：可能 > 15min |
| 3.14 | TC-ST-06 | LVM-Thin Snapshot 效能影響 | Snapshot 數量對 I/O 影響 | 建立 5 個 LVM-Thin snapshot，執行 FIO 測試 |  | Tony | 僅測試 LVM-Thin VM |
| 3.15 | TC-ST-07 | RAID 6 雙碟故障容錯 | 硬碟雙故障後的資料完整性 | 模擬 RAID 6 雙碟故障，執行 MD5 校驗 |  | Tony | 高風險，需 NetApp 快照 |

### 網路故障測試 (Network Failure Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.16 | TC-NW-01 | LACP 負載平衡與帶寬測試 | Bond 吞吐量驗證 | `iperf3 -P 10` 測試雙網卡 Bond 實際吞吐量 |  | Tony | 驗證流量均勻分佈 |
| 3.17 | TC-NW-02 | LACP 故障轉移時間 | Bond 成員故障後的切換時間 | 中斷單一鏈路，測量網路中斷時間 |  | Tony | 需驗證 switch 端 LACP 設定 |
| 3.18 | TC-NW-03 | 管理網路與 Corosync 網路分離 | 網路分流的穩定性 | 將 Corosync 流量移至專用網段 |  | Tony | 建議最佳實踐 |

### Backup_Replication測試(Backup_Replication_Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.19 | TC-BR-01 | Proxmox Backup Server (PBS) 整合 | PBS 與 PVE 9.1 整合度 | 安裝 PBS，配置 datastore，掛載至 PVE 儲存 |  | Tony | 需獨立伺服器或 VM |
| 3.20 | TC-BR-02 | VM 增量備份驗證 | 增量備份機制正確性 | 建立 VM，執行首次完整備份，修改資料後執行增量 |  | Tony | 驗證 client-side deduplication |
| 3.21 | TC-BR-03 | VM 備份還原驗證 | 備份還原完整性 | 備份 VM，刪除 VM，執行完整還原 |  | Tony | 需驗證資料一致性 |
| 3.22 | TC-BR-04 | VM Replication 跨節點複製 | ZFS/LVM-Thin 複製機制 | 配置 VM replication job，執行跨節點複製 |  | Tony | 不需要 PBS，純本地複製 |
| 3.23 | TC-BR-05 | 備份工作排程驗證 | 自動化備份排程正確性 | 設定每日備份排程，驗證執行時間與日誌 |  | Tony | 需長時間觀察 |

### LVM-Thin_Snapshot專項測試 (LVM-Thin Snapshot Tests)

> **注意**：本區塊僅針對 LVM-Thin 格式的 VM，QCOW2 VM 不在本測試範圍。

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.24 | TC-LVMSP-01 | LVM-Thin Snapshot 建立 | Snapshot 建立速度與可行性 | 對 LVM-Thin VM 建立線上 snapshot |  | Tony | 需確認 VM 磁碟為 LVM-Thin |
| 3.25 | TC-LVMSP-02 | LVM-Thin Snapshot 還原 | Snapshot 還原正確性 | 建立 snapshot，寫入資料，還原至 snapshot 點 |  | Tony | 驗證資料一致性 |
| 3.26 | TC-LVMSP-03 | LVM-Thin Snapshot 刪除 | Snapshot 刪除對效能影響 | 刪除多個 snapshot，觀察 I/O 變化 |  | Tony | 需注意刪除順序 |
| 3.27 | TC-LVMSP-04 | LVM-Thin Snapshot 數量上限 | Snapshot 數量對效能影響 | 建立 10 個 snapshot，執行 FIO 測試 |  | Tony | 找出效能明顯衰減的臨界點 |

### 版本升級測試 (Upgrade Tests)

| 項次 | 測試代號 | 測試項目 | 驗證項目 | 方法 | 結果 | 測試員 | 備註 |
|------|----------|----------|----------|------|------|--------|------|
| 3.28 | TC-UPG-01 | PVE 8 → 9 離線升級 | 離線升級流程正確性 | 參考官方文件，執行離線升級流程 |  | Tony | 需先在測試環境驗證 |
| 3.29 | TC-UPG-02 | 升級後服務啟動驗證 | 核心服務正常運行 | 檢查 `pve-cluster`, `pve-firewall`, `pve-ha-lrm` 狀態 |  | Tony | 需比對 `/var/log/pve-manager/` |
| 3.30 | TC-UPG-03 | 升級後 VM 運行驗證 | VM 不受升級影響 | 啟動所有 VM，驗證網路、儲存、I/O |  | Tony | 需執行效能基準測試 |
| 3.31 | TC-UPG-04 | 升級回滾演練 | 升級失敗的復原能力 | 備份後執行升級，模擬失敗，手動回滾 |  | Tony | 需練習完整流程 |

---

### 測試矩陣摘要 (Test Matrix Summary)

| 測試類別 | 項目數 | 測試代號 |
|----------|--------|----------|
| 環境建置 | 7 項 | TC-ENV-05 ~ TC-ENV-07 |
| 功能測試 | 3 項 | TC-FUNC-01 ~ TC-FUNC-07 |
| 系統穩定性測試 | 4 項 | TC-SYS-01 ~ TC-SYS-04 |
| HA 機制驗證測試 | 4 項 | TC-HA-01 ~ TC-HA-04 |
| 儲存風險測試 | 7 項 | TC-ST-01 ~ TC-ST-07 |
| 網路故障測試 | 3 項 | TC-NW-01 ~ TC-NW-03 |
| Backup/Replication | 5 項 | TC-BR-01 ~ TC-BR-05 |
| LVM-Thin Snapshot | 4 項 | TC-LVMSP-01 ~ TC-LVMSP-04 |
| 版本升級測試 | 4 項 | TC-UPG-01 ~ TC-UPG-04 |
| **總計** | **41 項** | - |

---

### 測試時程建議 (Timeline Recommendations)

| 測試階段 | 預估天數 | 測試項目 |
|----------|----------|----------|
| Phase 1: 環境建置驗收 | 15 天 | TC-ENV-05 ~ TC-ENV-07 |
| Phase 2: 功能測試 | 30 天 | TC-FUNC-01 ~ TC-FUNC-07 |
| Phase 3: 系統穩定性 | 15 天 | TC-SYS-01 ~ TC-SYS-04 |
| Phase 4: HA 機制驗證 | 15 天 | TC-HA-01 ~ TC-HA-04 |
| Phase 5: 儲存風險驗證 | 15 天 | TC-ST-03 ~ TC-ST-07 |
| Phase 6: 網路故障測試 | 15 天 | TC-NW-01 ~ TC-NW-03 |
| Phase 7: Backup/Replication | 5 天 | TC-BR-01 ~ TC-BR-05 |
| Phase 8: LVM-Thin Snapshot | 3 天 | TC-LVMSP-01 ~ TC-LVMSP-04 |
| Phase 9: 版本升級測試 | 5 天 | TC-UPG-01 ~ TC-UPG-04 |
| **總計** | **118 天** | - |

