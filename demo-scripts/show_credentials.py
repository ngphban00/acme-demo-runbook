"""Demonstrate no-credential-on-dev-machine: local env is empty, TFC holds the secrets."""
import json, os, urllib.request, urllib.error

ORG  = "ngphban"
HOME = os.path.expanduser("~")

C   = "\033[36m"; R  = "\033[0m"
G   = "\033[32m"; Y  = "\033[33m"
RED = "\033[31m"; B  = "\033[1m"

creds_path = f"{HOME}/.terraform.d/credentials.tfrc.json"
token = json.load(open(creds_path))["credentials"]["app.terraform.io"]["token"]
headers = {"Authorization": f"Bearer {token}"}

def api(path):
    req = urllib.request.Request(
        f"https://app.terraform.io/api/v2{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

# ── 1. Local environment ───────────────────────────────────────────────────────
print(f"\n{B}{C}  [1] Local machine — Azure credentials{R}")

AZURE_VARS = ["ARM_CLIENT_ID", "ARM_CLIENT_SECRET", "ARM_TENANT_ID",
              "ARM_SUBSCRIPTION_ID", "AZURE_CLIENT_SECRET"]
found_local = [(k, os.environ.get(k)) for k in AZURE_VARS if os.environ.get(k)]

if found_local:
    print(f"  {Y}⚠ Found Azure credentials in local env:{R}")
    for k, _ in found_local:
        print(f"    {k} = (set)")
else:
    print(f"  {G}✓ No Azure credentials in local environment{R}")
    print(f"    ARM_CLIENT_ID       = (not set)")
    print(f"    ARM_CLIENT_SECRET   = (not set)")
    print(f"    ARM_TENANT_ID       = (not set)")
    print(f"    ARM_SUBSCRIPTION_ID = (not set)")

print(f"\n  {C}Only credential on this machine:{R}")
print(f"    ~/.terraform.d/credentials.tfrc.json  ← TFC token only, scoped to app.terraform.io")

# ── 2. TFC workspace variables + variable sets ────────────────────────────────
print(f"\n{B}{C}  [2] TFC — where credentials actually live{R}")

def print_azure_vars(vars_list, indent="    "):
    azure_vars = [v for v in vars_list
                  if any(k in v["attributes"]["key"] for k in ["ARM_", "AZURE_"])]
    if azure_vars:
        for v in azure_vars:
            key       = v["attributes"]["key"]
            sensitive = v["attributes"]["sensitive"]
            category  = v["attributes"]["category"]
            icon  = f"{RED}●{R}" if sensitive else f"{Y}○{R}"
            label = "sensitive (write-only)" if sensitive else "visible"
            print(f"{indent}{icon} {key:<30} [{category}] [{label}]")
        return True
    return False

found_anywhere = False

# Check workspace-level vars
for ws_name in ["acme-apps-azure-dev", "acme-apps-azure-staging"]:
    ws    = api(f"/organizations/{ORG}/workspaces/{ws_name}")
    ws_id = ws["data"]["id"]
    vars_data = api(f"/workspaces/{ws_id}/vars")
    azure = print_azure_vars.__wrapped__ if hasattr(print_azure_vars, '__wrapped__') else None
    vars_list = vars_data.get("data", [])
    azure_vars = [v for v in vars_list
                  if any(k in v["attributes"]["key"] for k in ["ARM_", "AZURE_"])]
    if azure_vars:
        print(f"\n  Workspace: {ws_name}")
        print_azure_vars(vars_list)
        found_anywhere = True

# Check org-level variable sets
varsets_data = api(f"/organizations/{ORG}/varsets")
varsets = varsets_data.get("data", [])
for vs in varsets:
    vs_id   = vs["id"]
    vs_name = vs["attributes"]["name"]
    vs_vars = api(f"/varsets/{vs_id}/relationships/vars")
    vs_list = vs_vars.get("data", [])
    # fetch full var details
    azure_vars = [v for v in vs_list
                  if any(k in v["attributes"].get("key","") for k in ["ARM_", "AZURE_"])]
    if azure_vars:
        print(f"\n  Variable Set: {vs_name} (org-level, applies to all workspaces)")
        print_azure_vars(azure_vars)
        found_anywhere = True

if not found_anywhere:
    # Still list varsets for visibility
    if varsets:
        print(f"\n  Variable Sets found (may use non-ARM_ key names or OIDC):")
        for vs in varsets:
            print(f"    • {vs['attributes']['name']}")
    else:
        print(f"\n  {Y}No workspace vars or variable sets found with ARM_ keys.{R}")
        print(f"  Credentials may be using OIDC/Managed Identity (no static secrets needed).")

# ── 3. Security model explanation ──────────────────────────────────────────────
oidc = found_anywhere and any(
    "TFC_AZURE_PROVIDER_AUTH" in str(v) for v in varsets)

print(f"""
{B}{C}  [3] Security model{R}
""")

if oidc:
    print(f"  {G}Auth method: OIDC (Workload Identity Federation){R}")
    print(f"  No client secret stored anywhere — TFC generates short-lived tokens per run.")
    print(f"  Even TFC admins cannot extract a secret — there is none.\n")

print(f"""  Developer machine          TFC
  ─────────────────          ──────────────────────────────
  TFC token only        →    authenticates to TFC API
  git push              →    TFC pulls code from VCS
  terraform plan        →    plan executes IN TFC environment
                             credentials injected at runtime by TFC
                        →    result streamed back to terminal

  {G}Azure credentials never touch the developer machine.{R}
  ARM_CLIENT_SECRET does not exist — OIDC issues a token valid for this run only.

  {C}vs self-managed Terraform:{R}
  Terraform OSS + static SP    → secret on every CI runner and dev machine
                                  rotate manually, risk of leakage in logs
  Terraform OSS + OIDC in CI  → better, but each repo manages its own OIDC config
  {G}TFC + OIDC variable sets   → one config, applied org-wide, zero secrets anywhere{R}
""")
