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

LATEST_TAG := $(shell cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | head -1)

C := \033[36m
R := \033[0m

.PHONY: help setup status \
        sentinel-fail sentinel-pass \
        module-publish app-upgrade \
        cli-plan-dev cli-plan-staging \
        reset

help: ## List all demo scenarios
	@printf "\n  $(C)ACME TFC Demo Runbook$(R)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS=":.*## "}; {printf "  $(C)make %-20s$(R) %s\n", $$1, $$2}'
	@printf "\n  Module registry: $(C)$(LATEST_TAG)$(R) (latest)\n\n"

status: ## Show git log + module tags for both repos
	@printf "\n$(C)=== acme-apps-azure ===$(R)\n"
	@cd $(APPS_DIR) && git log --oneline -4
	@printf "\n$(C)=== terraform-azurerm-static-site ===$(R)\n"
	@cd $(MODULE_DIR) && git log --oneline -4
	@printf "Tags: " && cd $(MODULE_DIR) && git tag --sort=-v:refname | tr '\n' ' '
	@printf "\n\n"

# ── Sentinel ─────────────────────────────────────────────────────────────────

sentinel-fail: ## [Sentinel] Set access_tier=Hot → policy FAIL, apply blocked
	@printf "$(C)>>> Setting access_tier=Hot to violate Sentinel policy...$(R)\n"
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Cool\"','access_tier      = \"Hot\"',c); \
open(f,'w').write(c)"
	@cd $(APPS_DIR) && git add -A && \
	 git commit -m 'demo: set access_tier=Hot — should trigger Sentinel FAIL' && \
	 $(SSH) git push origin main
	@printf "\n  → $(TFC_DEV)\n\n"

sentinel-pass: ## [Sentinel] Revert access_tier=Cool → policy PASS, apply resumes
	@printf "$(C)>>> Reverting access_tier=Cool to fix Sentinel violation...$(R)\n"
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Hot\"','access_tier      = \"Cool\"',c); \
open(f,'w').write(c)"
	@cd $(APPS_DIR) && git add -A && \
	 git commit -m 'fix: revert access_tier=Cool — Sentinel compliant' && \
	 $(SSH) git push origin main
	@printf "\n  → $(TFC_DEV)\n\n"

# ── Module Registry ───────────────────────────────────────────────────────────

module-publish: ## [Module] Platform team pushes feature — CI runs tests then auto-tags
	@printf "$(C)>>> Platform team: pushing new feature to module repo...$(R)\n"
	@python3 $(RUNBOOK_DIR)/demo-scripts/patch_module_v1_3.py
	@cd $(MODULE_DIR) && git add -A && \
	 git commit -m 'feat: add min_tls_version variable (default TLS1_2) — non-breaking' && \
	 $(SSH) git push origin main
	@printf "\n  → CI is now running quality gate + unit tests\n"
	@printf "  → $(GH_CI)\n"
	@printf "  → If tests pass, CI will auto-tag and publish to TFC Registry\n\n"

app-upgrade: ## [App] Application team upgrades to latest published module version
	@printf "$(C)>>> Fetching latest tags from module registry...$(R)\n"
	@cd $(MODULE_DIR) && $(SSH) git fetch --tags -q
	@LATEST=$$(cd $(MODULE_DIR) && git tag --sort=-v:refname | grep '^v' | head -1) && \
	 MINOR=$$(echo $$LATEST | awk -F'[v.]' '{printf "~> %d.%d", $$2, $$3}') && \
	 printf "$(C)>>> Upgrading app to module $$MINOR ($$LATEST)...$(R)\n" && \
	 python3 -c " \
import re, sys; f='$(DEV_TF)'; minor=sys.argv[1]; c=open(f).read(); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"~> [\d.]+\"', \
         lambda m: m.group(1) + 'version = \"' + minor + '\"', c); \
open(f,'w').write(c)" "$$MINOR" && \
	 cd $(APPS_DIR) && git add -A && \
	 git commit -m "feat: upgrade to module $$MINOR" && \
	 $(SSH) git push origin main
	@printf "\n  → $(TFC_DEV)\n\n"

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## [Setup] Clone repos and terraform init (run once on a fresh machine)
	@printf "$(C)>>> Setting up demo environment...$(R)\n"
	@[ -d $(APPS_DIR) ] || $(SSH) git clone git@github.com:ngphban00/acme-apps-azure.git $(APPS_DIR)
	@[ -d $(MODULE_DIR) ] || $(SSH) git clone git@github.com:ngphban00/terraform-azurerm-static-site.git $(MODULE_DIR)
	@printf "  Initializing dev workspace...\n"
	@cd $(APPS_DIR)/envs/dev/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)'
	@printf "  Initializing staging workspace...\n"
	@cd $(APPS_DIR)/envs/staging/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)'
	@printf "  ✓ Setup complete. Run: make reset\n\n"

# ── CLI Workflow ──────────────────────────────────────────────────────────────

cli-plan-dev: ## [CLI] Run terraform plan locally — executes remotely on TFC Dev
	@printf "$(C)>>> Running terraform plan on dev (executes on TFC, streams locally)...$(R)\n"
	@[ -d $(APPS_DIR)/envs/dev/azure/.terraform ] || (printf "  Running terraform init first...\n" && cd $(APPS_DIR)/envs/dev/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)')
	@cd $(APPS_DIR)/envs/dev/azure && terraform plan

cli-plan-staging: ## [CLI] Run terraform plan locally — executes remotely on TFC Staging
	@printf "$(C)>>> Running terraform plan on staging (executes on TFC, streams locally)...$(R)\n"
	@[ -d $(APPS_DIR)/envs/staging/azure/.terraform ] || (printf "  Running terraform init first...\n" && cd $(APPS_DIR)/envs/staging/azure && terraform init -input=false -no-color 2>&1 | grep -E '(Initialized|module|Error)')
	@cd $(APPS_DIR)/envs/staging/azure && terraform plan

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
	@printf "  [2/4] Removing extra versions from TFC Registry + git tags...\n"
	@python3 $(RUNBOOK_DIR)/demo-scripts/reset_registry.py
	@cd $(MODULE_DIR) && \
	 $(SSH) git fetch --tags -q && \
	 EXTRA=$$(git tag | grep '^v' | grep -v '^v1\.0\.0$$' || true) && \
	 if [ -n "$$EXTRA" ]; then \
	   $(SSH) git push origin --delete $$EXTRA 2>/dev/null; \
	   git tag -d $$EXTRA 2>/dev/null; \
	   printf "  ✓ Deleted git tags: $$EXTRA\n"; \
	 else \
	   printf "  - No extra git tags to delete\n"; \
	 fi
	@printf "  [3/4] Resetting app version and access_tier...\n"
	@python3 -c "\
import re; f='$(DEV_TF)'; c=open(f).read(); \
c=re.sub(r'access_tier\s*=\s*\"Hot\"','access_tier      = \"Cool\"',c); \
c=re.sub(r'(source\s*=\s*\"app\.terraform\.io[^\n]*\n\s*)version = \"~> [\d.]+\"',r'\g<1>version = \"~> 1.0\"',c); \
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
