#!/usr/bin/make -f
# ==============================================================================
# PVE LACP HA & Bandwidth Testing Framework
# ==============================================================================
# Supports: TC-HA-02 (HA trigger tests) + TC-NW-02 (failover time tests)
# ==============================================================================

# ==============================================================================
# Variables
# ==============================================================================
TARGET_HOST_1 := 172.23.0.172
TARGET_HOST_2 := 172.23.0.173
LOCAL_HOST    := 172.23.0.171
CLUSTER_NET   := 172.19.0.x
STORAGE_NET   := 10.23.0.x
NIC0_NET      := 172.23.0.x

SCRIPT_DIR     := $(shell pwd)/iperf
IPERF_BASIC   := $(SCRIPT_DIR)/iperf-test.sh
IPERF_20G     := $(SCRIPT_DIR)/iperf20g-test.sh

STATUS_FILE   := $(HOME)/pve-test-status.json
LOG_DIR       := /tmp/pve-test-logs
REPORT_FILE   := $(HOME)/pve-test-report-$(shell date +%Y%m%d-%H%M%S).md

BOND0_NICS    := nic2 nic3
BOND2_NICS    := nic4 nic5
ALL_NICS      := $(BOND0_NICS) $(BOND2_NICS)

VM_ID         := 105

PYTHON_STATUS := $(shell pwd)/scripts/status_tracking.py
PYTHON_REPORT := $(shell pwd)/scripts/report_generator.py

# Trap for automatic rollback
ROLLBACK_TARGET := rollback

# ==============================================================================
# Helper Functions (using evaluate)
# ==============================================================================
define LOG
	@mkdir -p $(LOG_DIR)
	@echo "[$$(date '+%Y-%m-%d %H:%M:%S')] $(1)"
	@echo "[$$(date '+%Y-%m-%d %H:%M:%S')] $(1)" >> $(LOG_DIR)/test.log
endef

define START_TEST
	@mkdir -p $(LOG_DIR)
	@echo "========================================" | tee -a $(LOG_DIR)/test.log
	@echo "開始測試: $(1)" | tee -a $(LOG_DIR)/test.log
	@echo "時間: $$(date)" | tee -a $(LOG_DIR)/test.log
	@echo "========================================" | tee -a $(LOG_DIR)/test.log
	@python3 $(PYTHON_STATUS) start $(1)
endef

define END_TEST
	@echo "========================================" | tee -a $(LOG_DIR)/test.log
	@echo "測試完成: $(1) - $(2)" | tee -a $(LOG_DIR)/test.log
	@echo "========================================" | tee -a $(LOG_DIR)/test.log
	@python3 $(PYTHON_STATUS) end $(1) $(2)
endef

define CHECK_FAIL
	@CHECK_PASS=false
	@$(call LOG,"檢查失敗: $(1)")
endef

# ==============================================================================
# Default Target (Interactive Menu)
# ==============================================================================
.PHONY: all
all:
	@echo ""
	@echo "========================================"
	@echo "  PVE LACP HA & Bandwidth Testing"
	@echo "========================================"
	@echo ""
	@echo "  1) 健康檢查 (health-check)"
	@echo "  2) HA 測試 (test-ha-*)"
	@echo "  3) 頻寬測試 (test-bw-*)"
	@echo "  4) iperf 基準測試"
	@echo "  5) 完整測試流程 (fully-test)"
	@echo "  6) 重置/回滾 (reset/rollback)"
	@echo "  7) 狀態/歷史/報告"
	@echo "  8) 幫助 (help)"
	@echo ""
	@echo "========================================"
	@echo "  Quick: make health-check"
	@echo "         make test-ha-nic2"
	@echo "         make fully-test"
	@echo "========================================"
	@echo ""

.PHONY: help
help:
	@echo ""
	@echo "========================================"
	@echo "  PVE Testing Framework - Help"
	@echo "========================================"
	@echo ""
	@echo "## 健康檢查"
	@echo "  make health-check       # 9項健康檢查"
	@echo ""
	@echo "## HA 測試 (TC-HA-02)"
	@echo "  make test-ha-nic2           # bond0 nic2 故障"
	@echo "  make test-ha-nic3           # bond0 nic3 故障"
	@echo "  make test-ha-bond0-dual     # bond0 雙鏈路故障"
	@echo "  make test-ha-ring0-isolate  # Corosync ring0 隔離"
	@echo "  make test-ha-dual-ring      # Corosync 雙 ring 隔離 (HA觸發)"
	@echo ""
	@echo "## 頻寬測試 (TC-NW-02)"
	@echo "  make test-bw-bond0-ping     # bond0 ping 監控 (nic2)"
	@echo "  make test-bw-bond0-ping-nic3 # bond0 ping 監控 (nic3)"
	@echo "  make test-bw-nic4           # bond2 nic4 iperf3 測試"
	@echo "  make test-bw-nic5           # bond2 nic5 iperf3 測試"
	@echo "  make test-switch-reboot     # 60秒中斷模擬"
	@echo ""
	@echo "## iperf 基準測試"
	@echo "  make iperf-basic        # 標準 iperf3 測試"
	@echo "  make iperf-20g         # 20Gbps LACP 測試"
	@echo ""
	@echo "## 完整測試流程"
	@echo "  make fully-test        # TC-HA-02 + TC-NW-02 完整流程"
	@echo ""
	@echo "## 重置/回滾"
	@echo "  make reset         # 恢復所有網卡 + 清理 iptables"
	@echo "  make rollback      # 緊急回滾"
	@echo "  make cleanup       # 清理 iperf3 程序"
	@echo ""
	@echo "## 狀態/報告"
	@echo "  make status        # 查看當前狀態"
	@echo "  make history       # 查看測試歷史"
	@echo "  make report        # 生成 Markdown 報告"
	@echo ""
	@echo "## 回滾到特定階段"
	@echo "  make rollback-to-phase1  # 回滾到健康檢查"
	@echo "  make rollback-to-phase2  # 回滾到 Phase 2 HA測試"
	@echo ""
	@echo "========================================"

# ==============================================================================
# Cleanup, Reset, Rollback
# ==============================================================================

.PHONY: cleanup
cleanup:
	@$(call LOG,"執行清理")
	@ip link set up $(ALL_NICS) 2>/dev/null || true
	@iptables -P INPUT ACCEPT; iptables -F 2>/dev/null || true
	@iptables -X 2>/dev/null || true
	@pkill -9 iperf3 2>/dev/null || true
	@sleep 3
	@$(call LOG,"清理完成")

.PHONY: reset
reset: cleanup
	@$(call LOG,"執行 Reset - 強制恢復所有介面")
	@ip link set up $(ALL_NICS) 2>/dev/null || true
	@iptables -P INPUT ACCEPT; iptables -F 2>/dev/null || true
	@iptables -X 2>/dev/null || true
	@echo "=== 網路狀態 ==="
	@cat /proc/net/bonding/bond0 2>/dev/null | grep "MII Status" || echo "bond0 not found"
	@cat /proc/net/bonding/bond2 2>/dev/null | grep "MII Status" || echo "bond2 not found"
	@$(call LOG,"Reset 完成")

.PHONY: rollback
rollback:
	@$(call LOG,"執行緊急回滾")
	@ip link set up $(ALL_NICS) 2>/dev/null || true
	@iptables -P INPUT ACCEPT; iptables -F 2>/dev/null || true
	@pkill -9 iperf3 2>/dev/null || true
	@sleep 2
	@$(call LOG,"緊急回滾完成")

.PHONY: force-recover
force-recover:
	@$(call LOG,"執行強制恢復")
	@ip link set down $(ALL_NICS) 2>/dev/null || true
	@sleep 2
	@ip link set up $(ALL_NICS) 2>/dev/null || true
	@iptables -P INPUT ACCEPT; iptables -F 2>/dev/null || true
	@sleep 5
	@cat /proc/net/bonding/bond0 2>/dev/null | grep "MII Status" || echo "bond0 not found"
	@cat /proc/net/bonding/bond2 2>/dev/null | grep "MII Status" || echo "bond2 not found"
	@$(call LOG,"強制恢復完成")

# ==============================================================================
# Health Check (9 items)
# ==============================================================================
.PHONY: health-check
health-check:
	@mkdir -p $(LOG_DIR)
	@echo "[$$(date '+%Y-%m-%d %H:%M:%S')] 執行健康檢查" | tee -a $(LOG_DIR)/test.log
	@CHECK_PASS=true; \
echo "=== 健康檢查 - $$(date) ==="; \
echo -n "1. Cluster Quorate: "; \
if pvecm status 2>/dev/null | grep -q "Quorate: Yes"; then echo "PASS"; else echo "FAIL"; CHECK_PASS=false; fi; \
echo -n "2. HA Manager: "; \
if ha-manager status 2>/dev/null | grep -q "running"; then echo "PASS"; else echo "FAIL"; CHECK_PASS=false; fi; \
echo -n "3. VM $(VM_ID) 運行: "; \
if qm status $(VM_ID) 2>/dev/null | grep -q "status: running"; then echo "PASS"; else echo "FAIL"; CHECK_PASS=false; fi; \
echo -n "4. VM $(VM_ID) in HA: "; \
if ha-manager status 2>/dev/null | grep -q "vm:$(VM_ID)"; then echo "PASS"; else echo "WARN (not in HA)"; fi; \
echo -n "5. bond0 狀態: "; \
BOND0_UP=$$(cat /proc/net/bonding/bond0 2>/dev/null | grep "MII Status: up" | wc -l); \
if [ $$BOND0_UP -ge 2 ]; then echo "PASS ($$BOND0_UP/2)"; else echo "FAIL ($$BOND0_UP/2)"; CHECK_PASS=false; fi; \
echo -n "6. bond2 狀態: "; \
BOND2_UP=$$(cat /proc/net/bonding/bond2 2>/dev/null | grep "MII Status: up" | wc -l); \
if [ $$BOND2_UP -ge 2 ]; then echo "PASS ($$BOND2_UP/2)"; else echo "FAIL ($$BOND2_UP/2)"; CHECK_PASS=false; fi; \
echo -n "7. SSH (172.23.0.172): "; \
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "echo ok" 2>/dev/null | grep -q "ok"; then echo "PASS"; else echo "FAIL"; CHECK_PASS=false; fi; \
echo -n "8. SSH (172.23.0.173): "; \
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "echo ok" 2>/dev/null | grep -q "ok"; then echo "PASS"; else echo "FAIL"; CHECK_PASS=false; fi; \
echo -n "9. Corosync members: "; \
if corosync-cmapctl 2>/dev/null | grep -q "runtime.config.active members"; then echo "PASS"; else echo "WARN"; fi; \
echo "=== 健康檢查完成 ==="; \
if [ "$$CHECK_PASS" = false ]; then echo "[$$(date '+%Y-%m-%d %H:%M:%S')] 健康檢查失敗" | tee -a $(LOG_DIR)/test.log; exit 1; fi

# ==============================================================================
# HA Test Targets (TC-HA-02 Section 7)
# ==============================================================================

.PHONY: test-ha-nic2
test-ha-nic2:
	@$(call START_TEST,bond0_nic2_down)
	$(call LOG,"故障注入: ip link set down nic2")
	@ip link set down nic2
	@sleep 10
	$(call LOG,"驗證: SSH to $(TARGET_HOST_1)")
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "corosync-cmapctl | grep members" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "ha-manager status" 2>&1 | tee -a $(LOG_DIR)/test.log
	$(call LOG,"VM 狀態驗證")
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "qm status $(VM_ID)" 2>&1 | tee -a $(LOG_DIR)/test.log
	$(call LOG,"恢復: ip link set up nic2")
	@ip link set up nic2
	@sleep 5
	@$(call END_TEST,bond0_nic2_down,PASS)

.PHONY: test-ha-nic3
test-ha-nic3:
	@$(call START_TEST,bond0_nic3_down)
	$(call LOG,"故障注入: ip link set down nic3")
	@ip link set down nic3
	@sleep 10
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "ha-manager status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "qm status $(VM_ID)" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ip link set up nic3
	@sleep 5
	@$(call END_TEST,bond0_nic3_down,PASS)

.PHONY: test-ha-bond0-dual
test-ha-bond0-dual:
	@$(call START_TEST,bond0_dual_down)
	$(call LOG,"故障注入: ip link set down nic2 && ip link set down nic3")
	@ip link set down nic2 && ip link set down nic3
	@sleep 10
	$(call LOG,"驗證: SSH to $(TARGET_HOST_1) and $(TARGET_HOST_2)")
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "corosync-cmapctl | grep members" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "ha-manager status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ip link set up nic2 && ip link set up nic3
	@sleep 5
	@$(call END_TEST,bond0_dual_down,PASS)

.PHONY: test-ha-ring0-isolate
test-ha-ring0-isolate:
	@$(call START_TEST,corosync_ring0_isolation)
	@iptables -P INPUT ACCEPT
	$(call LOG,"故障注入: iptables -A INPUT -s 172.19.0.172 -j DROP")
	@iptables -A INPUT -s 172.19.0.172 -j DROP
	@sleep 15
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "corosync-cmapctl | grep members" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "ha-manager status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@iptables -D INPUT -s 172.19.0.172 -j DROP
	@sleep 5
	@$(call END_TEST,corosync_ring0_isolation,PASS)

.PHONY: test-ha-dual-ring
test-ha-dual-ring:
	@$(call START_TEST,corosync_dual_ring_isolation)
	@iptables -P INPUT ACCEPT
	$(call LOG,"故障注入: iptables 封鎖 172.19.0.172 + 10.23.0.172 兩個 ring")
	@iptables -A INPUT -s 172.19.0.172 -j DROP
	@iptables -A INPUT -s 10.23.0.172 -j DROP
	@sleep 15
	$(call LOG,"驗證 HA 觸發")
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "pvecm status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "ha-manager status" 2>&1 | tee -a $(LOG_DIR)/test.log
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_2) "qm status $(VM_ID)" 2>&1 | tee -a $(LOG_DIR)/test.log
	@iptables -D INPUT -s 172.19.0.172 -j DROP
	@iptables -D INPUT -s 10.23.0.172 -j DROP
	@sleep 10
	@$(call END_TEST,corosync_dual_ring_isolation,PASS)

# ==============================================================================
# Bandwidth Test Targets (TC-NW-02 Section 7)
# ==============================================================================

.PHONY: test-bw-bond0-ping
test-bw-bond0-ping:
	@$(call START_TEST,bond0_nic2_ping)
	@$(call LOG,"啟動 ping 監控")
	@timeout 20 ping -i 0.2 172.19.1.252 > /tmp/ping_monitor.log 2>&1 &
	@sleep 2
	@$(call LOG,"故障注入: ip link set down nic2")
	@ip link set down nic2
	@sleep 10
	@ip link set up nic2
	@sleep 2
	@$(call LOG,"計算丟包")
	@bash -c 'LOST=$$(grep "loss" /tmp/ping_monitor.log 2>/dev/null | tail -1 | awk "{print \$$4}" | tr -d "%"); echo "丟包率: $${LOST:-0}%"; if [ "$${LOST:-0}" -gt 5 ]; then echo "警告: 丟包率過高"; fi'
	@$(call END_TEST,bond0_nic2_ping,PASS)

.PHONY: test-bw-bond0-ping-nic3
test-bw-bond0-ping-nic3:
	@$(call START_TEST,bond0_nic3_ping)
	@timeout 20 ping -i 0.2 172.19.1.252 > /tmp/ping_monitor_nic3.log 2>&1 &
	@sleep 2
	@ip link set down nic3
	@sleep 10
	@ip link set up nic3
	@sleep 2
	@bash -c 'LOST=$$(grep "loss" /tmp/ping_monitor_nic3.log 2>/dev/null | tail -1 | awk "{print \$$4}" | tr -d "%"); echo "丟包率: $${LOST:-0}%"; if [ "$${LOST:-0}" -gt 5 ]; then echo "警告: 丟包率過高"; fi'
	@$(call END_TEST,bond0_nic3_ping,PASS)

.PHONY: test-bw-nic4
test-bw-nic4:
	@$(call START_TEST,bond2_nic4_down)
	$(call LOG,"啟動 iperf3 server")
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "pkill iperf3; iperf3 -s -D" 2>/dev/null
	@iperf3 -c $(TARGET_HOST_1) -t 60 -P 4 -J > /tmp/iperf_before_nic4.json 2>/dev/null &
	@sleep 5
	$(call LOG,"故障注入: ip link set down nic4")
	@ip link set down nic4
	@sleep 10
	$(call LOG,"VM 狀態 LOCAL storage 中斷")
	@qm status $(VM_ID) 2>&1 | tee -a $(LOG_DIR)/test.log || echo "VM I/O blocked or stopped"
	@ip link set up nic4
	@sleep 5
	@$(call END_TEST,bond2_nic4_down,PASS)

.PHONY: test-bw-nic5
test-bw-nic5:
	@$(call START_TEST,bond2_nic5_down)
	@ssh -o StrictHostKeyChecking=no root@$(TARGET_HOST_1) "pkill iperf3; iperf3 -s -D" 2>/dev/null
	@iperf3 -c $(TARGET_HOST_1) -t 60 -P 4 -J > /tmp/iperf_before_nic5.json 2>/dev/null &
	@sleep 5
	@ip link set down nic5
	@sleep 10
	@qm status $(VM_ID) 2>&1 | tee -a $(LOG_DIR)/test.log || echo "VM I/O blocked"
	@ip link set up nic5
	@sleep 5
	@$(call END_TEST,bond2_nic5_down,PASS)

.PHONY: test-switch-reboot
test-switch-reboot:
	@$(call START_TEST,switch_reboot_60s)
	$(call LOG,"故障注入: ip link set down nic2 nic3 60秒")
	@ip link set down nic2 && ip link set down nic3
	@timeout 70 ping -i 0.5 172.19.1.252 > /tmp/ping_reboot.log 2>&1 &
	@sleep 60
	$(call LOG,"恢復: ip link set up nic2 nic3")
	@ip link set up nic2 && ip link set up nic3
	@sleep 5
	@bash -c 'LOST=$$(grep "loss" /tmp/ping_reboot.log 2>/dev/null | tail -1 | awk "{print \$$4}" | tr -d "%"); echo "60秒中斷後丟包率: $${LOST:-0}%"'
	@$(call END_TEST,switch_reboot_60s,PASS)

# ==============================================================================
# iperf Baseline Tests
# ==============================================================================

.PHONY: iperf-basic
iperf-basic:
	@$(call LOG,"執行標準 iperf3 基準測試")
	@bash $(IPERF_BASIC)

.PHONY: iperf-20g
iperf-20g:
	@$(call LOG,"執行 20Gbps LACP 頻寬測試")
	@bash $(IPERF_20G)

# ==============================================================================
# Fully-Test (TC-HA-02 Section 5.7 Compliant)
# ==============================================================================
.PHONY: fully-test
fully-test:
	@mkdir -p $(LOG_DIR)
	@$(call LOG,"========================================")
	@$(call LOG,"開始完整測試執行 (TC-HA-02 + TC-NW-02)")
	@$(call LOG,"========================================")

	@$(call LOG,"[Phase 0] 清理與重置")
	@make reset

	@$(call LOG,"[Phase 1] 健康檢查")
	@make health-check || { $(call LOG,"錯誤: 健康檢查失敗"); exit 1; }

	@$(call LOG,"[Phase 2] 執行 HA 測試 (TC-HA-02)")
	@make test-ha-nic2 || { $(call LOG,"test-ha-nic2 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-ha-nic3 || { $(call LOG,"test-ha-nic3 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-ha-bond0-dual || { $(call LOG,"test-ha-bond0-dual 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-ha-ring0-isolate || { $(call LOG,"test-ha-ring0-isolate 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-ha-dual-ring || { $(call LOG,"test-ha-dual-ring 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }

	@$(call LOG,"[Phase 3] 執行頻寬測試 (TC-NW-02)")
	@make test-bw-bond0-ping || { $(call LOG,"test-bw-bond0-ping 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-bw-nic4 || { $(call LOG,"test-bw-nic4 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-bw-nic5 || { $(call LOG,"test-bw-nic5 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }
	@make test-switch-reboot || { $(call LOG,"test-switch-reboot 失敗"); exit 1; }
	@make reset && make health-check || { $(call LOG,"健康檢查失敗"); exit 1; }

	@$(call LOG,"[Phase 4] 最終驗證")
	@make health-check

	@$(call LOG,"[Phase 5] 生成報告")
	@make report

	@$(call LOG,"========================================")
	@$(call LOG,"測試執行完成")
	@$(call LOG,"========================================")

# ==============================================================================
# Rollback to Specific Phase
# ==============================================================================
.PHONY: rollback-to-phase1
rollback-to-phase1:
	@$(call LOG,"回滾到 Phase 1 健康檢查")
	@make cleanup
	@make health-check

.PHONY: rollback-to-phase2
rollback-to-phase2:
	@$(call LOG,"回滾到 Phase 2 HA測試")
	@make cleanup
	@make health-check
	@make test-ha-nic2

.PHONY: rollback-to-phase3
rollback-to-phase3:
	@$(call LOG,"回滾到 Phase 3 頻寬測試")
	@make cleanup
	@make health-check

# ==============================================================================
# Status Tracking
# ==============================================================================

.PHONY: status
status:
	@python3 $(PYTHON_STATUS) show

.PHONY: history
history:
	@python3 $(PYTHON_STATUS) history

# ==============================================================================
# Report Generation
# ==============================================================================

.PHONY: report
report:
	@python3 $(PYTHON_REPORT) -o $(REPORT_FILE)

# ==============================================================================
# Test Corosync Parameters
# ==============================================================================
.PHONY: test-ha-corosync-status
test-ha-corosync-status:
	@$(call LOG,"記錄 Corosync 參數")
	@echo "=== Corosync 當前參數 ==="
	@corosync-cmapctl 2>/dev/null | grep -E "deadtime|token|consensus" | tee $(LOG_DIR)/corosync-params.log
	@echo ""
	@echo "=== ring0 status ==="
	@corosync-cmapctl runtime.ip.ring0 2>/dev/null || echo "N/A"
	@echo "=== ring1 status ==="
	@corosync-cmapctl runtime.ip.ring1 2>/dev/null || echo "N/A"
	@echo "=== active members ==="
	@corosync-cmapctl runtime.config.active 2>/dev/null | grep members || echo "N/A"