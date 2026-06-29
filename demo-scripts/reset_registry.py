"""Delete all module versions > v1.0.0 from TFC Private Registry via API."""
import json, os, sys, urllib.request, urllib.error

ORG      = "ngphban"
MODULE   = "order-portal"
PROVIDER = "azurerm"
KEEP     = "1.0.0"

creds_path = os.path.expanduser("~/.terraform.d/credentials.tfrc.json")
try:
    creds = json.load(open(creds_path))
    token = creds["credentials"]["app.terraform.io"]["token"]
except (KeyError, FileNotFoundError) as e:
    print(f"  ✗ Cannot read TFC token: {e}")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/vnd.api+json",
}

base = f"https://app.terraform.io/api/v2/organizations/{ORG}/registry-modules/private/{ORG}/{MODULE}/{PROVIDER}"

# Get module detail (version-statuses lives here, not at /versions)
req = urllib.request.Request(base, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
except urllib.error.HTTPError as e:
    print(f"  ✗ Failed to fetch module: {e.code} {e.reason}")
    sys.exit(1)

statuses = data.get("data", {}).get("attributes", {}).get("version-statuses", [])
to_delete = [s["version"] for s in statuses if s["version"] != KEEP]

if not to_delete:
    print(f"  - Registry: only {KEEP} present, nothing to delete")
    sys.exit(0)

for ver in to_delete:
    req = urllib.request.Request(f"{base}/{ver}", headers=headers, method="DELETE")
    try:
        urllib.request.urlopen(req)
        print(f"  ✓ Deleted registry version v{ver}")
    except urllib.error.HTTPError as e:
        print(f"  ✗ Failed to delete v{ver}: {e.code} {e.reason}")
