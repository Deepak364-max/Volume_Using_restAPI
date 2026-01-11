import requests

# ONTAP cluster details
CLUSTER = "https://<ONTAP_CLUSTER_IP>"
USER = "admin"
PASS = "your_password"

# Volume details
payload = {
    "name": "vol_demo",
    "svm": {"name": "vs1"},
    "aggregates": [{"name": "aggr1"}],
    "size": 1073741824  # 1 GiB in bytes
}

# Send POST request
url = f"{CLUSTER}/api/storage/volumes"
response = requests.post(url, json=payload, auth=(USER, PASS), verify=False)

print("Status:", response.status_code)
print("Response:", response.json())
