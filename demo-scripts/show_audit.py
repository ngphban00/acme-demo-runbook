"""Show TFC run audit trail — every run is logged with who, when, what, result."""
import json, os, urllib.request
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
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

STATUS_COLOR = {
    "applied":             G,
    "planned_and_finished":G,
    "errored":             RED,
    "canceled":            Y,
    "discarded":           DIM,
    "policy_soft_failed":  Y,
    "policy_hard_failed":  RED,
}

TRIGGER = {
    "vcs":     "VCS push",
    "api":     "API",
    "ui":      "TFC UI",
    "unknown": "unknown",
}

def fmt_time(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            return f"{mins}m ago"
        elif mins < 1440:
            return f"{mins//60}h ago"
        else:
            return f"{mins//1440}d ago"
    except Exception:
        return iso[:16]

print(f"\n{B}{C}  TFC Run Audit Trail{R}")
print(f"  Every run is immutable — cannot be deleted or modified\n")

for ws_name in WORKSPACES:
    ws    = api(f"/organizations/{ORG}/workspaces/{ws_name}")
    ws_id = ws["data"]["id"]
    runs  = api(f"/workspaces/{ws_id}/runs?page[size]=6")

    print(f"{C}  ── {ws_name} ──{R}")
    print(f"  {'When':<10} {'Status':<24} {'Trigger':<10} {'Message'}")
    print(f"  {'─'*8}  {'─'*22}  {'─'*8}  {'─'*35}")

    for run in runs.get("data", []):
        attr    = run["attributes"]
        status  = attr["status"]
        message = (attr.get("message") or "")[:45]
        created = fmt_time(attr["created-at"])
        source  = TRIGGER.get(attr.get("source", "unknown"), attr.get("source", "?"))
        color   = STATUS_COLOR.get(status, C)
        run_id  = run["id"]

        print(f"  {DIM}{created:<10}{R} {color}{status:<24}{R} {source:<10} {message}")

    print()

print(f"{B}{C}  What TFC stores per run:{R}")
print(f"  • Run ID, timestamp, trigger source (VCS / API / UI)")
print(f"  • Git commit SHA and commit message")
print(f"  • Full terraform plan output")
print(f"  • Sentinel policy evaluation result per policy")
print(f"  • Who confirmed the apply (for manual-approve workspaces)")
print(f"  • Apply log — every resource created/changed/destroyed")

print(f"""
{B}{C}  vs self-managed Terraform:{R}
  Terraform OSS    → no built-in run history
                     who ran apply? check git blame if they committed the state
                     plan output? gone unless someone saved it manually
                     CI logs? retained for N days then deleted

  {G}TFC              → permanent, tamper-proof run history{R}
                     compliance teams can audit: what changed, when, who approved
                     plan output retained even if workspace is destroyed
""")
