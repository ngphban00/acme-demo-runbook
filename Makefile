SHELL    := /bin/bash
.DEFAULT_GOAL := help

RUNBOOK_DIR := $(HOME)/acme-demo-runbook
APPS_DIR    := $(HOME)/acme-apps-azure
MODULE_DIR  := $(HOME)/terraform-azurerm-static-site
DEV_TF     := $(APPS_DIR)/envs/dev/azure/main.tf
STG_TF     := $(APPS_DIR)/envs/staging/azure/main.tf
SSH        := GIT_SSH_COMMAND='ssh -i $(HOME)/.ssh/github-ngphban00 -o StrictHostKeyChecking=no'

TFC_DEV  := https://app.terraform.io/app/ngphban/acme-apps-azure-dev/runs
TFC_STG  := https://app.terraform.io/app/ngphban/acme-apps-azure-staging/runs
GH_CI    := https://github.com/ngphban00/terraform-azurerm-static-site/actions
GH_APPS  := https://github.com/ngphban00/acme-apps-azure

LATEST_TAG := $(shell cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | head -1)

C := \033[36m
R := \033[0m
Y := \033[33m

.PHONY: help check setup status \
        sentinel-fail sentinel-pass \
        module-publish app-upgrade \
        speculative-dev speculative-staging \
        pr-staging \
        destroy reset

check: ## Verify all tools, tokens, repos and TFC/GitHub access before demo
	@python3 $(RUNBOOK_DIR)/demo-scripts/preflight.py

help: ## List all demo scenarios
	@printf "\n  $(C)ACME TFC Demo Runbook$(R)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS=":.*## "}; {printf "  $(C)make %-22s$(R) %s\n", $$1, $$2}'
	@printf "\n  Module registry: $(C)$(LATEST_TAG)$(R) (latest)\n\n"

status: ## Show git log + module tags for both repos
	@printf "\n$(C)=== acme-apps-azure ===$(R)\n"
	@cd $(APPS_DIR) && git log --oneline -4
	@printf "\n$(C)=== terraform-azurerm-static-site ===$(R)\n"
	@cd $(MODULE_DIR) && git log --oneline -4
	@printf "Tags: " && cd $(MODULE_DIR) && git tag --sort=-v:refname | tr '\n' ' '
	@printf "\n\n"

# ── Sentinel ──────────────────────────────────────────────────────────────────

sentinel-fail: ## [Sentinel] Set access_tier=Hot on dev → Sentinel FAIL, apply blocked
	@printf "$(C)>>> Setting access_tier=Hot to trigger Sentinel policy violation...$(R)\n"
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Cool\"','access_tier      = \"Hot\"',c); \
open(f,'w').write(c)"
	@cd $(APPS_DIR) && git add -A && \
	 git commit -m 'demo: set access_tier=Hot — should trigger Sentinel FAIL' && \
	 $(SSH) git push origin main
	@printf "\n  → TFC dev workspace: plan will pass, Sentinel will block apply\n"
	@printf "  → $(TFC_DEV)\n\n"

sentinel-pass: ## [Sentinel] Revert access_tier=Cool on dev → Sentinel PASS, auto-apply
	@printf "$(C)>>> Reverting access_tier=Cool to fix Sentinel violation...$(R)\n"
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Hot\"','access_tier      = \"Cool\"',c); \
open(f,'w').write(c)"
	@cd $(APPS_DIR) && git add -A && \
	 git commit -m 'fix: revert access_tier=Cool — Sentinel compliant' && \
	 $(SSH) git push origin main
	@printf "\n  → TFC dev workspace: plan + Sentinel pass → auto-apply (no human needed)\n"
	@printf "  → $(TFC_DEV)\n\n"

# ── Module Registry ───────────────────────────────────────────────────────────

module-publish: ## [Module] Platform team pushes feature — CI quality gate → auto-tag
	@printf "$(C)>>> Platform team: pushing new feature to module repo...$(R)\n"
	@python3 $(RUNBOOK_DIR)/demo-scripts/patch_module_v1_3.py
	@cd $(MODULE_DIR) && git add -A && \
	 git commit -m 'feat: add min_tls_version variable (default TLS1_2) — non-breaking' && \
	 $(SSH) git push origin main
	@printf "\n  → CI is running: fmt-check → validate → terraform test\n"
	@printf "  → On pass: CI auto-tags next minor version → TFC Registry picks it up\n"
	@printf "  → $(GH_CI)\n\n"

app-upgrade: ## [App] Application team upgrades dev to latest published module version
	@printf "$(C)>>> Fetching latest module version from registry...$(R)\n"
	@cd $(MODULE_DIR) && $(SSH) git fetch --tags -q
	@LATEST=$$(cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | head -1) && \
	 MINOR=$$(echo $$LATEST | awk -F'[v.]' '{printf "~> %d.%d", $$2, $$3}') && \
	 printf "$(C)>>> Upgrading dev to module $$MINOR ($$LATEST)...$(R)\n" && \
	 python3 -c " \
import re, sys; f='$(DEV_TF)'; minor=sys.argv[1]; c=open(f).read(); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"~> [\d.]+\"', \
         lambda m: m.group(1) + 'version = \"' + minor + '\"', c); \
open(f,'w').write(c)" "$$MINOR" && \
	 cd $(APPS_DIR) && git add -A && \
	 git commit -m "feat: upgrade dev to module $$MINOR" && \
	 $(SSH) git push origin main
	@printf "\n  → Push to main → TFC dev workspace auto-triggers plan + apply\n"
	@printf "  → $(TFC_DEV)\n\n"

# ── CLI: Speculative Plan ─────────────────────────────────────────────────────
# terraform plan against a TFC workspace creates a SPECULATIVE plan:
# read-only preview, never applies, no approval button.
# To apply, changes must go through the VCS flow (branch → PR → merge).

speculative-dev: ## [CLI] Speculative plan on dev — preview only, cannot apply
	@printf "$(C)>>> Speculative plan on dev (read-only preview, will not apply)...$(R)\n"
	@printf "$(Y)  Note: 'terraform plan' on a VCS-driven workspace = speculative plan.\n"
	@printf "  To apply, push to main — TFC will auto-apply on dev.$(R)\n\n"
	@cd $(APPS_DIR)/envs/dev/azure && \
	 terraform init -upgrade -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)' && \
	 terraform plan

speculative-staging: ## [CLI] Speculative plan on staging — preview only, cannot apply
	@printf "$(C)>>> Speculative plan on staging (read-only preview, will not apply)...$(R)\n"
	@printf "$(Y)  Note: 'terraform plan' on a VCS-driven workspace = speculative plan.\n"
	@printf "  To apply, open a PR → merge → TFC triggers plan → manually approve in UI.$(R)\n\n"
	@cd $(APPS_DIR)/envs/staging/azure && \
	 terraform init -upgrade -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)' && \
	 terraform plan

# ── VCS Flow: PR → Merge → TFC → Manual Approve ──────────────────────────────

pr-staging: ## [VCS] Open a PR to upgrade staging — shows TFC check on PR, manual approve after merge
	@printf "$(C)>>> Creating PR to upgrade staging module version...$(R)\n"
	@cd $(MODULE_DIR) && $(SSH) git fetch --tags -q
	@LATEST=$$(cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | head -1) && \
	 BRANCH="release/staging-$$LATEST" && \
	 printf "$(C)>>> Upgrading staging to module $$LATEST on branch $$BRANCH...$(R)\n" && \
	 cd $(APPS_DIR) && $(SSH) git fetch origin -q && git checkout -B $$BRANCH origin/main && \
	 python3 -c " \
import re, sys; f='$(STG_TF)'; ver=sys.argv[1]; c=open(f).read(); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"[\d.]+\"', \
         lambda m: m.group(1) + 'version = \"' + ver + '\"', c); \
c=re.sub(r'(azure_region[^\n]*\n)', \
         r'\1  replication_type = \"GRS\"\n  access_tier      = \"Hot\"\n', c) \
  if 'replication_type' not in c else c; \
open(f,'w').write(c)" "$$LATEST" && \
	 git add -A && \
	 git commit -m "feat: upgrade staging to module $$LATEST" && \
	 $(SSH) git push origin $$BRANCH && \
	 python3 $(RUNBOOK_DIR)/demo-scripts/create_pr.py $$BRANCH $$LATEST && \
	 printf "\n  → $(TFC_STG)\n\n" && \
	 cd $(APPS_DIR) && git checkout main

# ── Destroy ───────────────────────────────────────────────────────────────────

destroy: ## Destroy all resources in dev + staging (run before reset for clean demo)
	@printf "$(C)>>> Destroying all resources in dev and staging workspaces...$(R)\n"
	@printf "$(Y)  This will destroy real Azure infrastructure. Ctrl-C to abort.$(R)\n"
	@sleep 3
	@python3 $(RUNBOOK_DIR)/demo-scripts/destroy_workspaces.py

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## [Setup] Clone repos and terraform init (run once on a fresh machine)
	@printf "$(C)>>> Setting up demo environment...$(R)\n"
	@[ -d $(APPS_DIR) ] || $(SSH) git clone git@github.com:ngphban00/acme-apps-azure.git $(APPS_DIR)
	@[ -d $(MODULE_DIR) ] || $(SSH) git clone git@github.com:ngphban00/terraform-azurerm-static-site.git $(MODULE_DIR)
	@printf "  Initializing dev workspace...\n"
	@cd $(APPS_DIR)/envs/dev/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)'
	@printf "  Initializing staging workspace...\n"
	@cd $(APPS_DIR)/envs/staging/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)'
	@[ -f $(HOME)/.github_token ] && printf "  ✓ GitHub token found\n" || \
	  printf "  $(Y)⚠ GitHub token missing — create one at https://github.com/settings/tokens\n    then: echo 'ghp_xxx' > ~/.github_token && chmod 600 ~/.github_token$(R)\n"
	@printf "  Tagging baseline commit as v1.0.0 (one-time, never overwritten)...\n"
	@cd $(MODULE_DIR) && $(SSH) git fetch --tags -q && \
	 if ! git tag | grep -q '^v1\.0\.0$$'; then \
	   git tag v1.0.0 && \
	   $(SSH) git push origin v1.0.0 && \
	   printf "  → Pushed v1.0.0 — waiting 45s for TFC Registry webhook...\n" && \
	   sleep 45 && \
	   printf "  ✓ v1.0.0 published to TFC Registry\n"; \
	 else \
	   printf "  ✓ v1.0.0 tag already exists (skipped)\n"; \
	 fi
	@printf "  ✓ Setup complete. Run: make destroy && make reset\n\n"

# ── Reset ─────────────────────────────────────────────────────────────────────

reset: ## Reset demo: app on v1.0, registry on v1.0.0 only, module at baseline
	@printf "$(C)>>> Resetting to demo starting state...$(R)\n"
	@printf "  [1/4] Resetting module code to v1.0.0 baseline...\n"
	@python3 $(RUNBOOK_DIR)/demo-scripts/reset_module.py
	@cd $(MODULE_DIR) && \
	 if ! git diff --quiet HEAD; then \
	   git add -A && \
	   git commit -m 'chore: reset module to v1.0.0 baseline' && \
	   $(SSH) git push origin main; \
	 else \
	   printf "  - module code: already at baseline\n"; \
	 fi
	@printf "  [2/4] Verifying v1.0.0 baseline tag + removing extra versions...\n"
	@cd $(MODULE_DIR) && $(SSH) git fetch --tags -q && \
	 if ! git tag | grep -q '^v1\.0\.0$$'; then \
	   printf "$(Y)  ✗ v1.0.0 git tag missing — it must point to the original baseline commit.\n"; \
	   printf "    Re-run: make setup  (will tag current HEAD as v1.0.0)\n$(R)"; \
	   exit 1; \
	 fi
	@python3 $(RUNBOOK_DIR)/demo-scripts/reset_registry.py
	@cd $(MODULE_DIR) && \
	 EXTRA=$$(git tag | grep '^v' | grep -v '^v1\.0\.0$$' || true) && \
	 if [ -n "$$EXTRA" ]; then \
	   $(SSH) git push origin --delete $$EXTRA 2>/dev/null; \
	   git tag -d $$EXTRA 2>/dev/null; \
	   printf "  ✓ Deleted git tags: $$EXTRA\n"; \
	 else \
	   printf "  - No extra git tags to delete\n"; \
	 fi
	@printf "  [3/4] Resetting app version and access_tier...\n"
	@cd $(APPS_DIR) && git checkout main -q && $(SSH) git fetch origin -q && git reset --hard origin/main -q
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Hot\"','access_tier      = \"Cool\"',c); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"~> [\d.]+\"',r'\g<1>version = \"~> 1.0\"',c); \
open(f,'w').write(c)"
	@python3 -c "\
import re; f='$(STG_TF)'; c=open(f).read(); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"[\d.]+\"',r'\g<1>version = \"1.0.0\"',c); \
c=re.sub(r'\n  replication_type\s*=\s*\"[^\"]+\"','',c); \
c=re.sub(r'\n  access_tier\s*=\s*\"[^\"]+\"','',c); \
open(f,'w').write(c)"
	@cd $(APPS_DIR) && \
	 if ! git diff --quiet HEAD; then \
	   git add -A && \
	   git commit -m 'chore: reset to demo starting state (app v1.0, Cool tier)' && \
	   $(SSH) git push origin main; \
	 else \
	   printf "  - app: already at starting state\n"; \
	 fi
	@printf "  [4/4] Verifying...\n"
	@printf "  ✓ App: consuming module ~> 1.0\n"
	@printf "  ✓ Registry: " && cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | tr '\n' ' '
	@printf "\n\n"
