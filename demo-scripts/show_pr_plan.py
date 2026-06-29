"""Fetch and display the latest speculative plan on staging — the PR check run."""
import json, os, sys, time, urllib.request, urllib.error

ORG      = "ngphban"
WORKSPACE = "acme-apps-azure-staging"
HOME     = os.path.expanduser("~")

C   = "\033[36m"; R   = "\033[0m"; B   = "\033[1m"
G   = "\033[32m"; Y   = "\033[33m"; RED = "\033[31m"; DIM = "\033[2m"

token = json.load(open(f"{HOME}/.terraform.d/credentials.tfrc.json")
                  )["credentials"]["app.terraform.io"]["token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/vnd.api+json",
}

def api(path):
    req = urllib.request.Request(
        f"https://app.terraform.io/api/v2{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code}

# ── Find latest speculative run ────────────────────────────────────────────────
ws    = api(f"/organizations/{ORG}/workspaces/{WORKSPACE}")
ws_id = ws["data"]["id"]

runs  = api(f"/workspaces/{ws_id}/runs?page[size]=10")
spec_run = next(
    (r for r in runs.get("data", [])
     if r["attributes"].get("is-speculative", False)),
    None
)

if not spec_run:
    print(f"\n  {Y}No speculative run found on {WORKSPACE}.{R}")
    print(f"  Run 'make pr-staging' first to create a PR — TFC will trigger a speculative plan.")
    sys.exit(0)

run_id   = spec_run["id"]
attr     = spec_run["attributes"]
status   = attr["status"]
message  = attr.get("message", "")
created  = attr["created-at"][:16].replace("T", " ")

print(f"\n{B}{C}  PR Check — TFC Speculative Plan on Staging{R}\n")
print(f"  {C}What is a speculative plan?{R}")
print(f"  TFC runs a full 'terraform plan' against real state when a PR is opened.")
print(f"  Result appears as a GitHub PR status check — reviewers see exact infra changes")
print(f"  before merging. The plan is read-only: cannot be applied from the PR.\n")

# Status
STATUS_COLOR = {
    "planned_and_finished": G,
    "planning":             Y,
    "plan_queued":          Y,
    "pending":              Y,
    "errored":              RED,
}
color = STATUS_COLOR.get(status, C)
print(f"  Run:     {DIM}{run_id}{R}")
print(f"  Message: {message}")
print(f"  Created: {created} UTC")
print(f"  Status:  {color}{status}{R}")

# Poll if still running
if status in {"pending", "plan_queued", "planning"}:
    print(f"\n  {Y}⏳ Plan still running — polling...{R}")
    for _ in range(24):  # max 2 min
        time.sleep(5)
        run_data = api(f"/runs/{run_id}")
        status = run_data["data"]["attributes"]["status"]
        print(f"     {status}", end="\r")
        if status not in {"pending", "plan_queued", "planning"}:
            break
    print()
    attr = run_data["data"]["attributes"]

# Plan summary
plan_rel = spec_run.get("relationships", {}).get("plan", {}).get("data", {})
plan_id  = plan_rel.get("id")

if plan_id:
    plan = api(f"/plans/{plan_id}")
    p    = plan.get("data", {}).get("attributes", {})
    adds    = p.get("resource-additions", 0)
    changes = p.get("resource-changes", 0)
    removes = p.get("resource-destructions", 0)

    print(f"\n  {B}Plan summary:{R}")
    print(f"    {G}+ {adds} to add{R}    {Y}~ {changes} to change{R}    {RED}- {removes} to destroy{R}")

    log_url = p.get("log-read-url")
    if log_url:
        print(f"\n  {C}Full plan output:{R}")
        try:
            req = urllib.request.Request(log_url)
            with urllib.request.urlopen(req, timeout=10) as r:
                log = r.read().decode("utf-8", errors="replace")
            # Print last meaningful section
            lines = [l for l in log.splitlines()
                     if any(kw in l for kw in ["will be created", "will be updated",
                                               "will be destroyed", "Plan:", "No changes",
                                               "resource_group", "storage_account",
                                               "must be replaced"])]
            for line in lines[:20]:
                print(f"    {line}")
        except Exception:
            pass

tfc_run_url = f"https://app.terraform.io/app/{ORG}/{WORKSPACE}/runs/{run_id}"
print(f"\n  {C}View full run in TFC:{R} {tfc_run_url}")

print(f"""
{B}{C}  Why TFC PR check > GitHub Actions terraform plan:{R}

  GitHub Actions plan    TFC speculative plan
  ──────────────────     ────────────────────────────────────
  Runs on GH runner      Runs in TFC — same env as real apply
  Needs cloud creds      Uses workspace credentials (OIDC)
    in repo secrets        never exposed to the PR branch
  Plan vs real state?    Always against real TFC-managed state
    depends on backend     no drift possible
  Anyone can re-run      Tied to exact commit SHA on PR
  Output in GH logs      Output in TFC UI + linked as PR check
  Can be skipped         Cannot be skipped for VCS-driven workspace
""")
