"""Print the Sentinel policy with annotated explanation for demo."""
import os

MODULE_DIR = os.path.expanduser("~/terraform-azurerm-static-site")
POLICY     = f"{MODULE_DIR}/policies/restrict-storage-tier-dev.sentinel"

C = "\033[36m"; R = "\033[0m"; Y = "\033[33m"; G = "\033[32m"; RED = "\033[31m"

policy = open(POLICY).read()

print(f"\n{C}  Sentinel Policy — restrict-storage-tier-dev{R}")
print(f"  File: policies/restrict-storage-tier-dev.sentinel")
print(f"  Enforcement: {RED}hard-mandatory{R} — no override path, not even org admin\n")
print(f"  {'─'*60}")

for line in policy.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        print(f"  {Y}{line}{R}")
    elif "tfrun.workspace.name" in line:
        print(f"  {line}   {C}← scope: applies only when workspace name ends in -dev{R}")
    elif "sa.change.after.access_tier" in line:
        print(f"  {line}   {C}← reads PLANNED value, not HCL code{R}")
    elif "main = rule" in line:
        print(f"  {line}   {C}← entry point evaluated by TFC{R}")
    else:
        print(f"  {line}")

print(f"  {'─'*60}")
print(f"""
{C}  How Sentinel fits in the TFC run lifecycle:{R}

    Push to main
        │
        ▼
    terraform plan    ← Terraform resolves all resource attributes
        │
        ▼
    {RED}Sentinel check{R}    ← reads plan output: sa.change.after.access_tier
        │               NOT the HCL source — actual planned value
        │
    ┌───┴────────────────────┐
    │ PASS                   │ FAIL (hard-mandatory)
    ▼                        ▼
    apply                 {RED}blocked — no override button exists{R}
    (auto on dev)         run must be discarded, fix code and push again
""")

print(f"{C}  Why this matters vs CI-based policy (e.g. OPA in GitHub Actions):{R}")
print(f"  CI policy runs on HCL code  → misses dynamic values (count, for_each, data sources)")
print(f"  Sentinel runs on tfplan     → sees exact resources and attribute values after evaluation")
print(f"  CI policy can be skipped    → git push --no-verify or bypass branch protection")
print(f"  {RED}hard-mandatory cannot be skipped{R} → enforced inside TFC, not in the pipeline\n")
