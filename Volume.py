
import requests

# ONTAP cluster details
CLUSTER = "https://192.168.0.101"   # no tab or spaces
#USER = "admin"
#PASS = "Netapp1!"
header = {"Authorization": "Basic YWRtaW46TmV0YXBwMSE="}

# Volume details
payload = {
    "name": "vol_4",
    "svm": {"name": "svm1"},
    "aggregates": [{"name": "cluster1_01_SSD_1"}],
    "size": 1073741824  # 1 GiB in bytes
}

url = f"{CLUSTER}/api/storage/volumes"

# add timeout and better error handling
try:
    r = requests.post(url, json=payload, headers=header, verify=False, timeout=15)
    print("Status:", r.status_code)
    print("Response:", r.json() if r.headers.get("Content-Type","").startswith("application/json") else r.text)
except requests.RequestException as e:
    print("Connection error:", e)
