"""Pre-flight check — verifies all tools, tokens, repos, and TFC/GitHub access."""
import json, os, shutil, subprocess, sys, urllib.request, urllib.error

HOME = os.path.expanduser("~")
OK   = "\033[32m  ✓\033[0m"
FAIL = "\033[31m  ✗\033[0m"
WARN = "\033[33m  ⚠\033[0m"

errors = []

def check(label, ok, msg=""):
    if ok:
        print(f"{OK} {label}")
    else:
        print(f"{FAIL} {label}" + (f" — {msg}" if msg else ""))
        errors.append(label)

def warn(label, msg=""):
    print(f"{WARN} {label}" + (f" — {msg}" if msg else ""))

def api(url, token, kind="Bearer"):
    req = urllib.request.Request(url, headers={"Authorization": f"{kind} {token}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)

def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)

# ── 1. Tools ──────────────────────────────────────────────────────────────────
print("\n\033[36m[1/5] Tools\033[0m")

tf_ok, tf_out = run(["terraform", "version", "-json"])
if tf_ok:
    try:
        ver = json.loads(tf_out.strip())["terraform_version"]
        parts = list(map(int, ver.split(".")))
        check(f"terraform >= 1.7 (found {ver})", parts >= [1, 7],
              "mock_provider requires Terraform 1.7+")
    except Exception:
        check("terraform version parseable", False, tf_out.strip())
else:
    check("terraform installed", False, "not found in PATH")

check("git installed",     shutil.which("git")     is not None)
check("python3 installed", shutil.which("python3") is not None)

# ── 2. SSH & GitHub token ─────────────────────────────────────────────────────
print("\n\033[36m[2/5] Auth & Tokens\033[0m")

ssh_key = f"{HOME}/.ssh/github-ngphban00"
check("SSH key exists (~/.ssh/github-ngphban00)", os.path.exists(ssh_key),
      f"create with: ssh-keygen -t ed25519 -f {ssh_key}")

if os.path.exists(ssh_key):
    ssh_ok, ssh_out = run([
        "ssh", "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-T", "git@github.com"
    ])
    # GitHub returns exit code 1 even on success ("Hi user!")
    authed = "successfully authenticated" in ssh_out or "ngphban00" in ssh_out
    check("SSH auth to github.com", authed, ssh_out.strip()[:80])

gh_token_path = f"{HOME}/.github_token"
gh_token = None
if os.path.exists(gh_token_path):
    gh_token = open(gh_token_path).read().strip()
    check("GitHub token file exists (~/.github_token)", True)
    data, err = api("https://api.github.com/user", gh_token, "token")
    check("GitHub token valid",
          data is not None and "login" in data,
          err or f"unexpected response")
else:
    check("GitHub token file exists (~/.github_token)", False,
          "create PAT at https://github.com/settings/tokens (scope: repo)\n"
          "    then: echo 'ghp_xxx' > ~/.github_token && chmod 600 ~/.github_token")

tfc_creds_path = f"{HOME}/.terraform.d/credentials.tfrc.json"
tfc_token = None
if os.path.exists(tfc_creds_path):
    try:
        tfc_token = json.load(open(tfc_creds_path))["credentials"]["app.terraform.io"]["token"]
        check("TFC token file exists (~/.terraform.d/credentials.tfrc.json)", True)
        data, err = api("https://app.terraform.io/api/v2/account/details", tfc_token)
        check("TFC token valid", data is not None, err or "")
    except (KeyError, json.JSONDecodeError) as e:
        check("TFC token parseable", False, str(e))
else:
    check("TFC token file exists", False, "run: terraform login")

# ── 3. Repositories ───────────────────────────────────────────────────────────
print("\n\033[36m[3/5] Repositories\033[0m")

for repo, path in [
    ("acme-apps-azure",              f"{HOME}/acme-apps-azure"),
    ("terraform-azurerm-static-site",f"{HOME}/terraform-azurerm-static-site"),
    ("acme-demo-runbook",            f"{HOME}/acme-demo-runbook"),
]:
    exists = os.path.isdir(f"{path}/.git")
    check(f"{repo} cloned", exists,
          f"run: make setup" if not exists else "")

for env, path in [
    ("dev",     f"{HOME}/acme-apps-azure/envs/dev/azure/.terraform"),
    ("staging", f"{HOME}/acme-apps-azure/envs/staging/azure/.terraform"),
]:
    check(f"terraform initialized ({env})", os.path.isdir(path),
          "run: make setup")

# ── 4. TFC Workspaces & Registry ─────────────────────────────────────────────
print("\n\033[36m[4/5] Terraform Cloud\033[0m")

if tfc_token:
    for ws in ["acme-apps-azure-dev", "acme-apps-azure-staging"]:
        data, err = api(
            f"https://app.terraform.io/api/v2/organizations/ngphban/workspaces/{ws}",
            tfc_token
        )
        check(f"TFC workspace: {ws}", data is not None, err or "")

    data, err = api(
        "https://app.terraform.io/api/v2/organizations/ngphban/registry-modules/private/ngphban/order-portal/azurerm",
        tfc_token
    )
    if data:
        versions = [v["version"] for v in data["data"]["attributes"].get("version-statuses", [])]
        check(f"TFC Registry: order-portal/azurerm ({', '.join(versions)})", True)
    else:
        check("TFC Registry: order-portal/azurerm", False, err or "module not found")
else:
    warn("TFC checks skipped — no token")

# ── 5. GitHub Repos ───────────────────────────────────────────────────────────
print("\n\033[36m[5/5] GitHub Repos\033[0m")

if gh_token:
    for repo in ["ngphban00/acme-apps-azure",
                 "ngphban00/terraform-azurerm-static-site",
                 "ngphban00/acme-demo-runbook"]:
        data, err = api(f"https://api.github.com/repos/{repo}", gh_token, "token")
        check(f"GitHub repo: {repo}", data is not None, err or "")
else:
    warn("GitHub repo checks skipped — no token")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"\033[31m  {len(errors)} issue(s) found. Fix before running make reset:\033[0m")
    for e in errors:
        print(f"    • {e}")
    sys.exit(1)
else:
    print("\033[32m  All checks passed. Ready to demo — run: make destroy && make reset\033[0m")
