#!/usr/bin/env bash
# Praxis release helper.
#
# Usage:
#   scripts/release.sh <version>          # everything except PyPI upload
#   scripts/release.sh <version> --pypi   # also build & upload to PyPI (needs creds)
#
# What it does (in order; aborts on first failure):
#   1. Verify clean working tree + main branch
#   2. Bump version in pyproject.toml + __init__.py
#   3. Verify CHANGELOG.md has an entry for this version
#   4. Run the full CI gate locally (ruff, ruff format, mypy, pytest)
#   5. Build sdist + wheel under packages/core-py/dist/
#   6. (Optional) twine upload to PyPI
#   7. Commit, tag, push
#   8. Print the GitHub release-create command to run

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <version> [--pypi]" >&2
  exit 64
fi

VERSION="$1"
WITH_PYPI=0
if [[ "${2:-}" == "--pypi" ]]; then
  WITH_PYPI=1
fi

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# -------- step 1: working tree state --------
if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty. Commit or stash before releasing." >&2
  exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" != "main" ]]; then
  echo "release must be cut from main (you are on $BRANCH)." >&2
  exit 1
fi

# -------- step 2: bump version --------
echo "bumping version to $VERSION"
python3 - <<PY
import re, pathlib
ver = "$VERSION"
init = pathlib.Path("packages/core-py/praxis_core/__init__.py")
init.write_text(re.sub(r'__version__ = "[^"]+"', f'__version__ = "{ver}"', init.read_text()))
pyproject = pathlib.Path("packages/core-py/pyproject.toml")
pyproject.write_text(re.sub(r'^version = "[^"]+"', f'version = "{ver}"', pyproject.read_text(), count=1, flags=re.M))
print("  version stamped in __init__.py and pyproject.toml")
PY

# -------- step 3: CHANGELOG check --------
if ! grep -q "^## \[$VERSION\]" CHANGELOG.md; then
  echo "CHANGELOG.md is missing an entry for [$VERSION]. Add one and re-run." >&2
  exit 1
fi

# -------- step 4: full local gate --------
echo "running full local CI gate"
cd packages/core-py
ruff check .
ruff format --check .
mypy praxis_core
pytest -q
cd "$ROOT"

# -------- step 5: build --------
echo "building sdist + wheel"
cd packages/core-py
rm -rf dist build *.egg-info
python3 -m pip install --quiet --upgrade build
python3 -m build
cd "$ROOT"
ls -lh packages/core-py/dist/

# -------- step 6: pypi upload (optional) --------
if [[ $WITH_PYPI -eq 1 ]]; then
  echo "uploading to PyPI (twine)"
  python3 -m pip install --quiet --upgrade twine
  cd packages/core-py
  python3 -m twine upload dist/*
  cd "$ROOT"
fi

# -------- step 7: commit + tag + push --------
echo "committing version bump and tagging"
git add packages/core-py/pyproject.toml packages/core-py/praxis_core/__init__.py
git commit -m "release: v$VERSION"
git tag -a "v$VERSION" -m "Praxis v$VERSION"
git push origin main
git push origin "v$VERSION"

# -------- step 8: nudge the github release --------
cat <<EOF

Released v$VERSION.
  - Commit & tag pushed to origin/main.
  - Build artifacts: packages/core-py/dist/

Next: create the GitHub release with the CHANGELOG entry as the body.
  gh -R ikatyal2110/openclaw-to-hermes release create v$VERSION --title "..." --notes-file <(awk '/^## \[$VERSION\]/{flag=1; next} /^## \[/{flag=0} flag' CHANGELOG.md)
EOF
