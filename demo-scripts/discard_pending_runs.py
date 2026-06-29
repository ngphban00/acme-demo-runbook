"""Discard all pending/planned runs on staging workspace after make reset."""
import json, os, sys, time, urllib.request, urllib.error

ORG       = "ngphban"
WORKSPACE = "acme-apps-azure-staging"
DISCARD_STATES = {"pending", "plan_queued", "planning", "planned", "needs_confirmation", "cost_estimating", "cost_estimated", "policy_checking", "policy_override"}

creds_path = os.path.expanduser("~/.terraform.d/credentials.tfrc.json")
try:
    token = json.load(open(creds_path))["credentials"]["app.terraform.io"]["token"]
except (KeyError, FileNotFoundError) as e:
    print(f"  ✗ Cannot read TFC token: {e}")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/vnd.api+json",
}

def api(method, path, body=None):
    url = f"https://app.terraform.io/api/v2{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()) if resp.length != 0 else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # 409 = run already in terminal state, safe to ignore
        if e.code == 409:
            return {}
        print(f"  ✗ API error {e.code}: {body[:120]}")
        return {}

# Get workspace ID
ws = api("GET", f"/organizations/{ORG}/workspaces/{WORKSPACE}")
ws_id = ws["data"]["id"]

# List recent runs
runs_data = api("GET", f"/workspaces/{ws_id}/runs?page[size]=20")
runs = runs_data.get("data", [])

discarded = 0
for run in runs:
    status = run["attributes"]["status"]
    run_id = run["id"]
    msg    = run["attributes"].get("message", "")
    if status in DISCARD_STATES:
        api("POST", f"/runs/{run_id}/actions/discard",
            {"comment": "Discarded by make reset — demo prep"})
        print(f"  ✓ Discarded staging run {run_id} ({status}) — {msg[:50]}")
        discarded += 1

if discarded == 0:
    print(f"  - No pending runs on {WORKSPACE}")
