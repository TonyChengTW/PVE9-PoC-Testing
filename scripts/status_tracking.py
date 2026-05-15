#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

STATUS_FILE = os.path.expanduser("~/pve-test-status.json")

def load_data():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'last_updated': '',
        'status': 'IDLE',
        'current_test': None,
        'last_run': {},
        'history': [],
        'tests': {}
    }

def save_data(data):
    data['last_updated'] = datetime.now().isoformat()
    with open(STATUS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def cmd_start(test_name):
    data = load_data()
    data['status'] = 'RUNNING'
    data['current_test'] = test_name
    if 'last_run' not in data:
        data['last_run'] = {}
    data['last_run']['test'] = test_name
    data['last_run']['start'] = datetime.now().isoformat()
    save_data(data)
    print(f"[STATUS] Test started: {test_name}")

def cmd_end(test_name, result):
    data = load_data()
    end_time = datetime.now().isoformat()
    start_time = data.get('last_run', {}).get('start', end_time)

    data['status'] = 'IDLE'
    data['current_test'] = None
    data['last_run']['end'] = end_time
    data['last_run']['result'] = result

    history_entry = {
        'test': test_name,
        'start': start_time,
        'end': end_time,
        'status': result
    }
    data['history'].append(history_entry)

    if test_name not in data['tests']:
        data['tests'][test_name] = {'runs': 0, 'passes': 0, 'failures': 0}
    data['tests'][test_name]['runs'] += 1
    if result == 'PASS':
        data['tests'][test_name]['passes'] += 1
    else:
        data['tests'][test_name]['failures'] += 1

    save_data(data)
    print(f"[STATUS] Test ended: {test_name} - {result}")

def cmd_show():
    data = load_data()
    print("=== PVE Test Status ===")
    print(f"Status: {data.get('status', 'N/A')}")
    print(f"Current Test: {data.get('current_test', 'None')}")
    print(f"Last Updated: {data.get('last_updated', 'N/A')}")
    last_run = data.get('last_run', {})
    if last_run:
        print(f"Last Run: {last_run.get('test', 'N/A')} - {last_run.get('result', 'N/A')}")
    print("=======================")

def cmd_history():
    data = load_data()
    print("=== Test History ===")
    for h in data.get('history', []):
        print(f"{h['test']}: {h['status']} ({h['start']} - {h.get('end', 'N/A')})")
    print("")
    print("=== Test Statistics ===")
    for t, s in data.get('tests', {}).items():
        rate = (s['passes'] / s['runs'] * 100) if s['runs'] > 0 else 0
        print(f"{t}: runs={s['runs']} passes={s['passes']} failures={s['failures']} ({rate:.1f}%)")

def main():
    if len(sys.argv) < 2:
        cmd_show()
        return

    cmd = sys.argv[1]

    if cmd == 'start' and len(sys.argv) >= 3:
        cmd_start(sys.argv[2])
    elif cmd == 'end' and len(sys.argv) >= 4:
        cmd_end(sys.argv[2], sys.argv[3])
    elif cmd == 'show':
        cmd_show()
    elif cmd == 'history':
        cmd_history()
    else:
        print(f"Usage: {sys.argv[0]} [start <name>|end <name> <result>|show|history]")
        sys.exit(1)

if __name__ == '__main__':
    main()