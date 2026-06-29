# ACME TFC Demo Runbook

Demo runbook for the ACME Order Portal — Terraform Cloud multi-cloud provisioning showcase.

## Repositories

| Repo | Team | Purpose |
|---|---|---|
| `terraform-azurerm-static-site` | Platform | Module code, CI quality gate, TFC Private Registry |
| `acme-apps-azure` | Application | Terraform configs consuming the module (dev + staging) |
| `acme-demo-runbook` | Presenter | This runbook — Makefile + demo scripts |

## Prerequisites (fresh machine)

```bash
git clone git@github.com:ngphban00/acme-demo-runbook.git ~/acme-demo-runbook
cd ~/acme-demo-runbook
make setup    # clones the other two repos + terraform init
make reset    # brings everything to demo starting state
```

## Demo Flow

Run all commands from `~/acme-demo-runbook`.

| Step | Command | Repo changed | What changes | Demo point |
|---|---|---|---|---|
| 0 | `make reset` | `terraform-azurerm-static-site` | Removes `min_tls_version` from module code + tests | Module back to v1.0.0 baseline |
| | | `acme-apps-azure` | dev: `version = "~> 1.0"`, `access_tier = "Cool"`; staging: `version = "1.0.0"` | App back to starting state |
| | | TFC Registry | Deletes all versions > 1.0.0 via API | Registry shows v1.0.0 only |
| 1 | `make module-publish` | `terraform-azurerm-static-site` | Adds `min_tls_version` variable + test case → commits `feat:` → pushes | CI runs quality gate (fmt + validate + terraform test) → auto-tags **v1.1.0** → TFC Registry gains new version |
| 2 | `make app-upgrade` | `acme-apps-azure` | dev: `version = "~> 1.0"` → `"~> 1.1"` | App team upgrades to new Registry version → TFC workspace triggers plan |
| 3 | `make sentinel-fail` | `acme-apps-azure` | dev: `access_tier = "Hot"` | Sentinel hard-mandatory FAIL → apply blocked, no one can override |
| 4 | `make sentinel-pass` | `acme-apps-azure` | dev: `access_tier = "Cool"` | Sentinel PASS → auto-apply — infrastructure compliant with policy |
| 5 | `make cli-plan-dev` | *(none)* | `terraform plan` runs locally, executes remotely on TFC | Developer needs no Azure credentials on laptop |
| 6 | `make cli-plan-staging` | *(none)* | `terraform plan` streams from TFC Staging | Staging on v1.0.0 (older pin) — plan detects drift vs current state |

After the full flow, run `make reset` again to confirm the cycle is clean before the real demo.

## All Targets

```
make help            List all targets with descriptions
make setup           Clone repos + terraform init (run once on a fresh machine)
make status          Show git log + module tags for both repos
make reset           Reset to demo starting state
make module-publish  Platform team: push new feature → CI quality gate → auto-tag
make app-upgrade     App team: upgrade to latest published module version
make sentinel-fail   Set access_tier=Hot → Sentinel FAIL
make sentinel-pass   Revert access_tier=Cool → Sentinel PASS + apply
make cli-plan-dev    terraform plan on dev — executes remotely on TFC
make cli-plan-staging terraform plan on staging — executes remotely on TFC
```

## Key URLs

| | |
|---|---|
| TFC Dev workspace | https://app.terraform.io/app/ngphban/acme-apps-azure-dev/runs |
| TFC Staging workspace | https://app.terraform.io/app/ngphban/acme-apps-azure-staging/runs |
| GitHub Actions (module CI) | https://github.com/ngphban00/terraform-azurerm-static-site/actions |
| TFC Private Registry | https://app.terraform.io/app/ngphban/registry/modules |
