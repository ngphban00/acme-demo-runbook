"""Reset module to v1.0.0 baseline — removes min_tls_version from code and tests."""
import os, re

MODULE_DIR = os.path.expanduser("~/terraform-azurerm-static-site")

# --- variables.tf ---
vf = f"{MODULE_DIR}/variables.tf"
content = open(vf).read()
if "min_tls_version" in content:
    content = re.sub(
        r'\n\nvariable "min_tls_version" \{.*?\n\}',
        '', content, flags=re.DOTALL
    )
    open(vf, 'w').write(content)
    print("  ✓ variables.tf: removed min_tls_version")
else:
    print("  - variables.tf: already clean")

# --- main.tf ---
mf = f"{MODULE_DIR}/main.tf"
content = open(mf).read()
if "min_tls_version" in content:
    content = re.sub(r'\n  min_tls_version\s*=\s*var\.min_tls_version', '', content)
    open(mf, 'w').write(content)
    print("  ✓ main.tf: removed min_tls_version")
else:
    print("  - main.tf: already clean")

# --- README.md ---
rf = f"{MODULE_DIR}/README.md"
content = open(rf).read()
if "min_tls_version" in content:
    content = re.sub(r'\n\| min_tls_version[^\n]*\|', '', content)
    content = re.sub(r'\n\| 1\.3\.0[^\n]*\|', '', content)
    open(rf, 'w').write(content)
    print("  ✓ README.md: removed min_tls_version row")
else:
    print("  - README.md: already clean")

# --- tests/unit.tftest.hcl ---
tf = f"{MODULE_DIR}/tests/unit.tftest.hcl"
content = open(tf).read()
changed = False

for test_name in ["default_tls_is_1_2", "rejects_invalid_tls_version"]:
    if f'run "{test_name}"' in content:
        content = re.sub(
            rf'\nrun "{test_name}" \{{.*?\n\}}',
            '', content, flags=re.DOTALL
        )
        changed = True

if changed:
    open(tf, 'w').write(content)
    print("  ✓ tests/unit.tftest.hcl: removed min_tls_version test cases")
else:
    print("  - tests/unit.tftest.hcl: already clean")

print("\n  → Module at v1.0.0 baseline (no min_tls_version).")
