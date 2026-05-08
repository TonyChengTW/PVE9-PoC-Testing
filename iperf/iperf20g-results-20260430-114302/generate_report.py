#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime

result_dir = os.path.dirname(os.path.abspath(__file__))
result_dir = os.path.dirname(result_dir) + "/" + os.path.basename(result_dir)
if not os.path.exists(result_dir):
    result_dir = os.getcwd()

report_file = os.path.expanduser("~/202604291721_PVE_iperf3壓力測試v1.md")

# 读取 bond0 信息
def get_bond_info(host="local"):
    if host == "local":
        cmd = "cat /proc/net/bonding/bond0 2>/dev/null"
    else:
        cmd = f"ssh -o StrictHostKeyChecking=no 172.19.0.173 'cat /proc/net/bonding/bond0 2>/dev/null'"
    
    info = subprocess.getoutput(cmd)
    return info

# 解析 iperf3 JSON
def parse_iperf_json(json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        end = data.get('end', {})
        result = {
            'type': 'TCP',
            'streams': 1,
            'duration': 0,
            'tx_bw': 0,
            'rx_bw': 0,
            'total_bw': 0,
            'loss': '-',
            'jitter': '-',
            'retransmits': '-'
        }
        
        # 判断类型
        if '-u' in data.get('start', {}).get('command_line', ''):
            result['type'] = 'UDP'
        
        # 持续时间
        if 'sum' in end:
            result['duration'] = end['sum'].get('seconds', 0)
        elif 'sum_received' in end:
            result['duration'] = end['sum_received'].get('seconds', 0)
        
        # 带宽
        if '--bidir' in data.get('start', {}).get('command_line', ''):
            # 双向测试
            sum_sent = end.get('sum_sent', {})
            sum_received = end.get('sum_received', {})
            result['tx_bw'] = sum_sent.get('bits_per_second', 0) / 1e9
            result['rx_bw'] = sum_received.get('bits_per_second', 0) / 1e9
            result['total_bw'] = result['tx_bw'] + result['rx_bw']
            result['retransmits'] = sum_sent.get('retransmits', '-')
        elif '-R' in data.get('start', {}).get('command_line', ''):
            # 反向测试
            sum_data = end.get('sum_received', {})
            result['rx_bw'] = sum_data.get('bits_per_second', 0) / 1e9
            result['total_bw'] = result['rx_bw']
        else:
            # 正常测试
            if result['type'] == 'UDP':
                sum_data = end.get('sum', {})
                result['tx_bw'] = sum_data.get('bits_per_second', 0) / 1e9
                result['total_bw'] = result['tx_bw']
                result['loss'] = f"{sum_data.get('lost_percent', 0):.2f}%"
                result['jitter'] = f"{sum_data.get('jitter_ms', 0):.3f}"
            else:
                sum_data = end.get('sum_received', end.get('sum_sent', {}))
                result['tx_bw'] = sum_data.get('bits_per_second', 0) / 1e9
                result['total_bw'] = result['tx_bw']
                result['retransmits'] = sum_data.get('retransmits', '-')
        
        # 并行流数
        intervals = data.get('intervals', [])
        if intervals:
            streams = set()
            for interval in intervals:
                streams.add(interval.get('streams', [{}])[0].get('socket', 0))
            result['streams'] = len(streams) if streams else 1
        
        return result
    except Exception as e:
        print(f"Error parsing {json_file}: {e}")
        return None

# 收集测试结果
test_files = [(f, os.path.join(result_dir, f)) for f in os.listdir(result_dir) if f.endswith('.json')]
test_files.sort()

# 生成报告
with open(report_file, 'w', encoding='utf-8') as f:
    f.write("# PVE iperf3 壓力測試 v1 - 20Gbps LACP 聚合驗證\n\n")
    
    # 测试信息
    f.write("## 測試信息\n\n")
    f.write("| 項目 | 內容 |\n")
    f.write("|------|------|\n")
    f.write(f"| 測試日期 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |\n")
    f.write(f"| 測試人員 | opencode 自動化測試 |\n")
    f.write(f"| 測試目的 | 驗證 2x10G LACP bond0 能否達到 20Gbps 聚合帶寬 |\n")
    f.write("\n")
    
    # 测试环境
    f.write("## 測試環境\n\n")
    
    # 源主机 bond0 信息
    bond_local = get_bond_info("local")
    f.write("### 源主機 (172.19.0.171)\n\n")
    f.write("**bond0 配置:**\n")
    f.write("```\n")
    for line in bond_local.split('\n')[:20]:
        if line.strip():
            f.write(line + '\n')
    f.write("```\n\n")
    
    # 目标主机 bond0 信息
    bond_remote = get_bond_info("remote")
    f.write("### 目標主機 (172.19.0.173)\n\n")
    f.write("**bond0 配置:**\n")
    f.write("```\n")
    for line in bond_remote.split('\n')[:20]:
        if line.strip():
            f.write(line + '\n')
    f.write("```\n\n")
    
    # iperf3 版本
    f.write(f"**iperf3 版本:** {subprocess.getoutput('iperf3 --version 2>&1 | head -1')}\n\n")
    
    # 测试结果汇总
    f.write("## 測試結果彙總\n\n")
    f.write("### TCP 測試\n\n")
    f.write("| 測試項 | 並行流 | 持續時間 | 發送帶寬 (Gbps) | 接收帶寬 (Gbps) | 總帶寬 (Gbps) | 重傳次數 |\n")
    f.write("|--------|--------|----------|----------------|----------------|---------------|----------|\n")
    
    tcp_tests = []
    udp_tests = []
    bidir_tests = []
    
    for filename, filepath in test_files:
        if not filename.endswith('.json'):
            continue
        result = parse_iperf_json(filepath)
        if not result:
            continue
        
        test_name = filename.replace('.json', '')
        
        if result['type'] == 'TCP':
            if 'bidir' in test_name or '--bidir' in str(result):
                bidir_tests.append((test_name, result))
            else:
                tcp_tests.append((test_name, result))
        else:
            udp_tests.append((test_name, result))
    
    for test_name, r in tcp_tests:
        f.write(f"| {test_name} | {r['streams']} | {r['duration']:.0f}s | {r['tx_bw']:.2f} | {r['rx_bw']:.2f} | {r['total_bw']:.2f} | {r['retransmits']} |\n")
    
    f.write("\n### UDP 測試\n\n")
    f.write("| 測試項 | 並行流 | 持續時間 | 帶寬 (Gbps) | 丟包率 | 抖動 (ms) |\n")
    f.write("|--------|--------|----------|-------------|--------|-----------|\n")
    
    for test_name, r in udp_tests:
        f.write(f"| {test_name} | {r['streams']} | {r['duration']:.0f}s | {r['total_bw']:.2f} | {r['loss']} | {r['jitter']} |\n")
    
    f.write("\n### 雙向測試\n\n")
    f.write("| 測試項 | 並行流 | 持續時間 | 發送 (Gbps) | 接收 (Gbps) | 總帶寬 (Gbps) |\n")
    f.write("|--------|--------|----------|-------------|-------------|---------------|\n")
    
    for test_name, r in bidir_tests:
        f.write(f"| {test_name} | {r['streams']} | {r['duration']:.0f}s | {r['tx_bw']:.2f} | {r['rx_bw']:.2f} | {r['total_bw']:.2f} |\n")
    
    f.write("\n")
    
    # 20Gbps 达成验证
    f.write("## 20Gbps 達成驗證\n\n")
    f.write("根據 LACP (802.3ad) 協議特性：\n")
    f.write("1. **單流限制**: 單個 TCP/UDP 流只會哈希到單條物理鏈路 → 最高 ~10 Gbps\n")
    f.write("2. **多流聚合**: 多個並行流通過 layer3+4 哈希分散到不同物理鏈路 → 可達 ~20 Gbps\n")
    f.write("3. **傳輸哈希策略**: layer3+4 (源/目標 IP + 端口) 決定流量走向\n")
    f.write("\n")
    
    # 找出最高带宽
    max_bw = 0
    max_test = ""
    for test_name, r in tcp_tests + udp_tests + bidir_tests:
        if r['total_bw'] > max_bw:
            max_bw = r['total_bw']
            max_test = test_name
    
    f.write(f"**最高聚合帶寬**: {max_bw:.2f} Gbps (測試項: {max_test})\n\n")
    
    if max_bw >= 18:
        f.write("✅ **結論**: LACP bond0 成功達到接近 20Gbps 的聚合帶寬！\n")
    elif max_bw >= 15:
        f.write("⚠️ **結論**: LACP bond0 部分達成聚合效果，但尚未完全利用雙鏈路。\n")
    else:
        f.write("❌ **結論**: LACP bond0 未達到預期聚合效果，流量可能集中在單條鏈路。\n")
    
    f.write("\n")
    
    # 详细结果
    f.write("## 詳細結果\n\n")
    
    for filename, filepath in test_files:
        if not filename.endswith('.json'):
            continue
        test_name = filename.replace('.json', '')
        f.write(f"### {test_name}\n\n")
        f.write("```json\n")
        try:
            with open(filepath, 'r') as jf:
                data = json.load(jf)
                end_data = data.get('end', {})
                # 输出关键摘要
                if 'sum_received' in end_data:
                    f.write(json.dumps({'sum_received': end_data['sum_received']}, indent=2) + '\n')
                if 'sum_sent' in end_data:
                    f.write(json.dumps({'sum_sent': end_data['sum_sent']}, indent=2) + '\n')
                if 'sum' in end_data:
                    f.write(json.dumps({'sum': end_data['sum']}, indent=2) + '\n')
        except:
            f.write("(無法解析)\n")
        f.write("```\n\n")
    
    # 结论与建议
    f.write("## 結論與建議\n\n")
    f.write("### 觀察重點\n\n")
    f.write("1. **TCP 單流**: 應接近 10 Gbps (單條 10G 鏈路極限)\n")
    f.write("2. **TCP 8-16流**: 應接近 18-20 Gbps (雙鏈路聚合)\n")
    f.write("3. **UDP 測試**: 注意丟包率，應低於 0.1%\n")
    f.write("4. **雙向測試**: 驗證全雙工性能\n\n")
    
    f.write("### 優化建議\n\n")
    f.write("1. **傳輸哈希策略**: 當前使用 `layer3+4`，可嘗試 `layer2+3` 觀察效果\n")
    f.write("2. **並行流數量**: 建議至少 8 個並行流以充分利用 LACP\n")
    f.write("3. **UDP 帶寬限制**: 單流 UDP 建議不超過 10G，多流可達 20G\n")
    f.write("4. **監控建議**: 使用 `cat /proc/net/bonding/bond0` 觀察流量分佈\n\n")
    
    f.write("## 原始數據\n\n")
    f.write(f"所有 JSON 原始數據保存在: `{result_dir}/`\n")

print(f"報告已生成: {report_file}")
