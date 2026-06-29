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
versions = [s["version"] for s in statuses]
to_delete = [v for v in versions if v != KEEP]

if not to_delete:
    print(f"  - Registry: only {KEEP} present, nothing to delete")
else:
    for ver in to_delete:
        req = urllib.request.Request(f"{base}/{ver}", headers=headers, method="DELETE")
        try:
            urllib.request.urlopen(req)
            print(f"  ✓ Deleted registry version v{ver}")
        except urllib.error.HTTPError as e:
            print(f"  ✗ Failed to delete v{ver}: {e.code} {e.reason}")

# Verify v1.0.0 is present after cleanup
if KEEP not in versions:
    print(f"  ⚠ v{KEEP} not found in Registry.")
    print(f"    Push git tag v{KEEP} to bootstrap:")
    print(f"    cd ~/terraform-azurerm-static-site && git tag v{KEEP} && git push origin v{KEEP}")
    print(f"    Then wait ~60s and re-run make reset.")
    sys.exit(1)
else:
    print(f"  ✓ Registry: v{KEEP} confirmed")
