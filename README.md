# Git Repo Backup (GitHub / Azure DevOps)

Mirrors every git repo you own into a local folder and packs each one into a
`.zip` you can restore from if something bad happens. Run it by hand, on a
schedule, or in a container.

Two sources are supported — pick one per run with `SOURCE`:

| Source | What gets backed up | Runner |
| --- | --- | --- |
| **GitHub** (`SOURCE=github`) | Every repo owned by the token's user — private included, forks opt‑in | `./run-github-backup.sh` |
| **Azure DevOps** (`SOURCE=azure_devops`) | Every project's git repos, wikis and a TFVC snapshot, optionally uploaded to SharePoint | `./run-devops-backup.sh` |

Both produce the same thing:

```
tmp/
├── clone/…/<repo>        # bare git mirror — kept between runs, fetched incrementally
└── archive/…/<repo>.zip  # zip of that mirror — rewritten only when the repo changed
```

Exit code is `0` on a clean run and `1` if any repo failed (the others still run).

---

## 1. One-time setup (either source)

Needs Python 3.12 and git on the PATH.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q          # should print "26 passed"
```

---

## 2. GitHub

### Credentials

Easiest: the GitHub CLI. Log in once and the runner picks the token up automatically.

```bash
brew install gh          # if needed
gh auth login            # choose HTTPS; make sure the token has the "repo" scope
gh auth status           # should say "Logged in to github.com"
```

Or create a personal access token (classic, `repo` scope) at
https://github.com/settings/tokens and put it in `configs/github.env` as
`GITHUB_TOKEN=…`. `configs/` is gitignored.

### Run

```bash
./run-github-backup.sh                          # all your own repos
REPO_FILTER=ppg ./run-github-backup.sh          # just one repo
REPO_FILTER=ppg,ttt2 ./run-github-backup.sh     # a few
FORCE_ARCHIVE=1 ./run-github-backup.sh          # re-zip everything, changed or not
INCLUDE_FORKS=1 ./run-github-backup.sh          # also back up repos you forked
```

Zips land in `tmp/archive/github/<owner>/git/<repo>.zip`.

Any of these can live in `configs/github.env` instead of on the command line —
see `configs/github.env.example`.

---

## 3. Azure DevOps

### Credentials

1. Create a PAT in Azure DevOps (User settings → Personal access tokens) with:

   | Scope | Permission |
   | --- | --- |
   | Code | Read |
   | Wiki | Read |

   Docs: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate

2. `cp configs/devops.env.example configs/devops.env` and fill in `DEVOPS_PAT`
   and `DEVOPS_ORGANIZATION_URL` (e.g. `https://dev.azure.com/myOrganization`).

### Run

```bash
./run-devops-backup.sh
```

Zips land in `tmp/archive/<project>/git/<repo>.zip`,
`tmp/archive/<project>/wiki/<wiki>.zip` and
`tmp/archive/<project>/tfs_repo_backup.zip` (TFVC, refreshed every 10 days).

### Optional: upload zips to SharePoint

You need a SharePoint site with an App-Only principal granted:

```xml
<AppPermissionRequests AllowAppOnlyPolicy="true">
  <AppPermissionRequest Scope="http://sharepoint/content/tenant" Right="FullControl" />
</AppPermissionRequests>
```

Docs: https://learn.microsoft.com/sharepoint/dev/solution-guidance/security-apponly-azureacs

Then in `configs/devops.env` set `COPY_ARCHIVES_TO_SHAREPOINT_ENABLED=1` and
the four `SHAREPOINT_*` values. After a successful upload `tmp/archive` is
emptied (the mirrors in `tmp/clone` stay).

---

## 4. Restoring from a zip

Every zip is a bare git mirror, so all branches, tags and history are inside.

```bash
unzip ppg.zip -d ppg-bare
git clone ppg-bare ppg          # normal working copy
cd ppg && git branch -a         # everything is there
```

To push it back to a new remote: `git -C ppg-bare push --mirror <new-url>`.

---

## 5. Running on a schedule

**Mac (launchd / cron)** — the runners are self-contained, so a cron line is enough:

```
0 3 * * * cd /path/to/azure-devops-backup && ./run-github-backup.sh >> tmp/backup.log 2>&1
```

Then copy `tmp/archive` somewhere off the machine (external drive, cloud
sync folder) — a backup on the same disk isn't much of a backup.

**Docker** — both sources work in the container; the compose file exposes
every setting as an env var.

```bash
docker compose --env-file ./configs/github.env up --build            # GitHub
SOURCE=azure_devops docker compose --env-file ./configs/devops.env up --build   # Azure DevOps
```

Mirrors and zips land in `./tmp` on the host. Run the test suite in the image
with `docker build --target test .`.

---

## 6. All settings

| Name | Default | Description |
| --- | --- | --- |
| `SOURCE` | `azure_devops` | `github` or `azure_devops` (the runner scripts set this) |
| `PATH_CLONE` | `./tmp/clone` | Where git mirrors are kept |
| `PATH_ARCHIVE` | `./tmp/archive` | Where zips are written |
| `COPY_ARCHIVES_TO_SHAREPOINT_ENABLED` | `0` | `1` uploads zips to SharePoint and clears `PATH_ARCHIVE` afterwards |
| `DEBUG_MODE` | `0` | `1` waits for a debugpy client on port 5678 (see `.vscode/launch.json`) |
| **GitHub** | | |
| `GITHUB_TOKEN` | `gh auth token` | Token with `repo` scope |
| `GITHUB_OWNER` | token's user | Only back up repos owned by this account |
| `REPO_FILTER` | all | Comma-separated repo names |
| `INCLUDE_FORKS` | `0` | `1` to include repos you forked |
| `FORCE_ARCHIVE` | `0` | `1` writes a zip for every repo even when unchanged |
| **Azure DevOps** | | |
| `DEVOPS_PAT` | — | PAT with Code: Read, Wiki: Read |
| `DEVOPS_ORGANIZATION_URL` | — | e.g. `https://dev.azure.com/myOrganization` |
| **SharePoint** (only if upload enabled) | | |
| `SHAREPOINT_URL` | — | e.g. `https://myCompany.sharepoint.com/sites/backups` |
| `SHAREPOINT_DIR` | — | e.g. `Documents/DevOps` |
| `SHAREPOINT_CLIENT_ID` / `SHAREPOINT_CLIENT_SECRET` | — | App-only credentials |

---

## Development

```
.
├── app/                      # application (app/main.py is the entrypoint)
│   └── modules/              # github, azure_devops, tfs, git, sharepoint clients
├── tests/                    # pytest suite (.venv/bin/python -m pytest -q)
├── configs/                  # *.env files (gitignored) + *.env.example templates
├── run-github-backup.sh      # local runner, SOURCE=github
├── run-devops-backup.sh      # local runner, SOURCE=azure_devops
└── tmp/                      # mirrors + archives (gitignored)
```

Credentials are handed to git through the environment for each command and
are never written into a mirror's config, so the zips are safe to store
anywhere. Mirrors created by versions before 0.3.0 did carry the credential in
their `config`; the tool strips it on the next run, but zips produced by those
versions should be regenerated and the old ones deleted.
