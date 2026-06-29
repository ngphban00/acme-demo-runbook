"""Interactive presenter script — walks through each demo step with talking points."""
import subprocess, sys, os

C  = "\033[36m";  R  = "\033[0m";  B  = "\033[1m"
G  = "\033[32m";  Y  = "\033[33m"; DIM= "\033[2m"
RED= "\033[31m";  UL = "\033[4m"

RUNBOOK = os.path.expanduser("~/acme-demo-runbook")

def hr(): print(f"\n  {'─'*62}\n")

def say(text):
    print(f"\n  {Y}🎤 SAY:{R}")
    for line in text.strip().splitlines():
        print(f"     {line.strip()}")

def point(text):
    print(f"\n  {C}👆 POINT TO:{R}")
    for line in text.strip().splitlines():
        print(f"     {line.strip()}")

def wait_say(text):
    print(f"\n  {Y}⏳ WHILE WAITING — SAY:{R}")
    for line in text.strip().splitlines():
        print(f"     {line.strip()}")

def highlight(text):
    print(f"\n  {G}✓ HIGHLIGHT:{R}")
    for line in text.strip().splitlines():
        print(f"     {line.strip()}")

def cmd(command):
    print(f"\n  {G}▶ RUN:{R}  {B}{command}{R}")

def pause(label="Press Enter to continue..."):
    print(f"\n  {DIM}[ {label} ]{R}", end="")
    input()

def run_step(command):
    print(f"\n  {G}▶ Executing: {command}{R}\n")
    subprocess.run(command, shell=True, cwd=RUNBOOK)

STEPS = [

# ── 0 ─────────────────────────────────────────────────────────────────────────
{
"title": "Opening — Set the scene",
"run": None,
"script": lambda: [
    say("""
        "We have three teams: Platform, Application, and Security.
        Platform owns the Terraform module. Application consumes it.
        Security enforces policy. None of them need to coordinate manually —
        Terraform Cloud is the connective tissue between all three."
    """),
    say("""
        "Everything you'll see today runs from a single terminal.
        No manual TFC UI clicks for infrastructure changes —
        only for deliberate approval gates, by design."
    """),
    point("make help output — show all targets and what they represent"),
]},

# ── 1 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 1 — Registry versioning",
"run": "make status-registry",
"script": lambda: [
    say("""
        "Before we publish anything — this is the starting state.
        Registry has one version: v1.0.0. Both dev and staging consume it.
        Notice dev uses a range constraint, staging pins an exact version.
        That difference will matter later."
    """),
    point("""
        Git source line at the bottom —
        'git::https://...?ref=abc1234 — any commit, no governance'
        vs 'app.terraform.io/org/module — only published versions'
    """),
    say("""
        "Without a registry, teams reference arbitrary git commits.
        No versioning contract, no discovery, no governance on what's consumed."
    """),
]},

# ── 2 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 2 — Platform team publishes new module version",
"run": "make module-publish",
"script": lambda: [
    say("""
        "Platform team adds a new feature — min_tls_version variable.
        Non-breaking, backward compatible. They push with a 'feat:' prefix."
    """),
    wait_say("""
        "Watch GitHub Actions — not TFC yet.
        Before any version appears in the Registry, code must pass:
        terraform fmt check, terraform validate, and terraform test with mock providers.
        The tag is created ONLY after all three pass.
        This is the quality gate — policy before artifact."
    """),
    point("GitHub Actions tab — show each job: validate → test → release"),
    highlight("""
        When CI green: Registry gains v1.1.0 automatically.
        Platform team pushed once — versioning, testing, publishing: all automated.
    """),
]},

# ── 3 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 3 — App team upgrades dev",
"run": "make app-upgrade",
"script": lambda: [
    say("""
        "App team sees v1.1.0 in the Registry. They upgrade dev.
        Notice the constraint: '~> 1.1' — any 1.1.x patch.
        Staging stays on 1.0.0. No automatic promotion."
    """),
    wait_say("""
        "TFC picks up the push and triggers a plan automatically.
        The developer didn't need Azure credentials — not on their machine,
        not in CI secrets. TFC holds them via OIDC. Zero credential sprawl."
    """),
    point("TFC dev workspace — show plan running, then applied"),
    highlight("""
        Auto-apply: resources created without anyone clicking anything.
        Dev is fast — push to main, infra follows.
    """),
]},

# ── 4 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 4 — Credentials: nothing on this machine",
"run": "make show-credentials",
"script": lambda: [
    say("""
        "Before we continue — a question audiences always ask:
        where are the Azure credentials? Let's prove they're not here."
    """),
    point("Section [1] — ARM_ variables: all (not set)"),
    say("""
        "The only credential on this machine is a TFC token.
        TFC authenticates to Azure via OIDC — no client secret exists anywhere.
        Short-lived tokens, generated per run, expired after the run."
    """),
    point("Section [2] — Variable sets in TFC, sensitive = write-only"),
    say("""
        "Even if I had TFC admin access, I couldn't read ARM_CLIENT_SECRET
        because there isn't one. OIDC means no secret to steal, rotate, or leak."
    """),
]},

# ── 5 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 5 — Sentinel: policy violation",
"run": "make show-sentinel",
"script": lambda: [
    say("""
        "Security team has a policy: dev workspaces must use Cool storage tier.
        Hot tier is expensive and unnecessary in development.
        Let's look at the policy before we trigger it."
    """),
    point("is_dev line — scope is automatic, based on workspace name"),
    point("sa.change.after.access_tier — reads PLANNED value, not HCL source"),
    say("""
        "This is the key difference from OPA in CI:
        Sentinel runs after terraform plan.
        It sees the actual value Terraform will set — not just what the code says.
        Dynamic values, data sources, for_each — all resolved before policy runs."
    """),
]},

# ── 6 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 6 — Trigger violation",
"run": "make sentinel-fail",
"script": lambda: [
    say("""
        "App team sets access_tier to Hot — maybe for performance testing.
        They push. TFC plan runs — plan itself passes, resources look valid.
        Then Sentinel evaluates."
    """),
    wait_say("""
        "Plan is running. Remember: Sentinel only fires after plan completes.
        That's why it catches things static analysis misses."
    """),
    point("TFC: plan green, Sentinel step: hard-failed"),
    point("No Override button — hard-mandatory means nobody can bypass this"),
    say("""
        "Not the workspace admin. Not the org owner. Nobody.
        The only path forward is to fix the code and push again."
    """),
]},

# ── 7 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 7 — Fix violation",
"run": "make sentinel-pass",
"script": lambda: [
    say("""
        "App team reverts to Cool tier. Push to main.
        New run — Sentinel passes this time. Auto-apply kicks in."
    """),
    wait_say("""
        "TFC shows two runs in history: the failed one and this one.
        Both are permanent. Security team can audit exactly what happened,
        when, and who fixed it — without asking anyone."
    """),
    highlight("Sentinel passed → auto-apply → infrastructure compliant"),
]},

# ── 8 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 8 — Audit trail",
"run": "make show-audit",
"script": lambda: [
    say("""
        "We can see every run that ever happened — who triggered it, when,
        what commit, what the outcome was. This is immutable."
    """),
    point("Trigger source: tfe-configuration-version = VCS push, tfe-api = script, tfe-ui = manual"),
    say("""
        "With Terraform OSS: who ran apply? Check git blame — if they committed.
        Plan output? Gone unless someone saved it.
        CI logs? Expired in 90 days.
        TFC: permanent, tamper-proof, compliance-ready out of the box."
    """),
]},

# ── 9 ─────────────────────────────────────────────────────────────────────────
{
"title": "Step 9 — CLI speculative plan",
"run": "make speculative-dev",
"script": lambda: [
    say("""
        "Developers can preview changes from their terminal — terraform plan.
        But watch what happens: the plan runs in TFC, not locally.
        TFC executes it with the workspace credentials and real state."
    """),
    highlight("No Apply button — output says 'this is a speculative plan'"),
    say("""
        "To apply, changes must go through VCS — push to main.
        The CLI is read-only. This enforces the audit trail:
        every apply has a commit, a PR, a history."
    """),
]},

# ── 10 ────────────────────────────────────────────────────────────────────────
{
"title": "Step 10 — Promote to staging via PR",
"run": "make pr-staging",
"script": lambda: [
    say("""
        "Staging is a different story. App team can't just push to staging.
        Promotion requires a PR — that's the explicit gate."
    """),
    wait_say("""
        "A PR just opened. In about 60 seconds, TFC will appear
        as a status check on that PR — not GitHub Actions, TFC itself.
        The check shows the terraform plan output: what will be created,
        changed, or destroyed, against real staging state."
    """),
    say("""
        "Reviewer sees exact infra impact before approving merge.
        Not 'the code looks fine' — 'the plan shows 2 resources created, 0 destroyed'."
    """),
]},

# ── 11 ────────────────────────────────────────────────────────────────────────
{
"title": "Step 11 — Show PR speculative plan",
"run": "make show-pr-plan",
"script": lambda: [
    point("Plan summary: + N to add, ~ N to change, - N to destroy"),
    say("""
        "This is running in TFC's environment with TFC's OIDC credentials.
        The PR branch never had access to those credentials —
        TFC fetches the code, runs the plan, posts the result.
        Credential isolation even at the PR check level."
    """),
    point("Link to TFC run — click through to see full plan output"),
]},

# ── 12 ────────────────────────────────────────────────────────────────────────
{
"title": "Step 12 — Merge PR → Confirm & Apply",
"run": None,
"script": lambda: [
    say("Merge the PR on GitHub now."),
    wait_say("""
        "After merge, TFC staging workspace triggers a real plan.
        This one has an Apply button — unlike the speculative plan on the PR."
    """),
    point("TFC staging workspace — plan completed, waiting for approval"),
    say("""
        "This is the final human gate. Someone with workspace permissions
        reviews the plan one more time and clicks Confirm & Apply.
        Auto-apply is OFF on staging — every change needs a human sign-off."
    """),
    say("Click Confirm & Apply now."),
    highlight("Resources created on staging — same module, different governance"),
]},

# ── 13 ────────────────────────────────────────────────────────────────────────
{
"title": "Step 13 — State management",
"run": "make show-state",
"script": lambda: [
    say("""
        "One last thing — where does the state live?
        Not in S3. Not in a git repo. Not on anyone's machine.
        TFC manages it."
    """),
    point("State serial — increments with every apply"),
    point("State locked: no — TFC locks it automatically during runs"),
    say("""
        "With Terraform OSS you provision S3, DynamoDB for locking,
        KMS for encryption, IAM policies for access — before writing a single
        line of infrastructure code.
        With TFC: zero setup. State is just there, versioned, locked, encrypted."
    """),
]},

# ── 14 ────────────────────────────────────────────────────────────────────────
{
"title": "Closing — The governance story",
"run": None,
"script": lambda: [
    say("""
        "What we just saw: one module, two environments, three teams —
        zero manual coordination.
        Platform published when ready. App consumed when ready.
        Security policy enforced automatically. Staging approved deliberately."
    """),
    say("""
        "The key insight: governance isn't a process you follow.
        It's infrastructure you provision — once, in code,
        and Terraform Cloud enforces it on every run, for every team,
        forever."
    """),
]},
]

# ── Runner ─────────────────────────────────────────────────────────────────────

def main():
    start = 0
    if len(sys.argv) > 1:
        try:
            start = int(sys.argv[1]) - 1
        except ValueError:
            pass

    print(f"\n{B}{C}  ACME TFC Demo — Presenter Script{R}")
    print(f"  {DIM}Use arrow keys or press Enter to advance each step.{R}")
    print(f"  {DIM}Run with a step number to start from that step: python3 present.py 5{R}\n")

    for i, step in enumerate(STEPS):
        if i < start:
            continue

        hr()
        total = len(STEPS)
        print(f"  {B}[{i+1}/{total}] {step['title']}{R}")

        if step["run"]:
            cmd(step["run"])

        pause("Press Enter to see talking points")
        step["script"]()

        if step["run"]:
            pause(f"Press Enter to run:  {step['run']}")
            run_step(step["run"])
            pause("Press Enter for next step")
        else:
            pause("Press Enter for next step")

    hr()
    print(f"  {G}{B}Demo complete.{R}\n")

if __name__ == "__main__":
    main()
