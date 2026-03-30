
#!/usr/bin/env python3
"""
NetApp ONTAP Health Check Script
=================================
Author      : Storage Admin
Version     : 1.0.0
Description : Performs comprehensive health checks on a NetApp ONTAP cluster
              using the ONTAP REST API. Covers cluster, nodes, aggregates,
              volumes, SVMs, disks, and network interfaces.

Usage       : python3 netapp_health_check.py
"""

import requests
import json
import sys
import urllib3
from datetime import datetime

# ─────────────────────────────────────────────
# Suppress SSL warnings for self-signed certs
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# CLUSTER CREDENTIALS (hardcoded for lab use)
# ─────────────────────────────────────────────
CLUSTER_IP  = "192.168.0.101"
USERNAME    = "admin"
PASSWORD    = "Netapp1!"
BASE_URL    = f"https://{CLUSTER_IP}/api"
VERIFY_SSL  = False   # Set True in production with valid certs

# ─────────────────────────────────────────────
# ANSI Color Codes for terminal output
# ─────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}[PASS]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
INFO = f"{CYAN}[INFO]{RESET}"


# ─────────────────────────────────────────────
# REST API Helper
# ─────────────────────────────────────────────
def api_get(endpoint: str, params: dict = None) -> dict | None:
    """
    Performs a GET request to the ONTAP REST API.
    Returns parsed JSON response or None on error.
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            params=params,
            verify=VERIFY_SSL,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"{FAIL} Cannot connect to {CLUSTER_IP}. Check IP and reachability.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"{WARN} Request timed out for endpoint: {endpoint}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"{WARN} HTTP error for {endpoint}: {e}")
        return None


def section(title: str):
    """Prints a formatted section header."""
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


# ─────────────────────────────────────────────
# Health Check Functions
# ─────────────────────────────────────────────

def check_cluster_info():
    """Displays basic cluster identity information."""
    section("1. CLUSTER INFORMATION")
    data = api_get("/cluster")
    if not data:
        print(f"{FAIL} Could not retrieve cluster information.")
        return

    print(f"{INFO} Cluster Name   : {data.get('name', 'N/A')}")
    print(f"{INFO} ONTAP Version  : {data.get('version', {}).get('full', 'N/A')}")
    print(f"{INFO} Serial Number  : {data.get('serial_number', 'N/A')}")
    print(f"{INFO} Location       : {data.get('location', 'N/A')}")
    print(f"{INFO} Contact        : {data.get('contact', 'N/A')}")


def check_nodes():
    """Checks node health and uptime."""
    section("2. NODE HEALTH")
    data = api_get("/cluster/nodes", params={"fields": "name,state,uptime,health"})
    if not data or not data.get("records"):
        print(f"{FAIL} No node data returned.")
        return

    all_healthy = True
    for node in data["records"]:
        name    = node.get("name", "N/A")
        state   = node.get("state", "unknown")
        health  = node.get("health", False)
        uptime  = node.get("uptime", 0)

        uptime_days = uptime // 86400
        status  = PASS if health and state == "online" else FAIL
        if not health or state != "online":
            all_healthy = False

        print(f"  {status} Node: {name:<20} State: {state:<10} Health: {str(health):<6} Uptime: {uptime_days} days")

    if all_healthy:
        print(f"\n  {PASS} All nodes are healthy.")
    else:
        print(f"\n  {FAIL} One or more nodes have health issues!")


def check_aggregates():
    """Checks aggregate state and space utilization."""
    section("3. AGGREGATE HEALTH & SPACE")
    data = api_get("/storage/aggregates", params={"fields": "name,state,space,data_encryption,node"})
    if not data or not data.get("records"):
        print(f"{FAIL} No aggregate data returned.")
        return

    print(f"  {'Aggregate':<30} {'Node':<20} {'State':<10} {'Used%':>6}  {'Status'}")
    print(f"  {'-'*80}")

    for aggr in data["records"]:
        name  = aggr.get("name", "N/A")
        state = aggr.get("state", "unknown")
        node  = aggr.get("node", {}).get("name", "N/A")
        space = aggr.get("space", {})
        total = space.get("block_storage", {}).get("size", 0)
        used  = space.get("block_storage", {}).get("used", 0)

        used_pct = round((used / total) * 100, 1) if total > 0 else 0

        if state != "online":
            status = FAIL
        elif used_pct >= 90:
            status = FAIL
        elif used_pct >= 80:
            status = WARN
        else:
            status = PASS

        print(f"  {name:<30} {node:<20} {state:<10} {used_pct:>5}%  {status}")


def check_volumes():
    """Checks volume state and space utilization."""
    section("4. VOLUME HEALTH & SPACE")
    data = api_get("/storage/volumes", params={
        "fields": "name,state,space,svm,style",
        "max_records": 200
    })
    if not data or not data.get("records"):
        print(f"{FAIL} No volume data returned.")
        return

    issues = 0
    print(f"  {'Volume':<30} {'SVM':<20} {'State':<10} {'Used%':>6}  {'Status'}")
    print(f"  {'-'*80}")

    for vol in data["records"]:
        name  = vol.get("name", "N/A")
        state = vol.get("state", "unknown")
        svm   = vol.get("svm", {}).get("name", "N/A")
        space = vol.get("space", {})
        total = space.get("size", 0)
        used  = space.get("used", 0)

        # Skip root/temp volumes
        if name.endswith("_root") or name == "vol0":
            continue

        used_pct = round((used / total) * 100, 1) if total > 0 else 0

        if state != "online":
            status = FAIL
            issues += 1
        elif used_pct >= 95:
            status = FAIL
            issues += 1
        elif used_pct >= 85:
            status = WARN
        else:
            status = PASS

        print(f"  {name:<30} {svm:<20} {state:<10} {used_pct:>5}%  {status}")

    print(f"\n  {PASS if issues == 0 else FAIL} Total volumes with issues: {issues}")


def check_svms():
    """Checks SVM (Storage Virtual Machine) state."""
    section("5. SVM (VSERVER) STATE")
    data = api_get("/svm/svms", params={"fields": "name,state,subtype"})
    if not data or not data.get("records"):
        print(f"{FAIL} No SVM data returned.")
        return

    for svm in data["records"]:
        name    = svm.get("name", "N/A")
        state   = svm.get("state", "unknown")
        subtype = svm.get("subtype", "N/A")
        status  = PASS if state == "running" else FAIL
        print(f"  {status} SVM: {name:<25} State: {state:<12} Type: {subtype}")


def check_disks():
    """Checks for broken or failed disks."""
    section("6. DISK HEALTH")
    data = api_get("/storage/disks", params={"fields": "name,state,type,node"})
    if not data or not data.get("records"):
        print(f"{FAIL} No disk data returned.")
        return

    broken   = []
    spare    = 0
    total    = len(data["records"])

    for disk in data["records"]:
        state = disk.get("state", "unknown")
        if state in ("broken", "failed", "unfail"):
            broken.append(disk.get("name", "N/A"))
        elif state == "spare":
            spare += 1

    print(f"  {INFO} Total Disks  : {total}")
    print(f"  {INFO} Spare Disks  : {spare}")

    if broken:
        print(f"  {FAIL} Broken/Failed Disks ({len(broken)}): {', '.join(broken)}")
    else:
        print(f"  {PASS} No broken or failed disks found.")

    if spare == 0:
        print(f"  {WARN} No spare disks available. Consider adding spares.")


def check_network_interfaces():
    """Checks LIF (Logical Interface) operational status."""
    section("7. NETWORK INTERFACE (LIF) HEALTH")
    data = api_get("/network/ip/interfaces", params={
        "fields": "name,state,ip,svm,enabled,location"
    })
    if not data or not data.get("records"):
        print(f"{FAIL} No LIF data returned.")
        return

    issues = 0
    print(f"  {'LIF Name':<30} {'SVM':<20} {'IP Address':<18} {'State':<10} {'Status'}")
    print(f"  {'-'*90}")

    for lif in data["records"]:
        name    = lif.get("name", "N/A")
        state   = lif.get("state", "unknown")
        enabled = lif.get("enabled", False)
        svm     = lif.get("svm", {}).get("name", "Cluster")
        ip      = lif.get("ip", {}).get("address", "N/A")

        if state == "up" and enabled:
            status = PASS
        else:
            status = FAIL
            issues += 1

        print(f"  {name:<30} {svm:<20} {ip:<18} {state:<10} {status}")

    print(f"\n  {PASS if issues == 0 else FAIL} LIFs with issues: {issues}")


def check_cluster_alerts():
    """Checks for active EMS alerts or AutoSupport issues."""
    section("8. EMS / CLUSTER ALERTS")
    data = api_get("/support/ems/messages", params={
        "fields":      "message,time,severity,node",
        "severity":    "error,alert,critical,emergency",
        "max_records": 10,
        "order_by":    "time desc"
    })

    if not data or not data.get("records"):
        print(f"  {PASS} No critical EMS alerts found.")
        return

    print(f"  {WARN} Recent EMS alerts (last 10):\n")
    print(f"  {'Time':<22} {'Severity':<12} {'Node':<20} {'Message'}")
    print(f"  {'-'*90}")

    for msg in data["records"]:
        time_str = msg.get("time", "N/A")
        severity = msg.get("severity", "N/A")
        node     = msg.get("node", {}).get("name", "N/A")
        message  = msg.get("message", {}).get("name", "N/A")
        color    = RED if severity in ("critical", "emergency") else YELLOW
        print(f"  {time_str:<22} {color}{severity:<12}{RESET} {node:<20} {message}")


def print_summary(start_time: datetime):
    """Prints the health check summary footer."""
    elapsed = (datetime.now() - start_time).seconds
    section("HEALTH CHECK COMPLETE")
    print(f"  {INFO} Script finished in {elapsed} second(s).")
    print(f"  {INFO} Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {INFO} Target    : {CLUSTER_IP}\n")


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
def main():
    start_time = datetime.now()
    print(f"\n{BOLD}{CYAN}NetApp ONTAP Health Check{RESET}")
    print(f"Target   : {CLUSTER_IP}")
    print(f"Started  : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    check_cluster_info()
    check_nodes()
    check_aggregates()
    check_volumes()
    check_svms()
    check_disks()
    check_network_interfaces()
    check_cluster_alerts()
    print_summary(start_time)


if __name__ == "__main__":
    main()
