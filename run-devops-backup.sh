#!/usr/bin/env bash
# Back up an Azure DevOps organisation (git repos, wikis, TFVC snapshot) to zip files.
#
#   ./run-devops-backup.sh                                   # everything in the org
#   COPY_ARCHIVES_TO_SHAREPOINT_ENABLED=1 ./run-devops-backup.sh   # also upload zips to SharePoint
#
# Reads configs/devops.env (gitignored) — copy configs/devops.env.example and fill in
# DEVOPS_PAT and DEVOPS_ORGANIZATION_URL at minimum.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f configs/devops.env ]; then
    set -a; . configs/devops.env; set +a
fi

export SOURCE=azure_devops
export PATH_CLONE="${PATH_CLONE:-$PWD/tmp/clone}"
export PATH_ARCHIVE="${PATH_ARCHIVE:-$PWD/tmp/archive}"
export COPY_ARCHIVES_TO_SHAREPOINT_ENABLED="${COPY_ARCHIVES_TO_SHAREPOINT_ENABLED:-0}"
# The app requires these to be present even when SharePoint upload is off
export SHAREPOINT_URL="${SHAREPOINT_URL:-}"
export SHAREPOINT_DIR="${SHAREPOINT_DIR:-}"
export SHAREPOINT_CLIENT_ID="${SHAREPOINT_CLIENT_ID:-}"
export SHAREPOINT_CLIENT_SECRET="${SHAREPOINT_CLIENT_SECRET:-}"
export PYTHONPATH="$PWD"

: "${DEVOPS_PAT:?Set DEVOPS_PAT (in configs/devops.env or the environment)}"
: "${DEVOPS_ORGANIZATION_URL:?Set DEVOPS_ORGANIZATION_URL, e.g. https://dev.azure.com/myOrganization}"

if [ ! -x .venv/bin/python ]; then
    echo "No .venv found — run: python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2
    exit 1
fi

exec .venv/bin/python app/main.py "$@"
