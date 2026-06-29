"""Create a GitHub pull request via API. Reads token from ~/.github_token."""
import json, os, sys, urllib.request, urllib.error

REPO  = "ngphban00/acme-apps-azure"
BASE  = "main"

if len(sys.argv) < 3:
    print("Usage: create_pr.py <branch> <version>")
    sys.exit(1)

branch  = sys.argv[1]
version = sys.argv[2]

# Read token
token_path = os.path.expanduser("~/.github_token")
if not os.path.exists(token_path):
    print(f"  ✗ GitHub token not found at {token_path}")
    print(f"  → Create a PAT at https://github.com/settings/tokens")
    print(f"  → Save it: echo 'ghp_xxx' > ~/.github_token && chmod 600 ~/.github_token")
    sys.exit(1)

token = open(token_path).read().strip()
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

body = {
    "title": f"feat: upgrade staging to module {version}",
    "head":  branch,
    "base":  BASE,
    "body":  (
        f"## Promote module {version} to staging\n\n"
        f"**TFC will run a speculative plan on this PR.**\n\n"
        f"After reviewing the plan in the checks below:\n"
        f"1. Merge this PR\n"
        f"2. TFC staging workspace will trigger a real plan\n"
        f"3. Go to TFC UI → **Confirm & Apply**\n"
    ),
}

req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/pulls",
    data=json.dumps(body).encode(),
    headers=headers,
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        pr = json.loads(resp.read())
    print(f"  ✓ PR created: {pr['html_url']}")
    print(f"\n  TFC speculative plan will appear in PR checks shortly.")
    print(f"  After merge → TFC staging runs real plan → Confirm & Apply in TFC UI.")
except urllib.error.HTTPError as e:
    err = json.loads(e.read())
    # PR already exists
    if "already exists" in err.get("errors", [{}])[0].get("message", ""):
        print(f"  - PR already exists for branch {branch}")
        # Fetch existing PR URL
        req2 = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/pulls?head=ngphban00:{branch}&state=open",
            headers=headers,
        )
        with urllib.request.urlopen(req2) as resp2:
            prs = json.loads(resp2.read())
            if prs:
                print(f"  → {prs[0]['html_url']}")
    else:
        print(f"  ✗ GitHub API error {e.code}: {err}")
        sys.exit(1)
