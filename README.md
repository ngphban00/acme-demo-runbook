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
make check    # verify all tools, tokens, repos, and TFC/GitHub access
make destroy  # destroy any existing Azure resources in dev + staging
make reset    # brings code and registry to demo starting state
```

### Required before `make check` passes

| Requirement | How to set up |
|---|---|
| SSH key `~/.ssh/github-ngphban00` | `ssh-keygen -t ed25519 -f ~/.ssh/github-ngphban00` → add public key to GitHub |
| GitHub PAT `~/.github_token` | Create at https://github.com/settings/tokens (scope: `repo`) → `echo 'ghp_xxx' > ~/.github_token && chmod 600 ~/.github_token` |
| TFC token | `terraform login` |
| Terraform >= 1.7 | https://developer.hashicorp.com/terraform/install |

## Resetting for a clean demo

Run these two commands in order before every demo:

```bash
make destroy  # destroy all Azure resources in dev + staging (auto-applies, no manual approval needed)
make reset    # reset module code to v1.0.0, TFC Registry to v1.0.0 only, app configs to starting state
```

`make destroy` uses the TFC API with `auto-apply: true` override, so staging destroy does **not** require manual approval.

After both commands complete, the environment is in the following state:

| | State |
|---|---|
| TFC Registry | v1.0.0 only |
| acme-apps-azure dev | `version = "~> 1.0"`, `access_tier = "Cool"` |
| acme-apps-azure staging | `version = "1.0.0"`, no replication_type/access_tier |
| Azure resources | None (destroyed) |

## Demo Flow

Run all commands from `~/acme-demo-runbook`.

| Step | Command | Repo changed | What changes | Demo point |
|---|---|---|---|---|
| 1 | `make module-publish` | `terraform-azurerm-static-site` | Adds `min_tls_version` variable + test case → commits `feat:` → pushes | CI runs quality gate (fmt + validate + terraform test) → auto-tags **v1.1.0** → TFC Registry gains new version |
| 2 | `make app-upgrade` | `acme-apps-azure` | dev: `version = "~> 1.0"` → `"~> 1.1"` | App team upgrades to new Registry version → TFC dev triggers plan → **auto-apply** (resources created) |
| 3 | `make sentinel-fail` | `acme-apps-azure` | dev: `access_tier = "Hot"` | Sentinel hard-mandatory FAIL → apply blocked, no one can override |
| 4 | `make sentinel-pass` | `acme-apps-azure` | dev: `access_tier = "Cool"` | Sentinel PASS → **auto-apply** — infrastructure compliant with policy |
| 5 | `make speculative-dev` | *(none)* | `terraform plan` = speculative plan, streams locally, executes on TFC | CLI preview only — cannot apply from CLI on VCS-driven workspace |
| 6 | `make speculative-staging` | *(none)* | Same as above on staging | Shows same speculative behavior — to apply, must go through PR flow |
| 7 | `make pr-staging` | `acme-apps-azure` | Creates branch `release/staging-vX.Y.Z`, upgrades staging version, pushes, prints PR URL | Open PR → TFC shows speculative plan check → merge → TFC triggers real plan → **manual Confirm & Apply** in TFC UI |

## Governance contrast: dev vs staging

| | Dev | Staging |
|---|---|---|
| Auto-apply | ON — merges to main apply immediately | OFF — requires manual approval in TFC UI |
| Sentinel policy | Hot tier blocked (dev cost control) | Hot tier allowed (production-like) |
| Version constraint | `~> 1.1` (minor range, flexible) | `1.2.0` (exact pin, conservative) |
| Apply trigger | Push to main | PR → merge → **Confirm & Apply** |

## All Targets

```
make help               List all targets with descriptions
make setup              Clone repos + terraform init (run once on a fresh machine)
make status             Show git log + module tags for both repos
make destroy            Destroy all Azure resources in dev + staging
make reset              Reset code, registry, and app configs to demo starting state
make module-publish     Platform team: push new feature → CI quality gate → auto-tag
make app-upgrade        App team: upgrade dev to latest published module version
make sentinel-fail      Set access_tier=Hot on dev → Sentinel FAIL
make sentinel-pass      Revert access_tier=Cool on dev → Sentinel PASS + auto-apply
make speculative-dev    Speculative plan on dev — preview only, cannot apply from CLI
make speculative-staging Speculative plan on staging — preview only, must use PR to apply
make pr-staging         Create PR to upgrade staging → TFC check on PR → manual approve after merge
```

## Key URLs

| | |
|---|---|
| TFC Dev workspace | https://app.terraform.io/app/ngphban/acme-apps-azure-dev/runs |
| TFC Staging workspace | https://app.terraform.io/app/ngphban/acme-apps-azure-staging/runs |
| GitHub Actions (module CI) | https://github.com/ngphban00/terraform-azurerm-static-site/actions |
| TFC Private Registry | https://app.terraform.io/app/ngphban/registry/modules |
| acme-apps-azure PRs | https://github.com/ngphban00/acme-apps-azure/pulls |
