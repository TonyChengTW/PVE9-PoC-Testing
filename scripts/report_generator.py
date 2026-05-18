#!/usr/bin/env python3
import json
import os
import sys
import argparse
from datetime import datetime

STATUS_FILE = os.path.expanduser("~/pve-test-status.json")
LOG_DIR = "/tmp/pve-test-logs"

TEST_DEFINITIONS = {
    'bond0_nic2_down': {
        'id': 1,
        'name': 'test-ha-nic2',
        'category': 'HA',
        'spec': 'TC-HA-02',
        'objective': '驗證 bond0 單一鏈路 (nic2) 故障不應觸發 HA',
        'expected': 'LACP 自動切換到 nic3，VM 繼續運行，Quorate 維持',
        'method': 'ip link set down nic2，等待 10 秒，驗證 SSH 和 HA 狀態，然後恢復',
        'verifications': [
            'SSH to 172.23.0.172: pvecm status',
            'SSH to 172.23.0.172: corosync-cmapctl | grep members',
            'SSH to 172.23.0.172: ha-manager status',
            'SSH to 172.23.0.172: qm status 105',
        ],
    },
    'bond0_nic3_down': {
        'id': 2,
        'name': 'test-ha-nic3',
        'category': 'HA',
        'spec': 'TC-HA-02',
        'objective': '驗證 bond0 單一鏈路 (nic3) 故障不應觸發 HA',
        'expected': 'LACP 自動切換到 nic2，VM 繼續運行，Quorate 維持',
        'method': 'ip link set down nic3，等待 10 秒，驗證 SSH 和 HA 狀態，然後恢復',
        'verifications': [
            'SSH to 172.23.0.172: pvecm status',
            'SSH to 172.23.0.172: ha-manager status',
            'SSH to 172.23.0.172: qm status 105',
        ],
    },
    'bond0_dual_down': {
        'id': 3,
        'name': 'test-ha-bond0-dual',
        'category': 'HA',
        'spec': 'TC-HA-02',
        'objective': '驗證 bond0 雙鏈路同時故障時 Quorate 應維持',
        'expected': '叢集成員仍可透過 nic0 溝通，Quorate 維持，不應觸發 HA',
        'method': 'ip link set down nic2 && nic3，等待 10 秒，驗證兩節點狀態，然後恢復',
        'verifications': [
            'SSH to 172.23.0.172: pvecm status',
            'SSH to 172.23.0.172: corosync-cmapctl | grep members',
            'SSH to 172.23.0.173: pvecm status',
            'SSH to 172.23.0.173: ha-manager status',
        ],
    },
    'corosync_ring0_isolation': {
        'id': 4,
        'name': 'test-ha-ring0-isolate',
        'category': 'HA',
        'spec': 'TC-HA-02',
        'objective': '驗證 Corosync ring0 隔離時 Quorate 應維持 (ring1 備援)',
        'expected': 'Corosync 透過 ring1 仍可通訊，Quorate 維持，不應觸發 HA',
        'method': 'iptables -A INPUT -s 172.19.0.172 -j DROP，隔離 15 秒，驗證後移除規則',
        'verifications': [
            'SSH to 172.23.0.173: pvecm status',
            'SSH to 172.23.0.173: corosync-cmapctl | grep members',
            'SSH to 172.23.0.173: ha-manager status',
        ],
    },
    'corosync_dual_ring_isolation': {
        'id': 5,
        'name': 'test-ha-dual-ring',
        'category': 'HA',
        'spec': 'TC-HA-02',
        'objective': '驗證 Corosync 雙 ring 同時隔離時應觸發 HA',
        'expected': 'Corosync 無法通訊，叢集失 Quorate，HA 應將 VM 105  failover 到另一節點',
        'method': 'iptables 封鎖 172.19.0.172 + 10.23.0.172 兩個 ring，等待 15 秒，驗證 HA 狀態',
        'verifications': [
            'SSH to 172.23.0.173: pvecm status',
            'SSH to 172.23.0.173: ha-manager status',
            'SSH to 172.23.0.173: qm status 105',
        ],
    },
    'bond0_nic2_ping': {
        'id': 6,
        'name': 'test-bw-bond0-ping',
        'category': 'Bandwidth',
        'spec': 'TC-NW-02',
        'objective': '驗證 bond0 nic2 故障時 LACP 切換時間 < 1 秒',
        'expected': 'Ping 輕微延遲或些微丟包， failover 時間 < 1 秒',
        'method': '背景 ping 172.19.1.252，ip link set down nic2，10 秒後恢復，分析丟包率',
        'verifications': [
            'timeout 20 ping -i 0.2 172.19.1.252',
            '分析 /tmp/ping_monitor.log 丟包率 (閾值: < 5%)',
        ],
    },
    'bond0_nic3_ping': {
        'id': 7,
        'name': 'test-bw-bond0-ping-nic3',
        'category': 'Bandwidth',
        'spec': 'TC-NW-02',
        'objective': '驗證 bond0 nic3 故障時 LACP 切換時間 < 1 秒',
        'expected': 'Ping 輕微延遲或些微丟包， failover 時間 < 1 秒',
        'method': '背景 ping 172.19.1.252，ip link set down nic3，10 秒後恢復，分析丟包率',
        'verifications': [
            'timeout 20 ping -i 0.2 172.19.1.252',
            '分析 /tmp/ping_monitor_nic3.log 丟包率 (閾值: < 5%)',
        ],
    },
    'bond2_nic4_down': {
        'id': 8,
        'name': 'test-bw-nic4',
        'category': 'Bandwidth',
        'spec': 'TC-NW-02',
        'objective': '驗證 bond2 nic4 故障時儲存網路 failover',
        'expected': 'VM 105 I/O 可能短暫中斷但不應影響 HA，60 秒後恢復約 9Gbps',
        'method': '啟動 iperf3 背景流量，ip link set down nic4，等待 10 秒，恢復後驗證',
        'verifications': [
            'iperf3 -c 172.23.0.172 -t 60 -P 4 -J > /tmp/iperf_before_nic4.json',
            'qm status 105',
        ],
    },
    'bond2_nic5_down': {
        'id': 9,
        'name': 'test-bw-nic5',
        'category': 'Bandwidth',
        'spec': 'TC-NW-02',
        'objective': '驗證 bond2 nic5 故障時儲存網路 failover',
        'expected': 'VM 105 I/O 可能短暫中斷但不應影響 HA，60 秒後恢復約 9Gbps',
        'method': '啟動 iperf3 背景流量，ip link set down nic5，等待 10 秒，恢復後驗證',
        'verifications': [
            'iperf3 -c 172.23.0.172 -t 60 -P 4 -J > /tmp/iperf_before_nic5.json',
            'qm status 105',
        ],
    },
    'switch_reboot_60s': {
        'id': 10,
        'name': 'test-switch-reboot',
        'category': 'Bandwidth',
        'spec': 'TC-NW-02',
        'objective': '驗證交換機重啟模擬 (60 秒中斷) 後網路自動恢復',
        'expected': '60 秒中斷期間 Ping 完全中斷，恢復後網路自動恢復，些微丟包可接受',
        'method': 'ip link set down nic2 && nic3，背景 ping 60 秒，恢復後分析丟包率',
        'verifications': [
            'timeout 70 ping -i 0.5 172.19.1.252',
            '分析 /tmp/ping_reboot.log 總丟包率',
        ],
    },
}

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

def format_duration(start_iso, end_iso):
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        delta = end - start
        total_sec = delta.total_seconds()
        if total_sec < 60:
            return f"{total_sec:.1f} 秒"
        elif total_sec < 3600:
            m = int(total_sec // 60)
            s = total_sec % 60
            return f"{m}m {s:.1f}s"
        else:
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            return f"{h}h {m}m"
    except:
        return "N/A"

def format_datetime(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_str or 'N/A'

def generate_report(data, output_file):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    total_runs = sum(s['runs'] for s in data.get('tests', {}).values())
    total_passes = sum(s['passes'] for s in data.get('tests', {}).values())
    total_failures = sum(s['failures'] for s in data.get('tests', {}).values())
    pass_rate = (total_passes / total_runs * 100) if total_runs > 0 else 0

    history_map = {h['test']: h for h in data.get('history', [])}

    report = f"""# PVE LACP HA & 故障轉移測試報告

## 1. 測試摘要

| 項目 | 內容 |
|------|------|
| 報告生成時間 | {now} |
| 測試框架版本 | Makefile-based Testing Framework v1.0 |
| 狀態文件 | {STATUS_FILE} |
| 測試資料更新時間 | {data.get('last_updated', 'N/A')} |
| 總執行次數 | {total_runs} |
| 通過次數 | {total_passes} |
| 失敗次數 | {total_failures} |
| 整體通過率 | {pass_rate:.1f}% |
| 測試狀態 | {'全部通過' if total_failures == 0 and total_runs > 0 else '部分失敗' if total_failures > 0 else '尚無執行記錄'} |

"""

    report += """## 2. 測試過程詳細記錄

"""

    for test_key, defn in TEST_DEFINITIONS.items():
        hist = history_map.get(test_key, {})
        result = get_test_result(data, test_key)

        start_time = hist.get('start', 'N/A')
        end_time = hist.get('end', 'N/A')
        duration = format_duration(start_time, end_time)

        result_icon = '✅' if result == 'PASS' else '❌' if result == 'FAIL' else '⏸️'
        result_color = '**通過**' if result == 'PASS' else '**失敗**' if result == 'FAIL' else '未執行'

        report += f"""### {defn['id']}. {defn['name']} {result_icon}

**測試分類**: {defn['category']} | **測試規格**: {defn['spec']}

| 欄位 | 內容 |
|------|------|
| 測試代碼 | `{test_key}` |
| 測試目標 | {defn['objective']} |
| 預期行為 | {defn['expected']} |
| 測試方法 | {defn['method']} |

**時間記錄**:

| 開始時間 | 結束時間 | 持續時間 | 測試結果 |
|----------|----------|----------|----------|
| {format_datetime(start_time)} | {format_datetime(end_time)} | {duration} | {result_icon} {result_color} |

**驗證項目** (測試執行時檢查的指令):

"""

        for v in defn['verifications']:
            report += f"- `{v}`\n"

        if hist:
            report += f"""
**實際行為觀測**:

- 測試於 **{format_datetime(start_time)}** 開始執行
- 故障注入完成後驗證遠端節點狀態
- 於 **{format_datetime(end_time)}** 完成測試並恢復網路
- 持續時間: **{duration}**
- 測試結果: **{result}**

"""
        else:
            report += """
**實際行為觀測**:

_此測試尚未執行，無觀測資料。_

"""

        report += "---\n\n"

    report += f"""

## 3. 測試矩陣總覽

| # | 測試代碼 | 分類 | 規格 | 開始時間 | 結束時間 | 持續時間 | 結果 |
|---|---------|------|------|----------|----------|----------|------|
"""

    for test_key, defn in TEST_DEFINITIONS.items():
        hist = history_map.get(test_key, {})
        result = get_test_result(data, test_key)
        result_icon = '✅ PASS' if result == 'PASS' else '❌ FAIL' if result == 'FAIL' else '⏸ NOT RUN'
        duration = format_duration(hist.get('start'), hist.get('end'))
        start_t = format_datetime(hist.get('start')) if hist else '-'
        end_t = format_datetime(hist.get('end')) if hist else '-'
        report += f"| {defn['id']} | `{test_key}` | {defn['category']} | {defn['spec']} | {start_t} | {end_t} | {duration} | {result_icon} |\n"

    report += f"""

## 4. 環境配置

| 項目 | 內容 |
|------|------|
| Local Host (本地) | 172.23.0.171 |
| Target Host 1 (節點 1) | 172.23.0.172 |
| Target Host 2 (節點 2) | 172.23.0.173 |
| Cluster 網段 (bond0) | 172.19.0.x (nic2 + nic3 LACP) |
| Storage 網段 (bond2) | 10.23.0.x (nic4 + nic5 LACP) |
| Debug/Agent 網段 (nic0) | 172.23.0.x |
| HA 管理 VM | VM 105 |
| iptables INPUT Policy | ACCEPT (測試期間) |
| 日誌目錄 | {LOG_DIR} |
| 狀態檔案 | {STATUS_FILE} |

### 4.1 網路架構圖

```
                         +-- nic2 ---+
  172.19.0.171 --------+-- nic3 ---+-- bond0 --+-- vmbr0.19 --+-- 172.19.0.x (Cluster 網段)
                         +-- nic4 ---+
  10.23.0.171 ---------+-- nic5 ---+-- bond2 --+-- vmbr2    --+-- 10.23.0.x (Storage 網段)
                         +-- nic0 ----------------------------+-- 172.23.0.x (Debug/Agent)
```

## 5. 測試結論

### 5.1 結果分析

"""

    if total_runs == 0:
        report += """**尚未執行任何測試** - 請執行以下命令開始測試：

```bash
make health-check    # 先執行健康檢查
make fully-test      # 執行完整測試流程 (TC-HA-02 + TC-NW-02)
```

"""
    elif pass_rate >= 80:
        report += f"""整體測試狀態: **良好** ✅

- 通過率: **{pass_rate:.1f}%** ({total_passes}/{total_runs})
- LACP HA 機制運作正常，容錯機制有效
- 建議: 定期執行健康檢查追蹤叢集狀態

"""
    elif pass_rate >= 50:
        report += f"""整體測試狀態: **部分異常** ⚠️

- 通過率: **{pass_rate:.1f}%** ({total_passes}/{total_runs})
- 建議: 檢查失敗的測試項目，確認是否為環境問題或設定異常

"""
    else:
        report += f"""整體測試狀態: **異常** ❌

- 通過率: **{pass_rate:.1f}%** ({total_passes}/{total_runs})
- 建議: **緊急檢查叢集狀態**，確認網路和 HA 設定

"""

    report += """### 5.2 關鍵觀測

1. **LACP 單鏈路故障**: 單一 nic 故障時 LACP 應自動切換到備援鏈路，不應影響 HA
2. **Corosync 雙 ring 備援**: ring1 可作為 ring0 的備援路徑，單一 ring 隔離不應影響叢集
3. **HA 觸發條件**: 只有當 Corosync 雙 ring 同時隔離導致叢集失 Quorate 時才應觸發 VM failover
4. **bond2 儲存網路**: 獨立於 cluster 網路，單一鏈路故障不應影響 HA 判斷

### 5.3 後續建議

| 問題 | 建議檢查項目 |
|------|------------|
| failover 時間 > 1 秒 | 檢查交換機 LACP 和 STP 設定 |
| 丟包率 > 5% | 調整 bond miimon 參數 (建議 100ms) |
| HA 誤觸發 | 檢查 Corosync deadtime 和 consensus 參數 |
| SSH 驗證失敗 | 確認網路連接性和防火牆規則 |
| Quorate 異常 | 檢查 Corosync totem 設定和網路延遲 |

---

*報告自動生成 - PVE LACP Testing Framework*  
*Generated: {}*
""".format(now)

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