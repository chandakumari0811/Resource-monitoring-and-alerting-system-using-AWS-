import boto3
import requests
from datetime import datetime, timedelta, timezone

AWS_REGION = "ap-south-1"
INSTANCE_IDS = ["i-035952da15a52c5d9"]  
WARNING_THRESHOLD = 70
CRITICAL_THRESHOLD = 90
SLACK_WEBHOOK = "https://hooks.slack.com/services/xyz"  # "fake_url"

cw = boto3.client("cloudwatch", region_name=AWS_REGION)

def fetch_cpu_utilization(instance_id):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=5)
    resp = cw.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start,
        EndTime=end,
        Period=60,
        Statistics=["Average"]
    )
    datapoints = resp.get("Datapoints", [])
    if not datapoints:
        return None
    latest = max(datapoints, key=lambda x: x["Timestamp"])
    return latest["Average"]

def send_slack_alert(level, instance_id, value):
    text = f"*{level.upper()} ALERT* EC2 {instance_id} CPU={value:.2f}%"
    payload = {"text": text}
    r = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
    r.raise_for_status()

def lambda_handler(event, context):
    results = []
    for iid in INSTANCE_IDS:
        value = fetch_cpu_utilization(iid)
        if value is None:
            results.append(f"No data for {iid}")
            continue
        if value >= CRITICAL_THRESHOLD:
            send_slack_alert("critical", iid, value)
            results.append(f"{iid} CRITICAL {value:.2f}%")
        elif value >= WARNING_THRESHOLD:
            send_slack_alert("warning", iid, value)
            results.append(f"{iid} WARNING {value:.2f}%")
        else:
            results.append(f"{iid} OK {value:.2f}%")
    return {"status": "done", "results": results}
