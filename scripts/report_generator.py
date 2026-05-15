#!/usr/bin/env python3
import json
import os
import sys
import argparse
from datetime import datetime

STATUS_FILE = os.path.expanduser("~/pve-test-status.json")
LOG_DIR = "/tmp/pve-test-logs"

def load_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def get_test_result(data, test_key):
    t = data.get('tests', {}).get(test_key, {})
    if t.get('passes', 0) > 0:
        return 'PASS'
    elif t.get('runs', 0) > 0:
        return 'FAIL'
    return 'NOT RUN'

def generate_report(data, output_file):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    total_runs = sum(s['runs'] for s in data.get('tests', {}).values())
    total_passes = sum(s['passes'] for s in data.get('tests', {}).values())
    total_failures = sum(s['failures'] for s in data.get('tests', {}).values())
    pass_rate = (total_passes / total_runs * 100) if total_runs > 0 else 0

    test_results = {
        'bond0_nic2_down': get_test_result(data, 'bond0_nic2_down'),
        'bond0_nic3_down': get_test_result(data, 'bond0_nic3_down'),
        'bond0_dual_down': get_test_result(data, 'bond0_dual_down'),
        'corosync_ring0_isolation': get_test_result(data, 'corosync_ring0_isolation'),
        'corosync_dual_ring_isolation': get_test_result(data, 'corosync_dual_ring_isolation'),
        'bond0_nic2_ping': get_test_result(data, 'bond0_nic2_ping'),
        'bond0_nic3_ping': get_test_result(data, 'bond0_nic3_ping'),
        'bond2_nic4_down': get_test_result(data, 'bond2_nic4_down'),
        'bond2_nic5_down': get_test_result(data, 'bond2_nic5_down'),
        'switch_reboot_60s': get_test_result(data, 'switch_reboot_60s'),
    }

    report = f"""# PVE LACP HA & 故障轉移測試報告

## 1. 測試資訊

| 項目 | 內容 |
|------|------|
| 報告生成時間 | {now} |
| 狀態文件 | {STATUS_FILE} |
| 最後更新 | {data.get('last_updated', 'N/A')} |
| 當前狀態 | {data.get('status', 'N/A')} |
| 當前測試 | {data.get('current_test', 'None')} |

## 2. 測試歷史

| 測試情境 | 開始時間 | 結束時間 | 狀態 |
|----------|----------|----------|------|
"""

    for h in data.get('history', []):
        report += "| {} | {} | {} | {} |\n".format(
            h['test'],
            h.get('start', 'N/A'),
            h.get('end', 'N/A'),
            h.get('status', 'N/A')
        )

    report += """
## 3. 測試統計

| 測試情境 | 執行次數 | 通過 | 失敗 | 通過率 |
|----------|----------|------|------|--------|
"""

    for t, s in data.get('tests', {}).items():
        rate = (s['passes'] / s['runs'] * 100) if s['runs'] > 0 else 0
        report += "| {} | {} | {} | {} | {:.1f}% |\n".format(
            t, s['runs'], s['passes'], s['failures'], rate
        )

    report += """
## 4. 測試矩陣 (TC-HA-02 + TC-NW-02)

| # | 測試代碼 | 測試目標 | 預期行為 | 實際結果 |
|---|---------|---------|---------|----------|
| 1 | test-ha-nic2 | bond0 nic2 | 不應觸發 HA | {} |
| 2 | test-ha-nic3 | bond0 nic3 | 不應觸發 HA | {} |
| 3 | test-ha-bond0-dual | bond0 nic2+nic3 | Quorate 維持 | {} |
| 4 | test-ha-ring0-isolate | 172.19.0.172 isolated | Quorate 維持 | {} |
| 5 | test-ha-dual-ring | both rings isolated | **HA 觸發** | {} |
| 6 | test-bw-bond0-ping | nic2 ping | <1s switch | {} |
| 7 | test-bw-bond0-ping-nic3 | nic3 ping | <1s switch | {} |
| 8 | test-bw-nic4 | bond2 nic4 | ~9Gbps | {} |
| 9 | test-bw-nic5 | bond2 nic5 | ~9Gbps | {} |
| 10 | test-switch-reboot | nic2+nic3 60s | 60s後恢復 | {} |

## 5. 摘要

| 指標 | 數值 |
|------|------|
| 總執行次數 | {} |
| 總通過次數 | {} |
| 總失敗次數 | {} |
| 通過率 | {:.1f}% |

## 6. 環境配置

- **Local Host**: 172.23.0.171
- **Target Host 1**: 172.23.0.172
- **Target Host 2**: 172.23.0.173
- **Cluster 網段**: 172.19.0.x (bond0: nic2+nic3)
- **儲存網段**: 10.23.0.x (bond2: nic4+nic5)
- **Debug 網段**: 172.23.0.x (nic0)
- **VM ID**: 105 (HA managed)

## 7. 網路架構

```
                    +-- nic2 ---+
    172.19.0.171 --+-- nic3 ---+-- bond0 --+-- vmbr0.19 --+-- 172.19.0.x (Cluster)
                    +-- nic4 ---+
    10.23.0.171 ---+-- nic5 ---+-- bond2 --+-- vmbr2    --+-- 10.23.0.x (Storage)
                    +-- nic0 ---------------------------+-- 172.23.0.x (Debug/Agent)
```

## 8. 結論與建議

### 測試結果分析

""".format(
        test_results['bond0_nic2_down'],
        test_results['bond0_nic3_down'],
        test_results['bond0_dual_down'],
        test_results['corosync_ring0_isolation'],
        test_results['corosync_dual_ring_isolation'],
        test_results['bond0_nic2_ping'],
        test_results['bond0_nic3_ping'],
        test_results['bond2_nic4_down'],
        test_results['bond2_nic5_down'],
        test_results['switch_reboot_60s'],
        total_runs,
        total_passes,
        total_failures,
        pass_rate
    )

    if total_runs == 0:
        report += "**尚未執行任何測試** - 請執行 `make fully-test` 或個別測試目標。\n\n"
    elif pass_rate >= 80:
        report += "整體測試狀態: 良好 - 通過率 {:.1f}%，LACP HA 機制運作正常。\n\n".format(pass_rate)
    elif pass_rate >= 50:
        report += "整體測試狀態: 部分異常 - 通過率 {:.1f}%，建議檢查失敗的測試項目。\n\n".format(pass_rate)
    else:
        report += "整體測試狀態: 異常 - 通過率 {:.1f}%，請緊急檢查叢集狀態。\n\n".format(pass_rate)

    report += """### 關鍵觀察

1. **LACP 單鏈路故障**: 單一 nic 故障不應影響 HA，驗證 bond0 備援機制
2. **Corosync 雙 ring**: ring1 可作為 ring0 的備援路徑
3. **HA 觸發條件**: 只有當 Corosync 雙 ring 同步隔離時才應觸發 VM failover
4. **bond2 儲存網路**: 獨立於 cluster 網路，不應影響 HA 判斷

### 建議

- [ ] 若切換時間 > 1 秒，檢查交換機 LACP 配置
- [ ] 若丟包數 > 3 個，調整 bond miimon 參數
- [ ] 若 HA 誤觸發，調整 Corosync deadtime 參數
- [ ] 若 SSH 驗證失敗，檢查網路連接性和防火牆

---

*報告自動生成 - PVE LACP Testing Framework*
"""

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print("Report saved to: {}".format(output_file))
    else:
        print(report)

def main():
    parser = argparse.ArgumentParser(description='Generate PVE test report')
    parser.add_argument('-o', '--output', help='Output file path')
    args = parser.parse_args()

    data = load_status()
    if data is None:
        print("# PVE LACP HA 測試報告\n\n*無測試數據 - 請先執行測試*\n\n建議操作:\n  make health-check  # 先執行健康檢查\n  make fully-test    # 執行完整測試流程")
        sys.exit(0)

    generate_report(data, args.output)

if __name__ == '__main__':
    main()