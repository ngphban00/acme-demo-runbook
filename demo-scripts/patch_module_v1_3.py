"""Platform team: patch module — add min_tls_version variable + tests."""
import os

MODULE_DIR = os.path.expanduser("~/terraform-azurerm-static-site")

# --- variables.tf ---
vars_file = f"{MODULE_DIR}/variables.tf"
content = open(vars_file).read()

if "min_tls_version" not in content:
    content += """
variable "min_tls_version" {
  type        = string
  description = "Minimum TLS version enforced on the storage account"
  default     = "TLS1_2"

  validation {
    condition     = contains(["TLS1_0", "TLS1_1", "TLS1_2"], var.min_tls_version)
    error_message = "min_tls_version must be TLS1_0, TLS1_1, or TLS1_2."
  }
}
"""
    open(vars_file, "w").write(content)
    print("  ✓ variables.tf: added min_tls_version")
else:
    print("  ⚠ variables.tf: min_tls_version already present")

# --- main.tf ---
main_file = f"{MODULE_DIR}/main.tf"
content = open(main_file).read()

if "min_tls_version" not in content:
    content = content.replace(
        "  access_tier              = var.access_tier",
        "  access_tier              = var.access_tier\n  min_tls_version          = var.min_tls_version",
    )
    open(main_file, "w").write(content)
    print("  ✓ main.tf: added min_tls_version to storage account")
else:
    print("  ⚠ main.tf: min_tls_version already present")

# --- README.md ---
readme_file = f"{MODULE_DIR}/README.md"
content = open(readme_file).read()

if "min_tls_version" not in content:
    content = content.replace(
        "| access_tier | Storage access tier (Hot/Cool) | string | no (default: Hot) |",
        "| access_tier | Storage access tier (Hot/Cool) | string | no (default: Hot) |\n| min_tls_version | Minimum TLS version (TLS1_0/TLS1_1/TLS1_2) | string | no (default: TLS1_2) |",
    )
    content = content.replace(
        "| 1.2.0 | Add `access_tier` variable (default Hot) — non-breaking |",
        "| 1.2.0 | Add `access_tier` variable (default Hot) — non-breaking |\n| 1.3.0 | Add `min_tls_version` variable (default TLS1_2) — non-breaking |",
    )
    open(readme_file, "w").write(content)
    print("  ✓ README.md: updated inputs table and versioning")

# --- tests/unit.tftest.hcl: add min_tls_version test cases ---
test_file = f"{MODULE_DIR}/tests/unit.tftest.hcl"
content = open(test_file).read()

if "min_tls_version" not in content:
    tls_default_test = '''
run "default_tls_is_1_2" {
  assert {
    condition     = azurerm_storage_account.site.min_tls_version == "TLS1_2"
    error_message = "Default min_tls_version must be TLS1_2"
  }
}
'''
    tls_validation_test = '''
run "rejects_invalid_tls_version" {
  variables {
    min_tls_version = "TLS1_3"
  }
  expect_failures = [var.min_tls_version]
}
'''
    # Insert default test after default_replication_is_lrs block
    content = content.replace(
        '\n# ── Mandatory tags',
        tls_default_test + '\n# ── Mandatory tags'
    )
    # Insert validation test after rejects_invalid_replication_type block
    content = content.replace(
        '\n# ── Custom values pass through',
        tls_validation_test + '\n# ── Custom values pass through'
    )
    open(test_file, "w").write(content)
    print("  ✓ tests/unit.tftest.hcl: added min_tls_version test cases")
else:
    print("  ⚠ tests/unit.tftest.hcl: min_tls_version tests already present")

print("\n  → Module patched. CI will run tests and auto-tag on push.")
