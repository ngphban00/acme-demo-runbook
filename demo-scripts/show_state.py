"""Show TFC state management — versioned, locked, centrally stored."""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone

ORG        = "ngphban"
WORKSPACES = ["acme-apps-azure-dev", "acme-apps-azure-staging"]
HOME       = os.path.expanduser("~")

C   = "\033[36m"; R   = "\033[0m"; B   = "\033[1m"
G   = "\033[32m"; Y   = "\033[33m"; RED = "\033[31m"; DIM = "\033[2m"

token = json.load(open(f"{HOME}/.terraform.d/credentials.tfrc.json")
                  )["credentials"]["app.terraform.io"]["token"]
headers = {"Authorization": f"Bearer {token}"}

def api(path):
    req = urllib.request.Request(
        f"https://app.terraform.io/api/v2{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {}

def fmt_time(iso):
    try:
        dt  = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 60:   return f"{mins}m ago"
        if mins < 1440: return f"{mins//60}h ago"
        return f"{mins//1440}d ago"
    except Exception:
        return iso[:16]

print(f"\n{B}{C}  TFC State Management{R}\n")

for ws_name in WORKSPACES:
    ws    = api(f"/organizations/{ORG}/workspaces/{ws_name}")
    ws_id = ws["data"]["id"]
    attr  = ws["data"]["attributes"]

    resources  = attr.get("resource-count", 0)
    locked     = attr.get("locked", False)
    lock_reason = attr.get("locked-reason") or ""

    print(f"{C}  ── {ws_name} ──{R}")
    print(f"  Resources in state : {B}{resources}{R}")
    print(f"  State locked       : {RED + 'yes — ' + lock_reason + R if locked else G + 'no' + R}")

    # Current state version
    sv = api(f"/workspaces/{ws_id}/current-state-version")
    if sv and sv.get("data"):
        sv_attr    = sv["data"]["attributes"]
        serial     = sv_attr.get("serial", "?")
        created_at = fmt_time(sv_attr.get("created-at", ""))
        size       = sv_attr.get("size", 0)
        print(f"  State serial       : {serial}  ({created_at}, {size:,} bytes)")
        mods = sv_attr.get("modules-count")
        provs = sv_attr.get("providers-count")
        if mods is not None: print(f"  Modules recorded   : {mods}")
        if provs is not None: print(f"  Providers recorded : {provs}")

    # State version history
    svs = api(f"/workspaces/{ws_id}/state-versions?page[size]=5")
    versions = svs.get("data", [])
    if versions:
        print(f"\n  {C}State version history (latest 5):{R}")
        print(f"  {'Serial':<8} {'When':<12} {'Resources':<12} {'Run triggered by'}")
        print(f"  {'─'*6}  {'─'*10}  {'─'*10}  {'─'*30}")
        for v in versions:
            va  = v["attributes"]
            run_rel = v.get("relationships", {}).get("run", {}).get("data") or {}
            run_id  = run_rel.get("id", "")
            msg = ""
            if run_id:
                run_data = api(f"/runs/{run_id}")
                msg = (run_data.get("data", {})
                               .get("attributes", {})
                               .get("message", ""))[:35]
            print(f"  {va.get('serial','?'):<8} "
                  f"{fmt_time(va.get('created-at','')):<12} "
                  f"{va.get('resource-count',0):<12} "
                  f"{DIM}{msg}{R}")
    print()

print(f"{B}{C}  What TFC state management gives you:{R}")
print(f"  • {G}Automatic versioning{R} — every apply creates a new state version")
print(f"  • {G}State locking{R}       — concurrent runs are queued, never corrupt state")
print(f"  • {G}State history{R}       — roll back to any previous state version from UI")
print(f"  • {G}Encrypted at rest{R}   — state contains secrets, TFC encrypts automatically")
print(f"  • {G}Access control{R}      — workspace permissions govern who can read state")
print(f"  • {G}Remote outputs{R}      — other workspaces can read outputs via data source")

print(f"""
{B}{C}  vs self-managed state (S3 + DynamoDB):{R}

  S3 + DynamoDB backend         TFC state
  ─────────────────────         ──────────────────────────────────
  Manual S3 bucket setup        Zero config — state managed by TFC
  Manual DynamoDB for locking   Locking built in, no extra service
  Versioning via S3 config      Versioning automatic, browseable in UI
  Encryption via KMS (optional) Encryption always on
  No access control on state    Workspace RBAC controls state access
  Secrets visible in S3 object  Sensitive values masked in TFC UI
  Team must manage infra         {G}TFC manages the state backend itself{R}
""")
