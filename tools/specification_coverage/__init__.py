"""Split support package for the specification-coverage checker (tools/check_specification_coverage.py)."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYTHON_PACKAGES = _REPO_ROOT / "implementations" / "python" / "packages"
for _import_root in (_REPO_ROOT, _PYTHON_PACKAGES):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))
