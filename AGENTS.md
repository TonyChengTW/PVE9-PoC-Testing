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

## Workflow & Verification
- **Execution**: Scripts run `iperf3` on the local host against targets.
- **Output**: JSON raw data is saved to timestamped directories in `$HOME`; summary Markdown reports are generated in `$HOME`.

## Key Documentation
- **Test Plans**: `docs/codimd/`
- **Test Specs**: `docs/superpowers/spec/`
- **Environment Setup**: `docs/codimd/環境說明_Environment_Setup.md`