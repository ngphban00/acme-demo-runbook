"""Queue destroy runs for dev and staging workspaces via TFC API."""
import json, os, sys, time, urllib.request, urllib.error

ORG        = "ngphban"
WORKSPACES = ["acme-apps-azure-dev", "acme-apps-azure-staging"]

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
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  ✗ API error {e.code}: {e.read().decode()}")
        sys.exit(1)

run_ids = []

for ws_name in WORKSPACES:
    # Get workspace ID
    ws = api("GET", f"/organizations/{ORG}/workspaces/{ws_name}")
    ws_id = ws["data"]["id"]

    # Check if there are any resources to destroy
    resources = ws["data"]["attributes"].get("resource-count", 0)
    if resources == 0:
        print(f"  - {ws_name}: no resources, skipping")
        continue

    # Queue destroy run with auto-apply override
    run = api("POST", "/runs", {
        "data": {
            "attributes": {
                "is-destroy":   True,
                "auto-apply":   True,
                "message":      "Demo cleanup: destroy all resources",
            },
            "relationships": {
                "workspace": {"data": {"id": ws_id, "type": "workspaces"}}
            },
            "type": "runs"
        }
    })
    run_id = run["data"]["id"]
    run_ids.append((ws_name, run_id))
    print(f"  ✓ {ws_name}: queued destroy run {run_id}")

if not run_ids:
    print("  - Nothing to destroy.")
    sys.exit(0)

# Poll until all runs complete
print("  Waiting for destroy runs to complete...")
terminal = {"applied", "errored", "canceled", "discarded", "planned_and_finished"}

while run_ids:
    time.sleep(5)
    still_running = []
    for ws_name, run_id in run_ids:
        status = api("GET", f"/runs/{run_id}")["data"]["attributes"]["status"]
        if status in terminal:
            icon = "✓" if status == "applied" else "✗"
            print(f"  {icon} {ws_name}: {status}")
        else:
            still_running.append((ws_name, run_id))
    run_ids = still_running

print("\n  → All resources destroyed.")
