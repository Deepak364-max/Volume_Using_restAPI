import requests

# ONTAP cluster details
CLUSTER = "https://	192.168.0.101"
USER = "admin"
PASS = "Netapp1!"

# Volume details
payload = {
    "name": "vol_3",
    "svm": {"name": "svm1"},
    "aggregates": [{"name": "cluster1_01_SSD_1"}],
    "size": 1073741824  # 1 GiB in bytes
}

# Send POST request
url = f"{CLUSTER}/api/storage/volumes"
response = requests.post(url, json=payload, auth=(USER, PASS), verify=False)

print("Status:", response.status_code)
print("Response:", response.json())

