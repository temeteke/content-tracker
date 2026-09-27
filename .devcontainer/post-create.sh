#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m pip install -e "${repo_root}/backend[dev]"

if [[ -n "${NVM_DIR:-}" && -s "${NVM_DIR}/nvm.sh" ]]; then
  # The Node Dev Container Feature uses nvm.
  . "${NVM_DIR}/nvm.sh"
fi

npm --prefix "${repo_root}/frontend" ci

(
  cd "${repo_root}/backend"
  python manage.py migrate
)
