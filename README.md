# Git Repo Backup (GitHub / Azure DevOps)

Mirrors every git repo you own into a local folder and packs each one into a
`.zip` you can restore from if something bad happens. Runs from a `gh`-logged-in
Mac with one command, or as a container / cron job.

Two sources are supported:

- **GitHub** (`SOURCE=github`) — all repos owned by the token's user (private
  included, forks excluded by default).
- **Azure DevOps** (`SOURCE=azure_devops`) — every project's git repos, wikis
  and TFVC snapshot in an organisation. Optional upload to SharePoint.

Exit code is `0` on a clean run and `1` if any repo failed (the rest still run).

## Quick start (GitHub, local Mac)

```bash
gh auth login                                   # once; needs the `repo` scope
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

./run-github-backup.sh                          # all your own repos
REPO_FILTER=ppg ./run-github-backup.sh          # just one
FORCE_ARCHIVE=1 ./run-github-backup.sh          # re-zip everything, changed or not
```

Output:

```
tmp/
├── clone/github/<owner>/git/<repo>      # bare git mirror (kept between runs, fetched incrementally)
└── archive/github/<owner>/git/<repo>.zip # zip of the mirror; only rewritten when the repo changed
```

Restore a zip:

```bash
unzip ppg.zip -d ppg-bare && git clone ppg-bare ppg
```

The zip is a bare mirror: every branch, tag and commit is in there.

Settings can also live in `configs/github.env` (gitignored, loaded by the
script) — see `configs/github.env.example`.

## Configuration

| Name                                | Default            | Description                                                  |
| ----------------------------------- | ------------------ | ------------------------------------------------------------ |
| `SOURCE`                            | `azure_devops`     | `github` or `azure_devops` (`run-github-backup.sh` sets `github`) |
| `PATH_CLONE`                        | —                  | Where git mirrors are kept                                   |
| `PATH_ARCHIVE`                      | —                  | Where zips are written                                       |
| `COPY_ARCHIVES_TO_SHAREPOINT_ENABLED` | `1` (azure) / `0` (github) | Upload zips to SharePoint and clear `PATH_ARCHIVE` afterwards |
| `DEBUG_MODE`                        | `0`                | `1` waits for a debugpy client on port 5678                  |
| **GitHub**                          |                    |                                                              |
| `GITHUB_TOKEN`                      | `gh auth token`    | Token with `repo` scope                                      |
| `GITHUB_OWNER`                      | token's user       | Only back up repos owned by this account                     |
| `REPO_FILTER`                       | all                | Comma-separated repo names                                   |
| `INCLUDE_FORKS`                     | `0`                | `1` to include repos you forked                              |
| `FORCE_ARCHIVE`                     | `0`                | `1` writes a zip for every repo even when unchanged          |
| **Azure DevOps**                    |                    |                                                              |
| `DEVOPS_PAT`                        | —                  | PAT with Code: Read, Wiki: Read                              |
| `DEVOPS_ORGANIZATION_URL`           | —                  | e.g. `https://dev.azure.com/myOrganization`                  |
| **SharePoint** (only if upload enabled) |                |                                                              |
| `SHAREPOINT_URL`                    | —                  | e.g. `https://myCompany.sharepoint.com/sites/backups`        |
| `SHAREPOINT_DIR`                    | —                  | e.g. `Documents/DevOps`                                      |
| `SHAREPOINT_CLIENT_ID` / `_SECRET`  | —                  | App-only credentials                                         |

## Running in Docker

```bash
cp configs/github.env.example configs/github.env   # fill in GITHUB_TOKEN
docker compose --env-file ./configs/github.env up --build
```

Mirrors and zips land in `./tmp` on the host. Run the tests in the image with
`docker build --target test .`.

## Development

```bash
.venv/bin/python -m pytest -q
```

Layout:

```
.
├── app/                      # application (app/main.py is the entrypoint)
│   └── modules/              # github, azure_devops, tfs, git, sharepoint clients
├── tests/
├── configs/                  # *.env files (gitignored) + github.env.example
├── run-github-backup.sh      # local one-shot runner
└── tmp/                      # mirrors + archives (gitignored)
```

## Notes

- Credentials are passed to git through the environment for each command and
  are never written into the mirror's config, so zips are safe to store
  anywhere. Mirrors created by versions before 0.3.0 had the credential in
  their `config`; the tool removes it on the next run — but any zips produced
  by those versions should be regenerated (`FORCE_ARCHIVE=1`) and the old ones
  deleted.
