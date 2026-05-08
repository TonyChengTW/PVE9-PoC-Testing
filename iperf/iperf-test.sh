#!/bin/bash
# iperf3 压力测试脚本
# 源主机: 172.19.0.171
# 目标主机: 172.19.0.173

TARGET="172.19.0.173"
RESULT_DIR="$HOME/iperf-results-$(date +%Y%m%d-%H%M%S)"
REPORT="$HOME/iperf壓力測試.md"

mkdir -p "$RESULT_DIR"

echo "=========================================="
echo "iperf3 压力测试开始"
echo "源主机: $(hostname -I | awk '{print $1}')"
echo "目标主机: $TARGET"
echo "结果目录: $RESULT_DIR"
echo "=========================================="

# 函数: 运行测试并保存 JSON 结果
run_test() {
    local test_name="$1"
    local iperf_opts="$2"
    local output_file="$RESULT_DIR/${test_name}.json"
    
    echo "[$(date '+%H:%M:%S')] 开始测试: $test_name"
    iperf3 -c "$TARGET" $iperf_opts -J > "$output_file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  -> 完成: $output_file"
    else
        echo "  -> 失败"
    fi
    sleep 2
}

# 测试场景
run_test "tcp_1stream" "-t 60"
run_test "tcp_4streams" "-t 60 -P 4"
run_test "tcp_8streams" "-t 60 -P 8"
run_test "udp_test" "-u -b 10G -t 30"
run_test "reverse_test" "-t 30 -R"
run_test "bidirectional_test" "-t 30 --bidir"

echo "=========================================="
echo "所有测试完成，开始生成报告..."
echo "=========================================="

# 生成 Markdown 报告
cat > "$REPORT" << 'HEADER'
# iperf3 网络压力测试报告

## 测试环境

| 项目 | 信息 |
|------|------|
| 测试日期 | 
HEADER

echo "| 测试日期 | $(date '+%Y-%m-%d %H:%M:%S') |" >> "$REPORT"
cat >> "$REPORT" << 'ENV'
| 源主机 | 172.19.0.171 |
| 目标主机 | 172.19.0.173 |
| iperf3 版本 | 
ENV

echo "| iperf3 版本 | $(iperf3 --version 2>&1 | head -1) |" >> "$REPORT"
cat >> "$REPORT" << 'TABLE'
| 操作系统 | $(uname -a) |
| 源主机 IP | $(ip addr show | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | head -3) |

## 测试结果汇总

TABLE

# 解析 JSON 结果并生成表格
echo "| 测试项 | 类型 | 并行流 | 持续时间 | 带宽 (Gbps) | 丢包率 | 抖动 (ms) |" >> "$REPORT"
echo "|--------|------|--------|----------|-------------|--------|-----------|" >> "$REPORT"

parse_json() {
    local json_file="$1"
    local test_name="$2"
    
    if [ ! -f "$json_file" ]; then
        return
    fi
    
    local type="TCP"
    local streams=1
    local duration=0
    local bandwidth=0
    local loss=0
    local jitter=0
    
    # 提取信息
    if echo "$test_name" | grep -q "udp"; then
        type="UDP"
    fi
    
    if echo "$test_name" | grep -q "4streams"; then
        streams=4
    elif echo "$test_name" | grep -q "8streams"; then
        streams=8
    fi
    
    if echo "$test_name" | grep -q "reverse"; then
        streams=1
    fi
    
    # 提取带宽 (转换为 Gbps)
    bandwidth=$(cat "$json_file" | grep -o '"bits_per_second":[0-9.]*' | head -1 | awk -F: '{print $2/1000000000}')
    bandwidth=$(printf "%.2f" $bandwidth)
    
    # 提取持续时间
    duration=$(cat "$json_file" | grep -o '"duration":[0-9.]*' | head -1 | awk -F: '{print $2}')
    duration=$(printf "%.0f" $duration)
    
    # 提取丢包率 (仅 UDP)
    if [ "$type" = "UDP" ]; then
        loss=$(cat "$json_file" | grep -o '"loss_percent":[0-9.]*' | head -1 | awk -F: '{print $2}')
        if [ -z "$loss" ]; then loss="0"; fi
        jitter=$(cat "$json_file" | grep -o '"jitter_ms":[0-9.]*' | head -1 | awk -F: '{print $2}')
        if [ -z "$jitter" ]; then jitter="0"; fi
    fi
    
    echo "| $test_name | $type | $streams | ${duration}s | $bandwidth | ${loss}% | $jitter |" >> "$REPORT"
}

for json in "$RESULT_DIR"/*.json; do
    if [ -f "$json" ]; then
        test_name=$(basename "$json" .json)
        parse_json "$json" "$test_name"
    fi
done

cat >> "$REPORT" << 'FOOTER'

## 详细结果

### TCP 单流测试 (60秒)
FOOTER

# 添加详细结果
if [ -f "$RESULT_DIR/tcp_1stream.json" ]; then
    echo '```' >> "$REPORT"
    cat "$RESULT_DIR/tcp_1stream.json" | grep -A 5 "summary" | head -20 >> "$REPORT"
    echo '```' >> "$REPORT"
fi

cat >> "$REPORT" << 'FOOTER2'

### TCP 4流测试 (60秒)

FOOTER2

if [ -f "$RESULT_DIR/tcp_4streams.json" ]; then
    echo '```' >> "$REPORT"
    cat "$RESULT_DIR/tcp_4streams.json" | grep -A 5 "summary" | head -20 >> "$REPORT"
    echo '```' >> "$REPORT"
fi

cat >> "$REPORT" << 'FOOTER3'

### UDP 测试 (30秒)

FOOTER3

if [ -f "$RESULT_DIR/udp_test.json" ]; then
    echo '```' >> "$REPORT"
    cat "$RESULT_DIR/udp_test.json" | grep -A 10 "summary" | head -30 >> "$REPORT"
    echo '```' >> "$REPORT"
fi

cat >> "$REPORT" << 'FOOTER4'

## 结论与建议

1. TCP 单流带宽反映了单连接的最大吞吐能力
2. 多流并行可以测试网络设备的负载均衡能力
3. UDP 测试的丢包率应低于 0.1% 为正常
4. 反向测试验证双向带宽是否对称

## 原始数据

所有 JSON 原始数据保存在: \`$RESULT_DIR\`

FOOTER4

echo ""
echo "=========================================="
echo "测试完成!"
echo "报告已生成: $REPORT"
echo "原始数据: $RESULT_DIR"
echo "=========================================="
