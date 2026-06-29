"""Print Registry versions + what each environment is currently consuming."""
import json, os, re, urllib.request, urllib.error

ORG      = "ngphban"
MODULE   = "order-portal"
PROVIDER = "azurerm"
HOME     = os.path.expanduser("~")

APPS_DIR  = f"{HOME}/acme-apps-azure"
DEV_TF    = f"{APPS_DIR}/envs/dev/azure/main.tf"
STG_TF    = f"{APPS_DIR}/envs/staging/azure/main.tf"

creds_path = f"{HOME}/.terraform.d/credentials.tfrc.json"
token = json.load(open(creds_path))["credentials"]["app.terraform.io"]["token"]
headers = {"Authorization": f"Bearer {token}"}

def api(path):
    req = urllib.request.Request(f"https://app.terraform.io/api/v2{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return {}

def read_version(tf_path):
    try:
        content = open(tf_path).read()
        # Match version inside the module "order_portal" block only
        m = re.search(r'source\s*=\s*"app\.terraform\.io[^\n]*\n\s*version\s*=\s*"([^"]+)"', content)
        return m.group(1) if m else "?"
    except FileNotFoundError:
        return "(file not found)"

C = "\033[36m"; R = "\033[0m"; G = "\033[32m"; Y = "\033[33m"

# Registry versions
base = f"/organizations/{ORG}/registry-modules/private/{ORG}/{MODULE}/{PROVIDER}"
data = api(base)
statuses = data.get("data", {}).get("attributes", {}).get("version-statuses", [])
versions = sorted([s["version"] for s in statuses],
                  key=lambda v: list(map(int, v.split("."))), reverse=True)

print(f"\n{C}  TFC Private Registry — {ORG}/{MODULE}/{PROVIDER}{R}")
if versions:
    for i, v in enumerate(versions):
        tag = f"  {G}✓ v{v}{R}"
        if i == 0:
            tag += f"  {Y}← latest{R}"
        print(tag)
else:
    print(f"  (no versions published)")

# What each env consumes
dev_ver = read_version(DEV_TF)
stg_ver = read_version(STG_TF)

print(f"\n{C}  Consuming{R}")
print(f"  dev     version = \"{dev_ver}\"  {'→ floats within minor range' if '~>' in dev_ver else ''}")
print(f"  staging version = \"{stg_ver}\"  {'→ exact pin, explicit promotion required' if '~>' not in stg_ver and stg_ver != '?' else ''}")

# Contrast note
print(f"\n{C}  Why Registry — not Git source?{R}")
print(f"  Git source:  source = \"git::https://github.com/org/repo.git?ref=abc1234\"")
print(f"               → any commit, no governance, no discovery, no version UI")
print(f"  TFC Registry: source = \"app.terraform.io/{ORG}/{MODULE}/{PROVIDER}\"")
print(f"               → only published versions, semantic versioning, browseable in UI")
print()
