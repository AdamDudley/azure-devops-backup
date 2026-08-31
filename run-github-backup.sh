#!/usr/bin/env bash
# Back up your GitHub repos to zip files on this machine (no Docker, no SharePoint).
#
#   ./run-github-backup.sh                       # all your own (non-fork) repos
#   REPO_FILTER=ppg ./run-github-backup.sh       # just ppg
#   REPO_FILTER=ppg,ttt2 FORCE_ARCHIVE=1 ./run-github-backup.sh   # re-zip even if unchanged
#
# Token: uses $GITHUB_TOKEN if set, otherwise `gh auth token` (needs `gh auth login` once).
# Optional overrides live in configs/github.env (gitignored) — see configs/github.env.example.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f configs/github.env ]; then
    set -a; . configs/github.env; set +a
fi

export SOURCE=github
export GITHUB_TOKEN="${GITHUB_TOKEN:-$(gh auth token)}"
export PATH_CLONE="${PATH_CLONE:-$PWD/tmp/clone}"
export PATH_ARCHIVE="${PATH_ARCHIVE:-$PWD/tmp/archive}"
export COPY_ARCHIVES_TO_SHAREPOINT_ENABLED="${COPY_ARCHIVES_TO_SHAREPOINT_ENABLED:-0}"
export PYTHONPATH="$PWD"

if [ ! -x .venv/bin/python ]; then
    echo "No .venv found — run: python3.12 -m venv .venv && .venv/bin/pip install -r app/requirements.txt" >&2
    exit 1
fi

exec .venv/bin/python app/main.py "$@"
