# Volume Creation Using NetApp ONTAP REST API

## Overview

This project provides a Python script (`Volume.py`) that automates the creation of a storage volume on a NetApp ONTAP cluster using its REST API. It demonstrates how to interact with the ONTAP REST API to perform storage provisioning tasks programmatically.

## What It Does

The script sends an HTTP `POST` request to the ONTAP cluster's `/api/storage/volumes` endpoint to create a new FlexVol volume with the specified configuration:

- **Volume name** – the name to assign to the new volume
- **SVM** – the Storage Virtual Machine (SVM) that will own the volume
- **Aggregate** – the underlying physical storage aggregate to place the volume on
- **Size** – the provisioned capacity of the volume (in bytes)

## Prerequisites

- Python 3.x
- [`requests`](https://pypi.org/project/requests/) library (`pip install requests`)
- Access to a NetApp ONTAP cluster (9.6 or later recommended) with REST API enabled
- Valid ONTAP credentials with sufficient privileges to create volumes

## Configuration

Before running the script, update the following variables inside `Volume.py`:

| Variable | Description | Example |
|---|---|---|
| `CLUSTER` | Base URL of your ONTAP cluster | `https://192.168.0.101` |
| `header` | Base64-encoded `user:password` in the `Authorization` header | See note below |
| `payload["name"]` | Name for the new volume | `vol_4` |
| `payload["svm"]["name"]` | SVM that will own the volume | `svm1` |
| `payload["aggregates"][0]["name"]` | Aggregate to place the volume on | `cluster1_01_SSD_1` |
| `payload["size"]` | Volume size in bytes | `1073741824` (1 GiB) |

> **Generating the Authorization header value:**
> The `Authorization` header uses HTTP Basic Auth encoded as Base64.
> ```bash
> echo -n "admin:YourPassword" | base64
> ```
> Paste the result as the value after `"Basic "` in the header dictionary.
> **Note:** The command above is for illustration only. Typing passwords directly on the command line may expose them in your shell history. In production, use `read -s` or a secrets manager to handle credentials securely.

## Usage

```bash
python Volume.py
```

### Example Output

```
Status: 201
Response: {'job': {'uuid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', '_links': {...}}}
```

A `201 Created` status indicates the volume was successfully created. The response includes a job UUID that can be used to track the provisioning job status via the ONTAP REST API.

## Notes

- **⚠️ SSL Warning:** SSL certificate verification is disabled (`verify=False`) in this script. This exposes connections to man-in-the-middle attacks and **must not be used in production**. For production environments, provide a valid CA-signed certificate and set `verify=True` or pass the path to your CA bundle (e.g., `verify="/path/to/ca-bundle.crt"`).
- The script has a 15-second timeout on the HTTP request to avoid hanging indefinitely on network issues.
