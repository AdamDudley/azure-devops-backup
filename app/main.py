#!/usr/bin/env python3
"""
Azure DevOps Backup

Solution to extract & transport data from Azure DevOps
into local file storage.

Script should run as CronJob with no-concurency policy,
suitable to run in container, requires persistent volume mappings.
"""

__author__ = "adam@thedudleys.co.uk"
__version__ = "0.3.0"
__license__ = "AGPLv3"

import os
import sys
import shutil
import debugpy
import time
from datetime import datetime, timedelta

from logzero import logger

from app.modules.azure_devops.main import AzureDevops
from app.modules.git.main import Git
from app.modules.github.main import GitHub
from app.modules.sharepoint.main import SharePoint
from app.modules.tfs.main import Tfs


def set_exit_code(value: int) -> None:
    global exit_code
    exit_code = value


def get_exit_code() -> int:
    global exit_code
    return exit_code


def except_hook(exctype, excvalue, exctraceback):
    import traceback

    logger.error(excvalue)
    logger.error(traceback.format_tb(exctraceback))
    sys.exit(1)


# Set initial exit code
exit_code = 0

# Set default exception handler
sys.excepthook = except_hook


def get_archive_paths(path_archive: str) -> dict:
    # Get len of path_archive to substring absolute path
    len_substring_path = len(path_archive) + 1

    dir_paths = set()
    file_paths = set()
    for subdir, dirs, files in os.walk(path_archive):
        for file in files:
            full_path = os.path.join(subdir, file)
            absolute_path = os.path.dirname(full_path)

            dir_paths.add(absolute_path[len_substring_path:])
            file_paths.add(full_path)

    return {
        "dir_paths": dir_paths,
        "file_paths": file_paths
    }


def clean_archive_path(path_archive: str) -> None:
    logger.info(f"clean_archive_path | cleaning archive path | path_archive: {path_archive}")
    if os.path.isdir(path_archive):
        shutil.rmtree(path_archive)


def get_env_vars() -> tuple:
    try:
        devops_pat = os.environ['DEVOPS_PAT']
        devops_org_url = os.environ['DEVOPS_ORGANIZATION_URL']
        path_clone = os.environ['PATH_CLONE']
        path_archive = os.environ['PATH_ARCHIVE']
        sharepoint_url = os.environ['SHAREPOINT_URL']
        sharepoint_dir = os.environ['SHAREPOINT_DIR']
        sharepoint_client_id = os.environ['SHAREPOINT_CLIENT_ID']
        sharepoint_client_secret = os.environ['SHAREPOINT_CLIENT_SECRET']
        debug_mode = os.environ.get('DEBUG_MODE', '0')  # Default to '0' if not set
        copy_archives_to_sharepoint_enabled = os.environ.get('COPY_ARCHIVES_TO_SHAREPOINT_ENABLED', '1')  # Default to '1' if not set
    except KeyError as exception:
        raise Exception(f"Missing ENV Variable: {exception}")

    return devops_pat, devops_org_url, path_clone, path_archive, sharepoint_url, sharepoint_dir, sharepoint_client_id, sharepoint_client_secret, debug_mode, copy_archives_to_sharepoint_enabled

def get_source() -> str:
    return os.environ.get('SOURCE', 'azure_devops').strip().lower()


def get_github_env_vars() -> tuple:
    try:
        github_token = os.environ['GITHUB_TOKEN']
        path_clone = os.environ['PATH_CLONE']
        path_archive = os.environ['PATH_ARCHIVE']
    except KeyError as exception:
        raise Exception(f"Missing ENV Variable: {exception}")

    github_owner = os.environ.get('GITHUB_OWNER', '')
    repo_filter = {name.strip() for name in os.environ.get('REPO_FILTER', '').split(',') if name.strip()}
    force_archive = os.environ.get('FORCE_ARCHIVE', '0') == '1'
    include_forks = os.environ.get('INCLUDE_FORKS', '0') == '1'
    debug_mode = os.environ.get('DEBUG_MODE', '0')
    copy_archives_to_sharepoint_enabled = os.environ.get('COPY_ARCHIVES_TO_SHAREPOINT_ENABLED', '0')

    return github_token, github_owner, path_clone, path_archive, repo_filter, force_archive, include_forks, debug_mode, copy_archives_to_sharepoint_enabled


def get_sharepoint_env_vars() -> tuple:
    try:
        return (os.environ['SHAREPOINT_URL'], os.environ['SHAREPOINT_DIR'],
                os.environ['SHAREPOINT_CLIENT_ID'], os.environ['SHAREPOINT_CLIENT_SECRET'])
    except KeyError as exception:
        raise Exception(f"Missing ENV Variable: {exception}")


def backup_needs_update(zip_path, max_age_days=10):
    if not os.path.exists(zip_path):
        return True
    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(zip_path))
    return file_age >= timedelta(days=max_age_days)


def sync_data(devops_pat: str, devops_org_url, path_clone: str) -> set:
    # Initialize Azure DevOps Client
    devops = AzureDevops(devops_pat, devops_org_url)

    # Initialize Git
    git = Git("", devops_pat)

    # List DevOps Projects
    projects_name = devops.list_projects_name()

    changes = set()
    for project_name in projects_name:
        # Sync project repos
        for repo in devops.list_project_repos(project_name):
            try:
                repo_name = repo['name']
                repo_remote_url = repo['remote_url']

                has_changes = git.sync(repo_remote_url, f"{path_clone}/{project_name}/git/{repo_name}")
                if has_changes:
                    changes.add(f"{project_name}/git/{repo_name}")

                logger.info(f"sync_data | syncing repos | project: {project_name} | repo: {repo_name} | has_changes: {has_changes}")
            except Exception as exception:
                logger.error(f"sync_data | syncing repos | project: {project_name} | repo: {repo_name} | exception: {exception}")
                set_exit_code(1)
                continue

        # # Sync project wikis
        for wiki in devops.list_project_wikis(project_name):
            try:
                wiki_name = wiki['name']
                wiki_remote_url = wiki['remote_url']

                has_changes = git.sync(wiki_remote_url, f"{path_clone}/{project_name}/wiki/{wiki_name}")
                if has_changes:
                    changes.add(f"{project_name}/wiki/{wiki_name}")

                logger.info(f"sync_data | syncing wikis | project: {project_name} | wiki: {wiki_name} | has_changes: {has_changes}")
            except Exception as exception:
                logger.error(f"sync_data | syncing repos | project: {project_name} | repo: {wiki_name} | exception: {exception}")
                set_exit_code(1)
                continue

        # Sync project TFS repos
        tfs_repos = devops.list_project_tfs_repos(project_name)
        if tfs_repos:
            try:
                tfs = Tfs(organization_url=devops_org_url, personal_access_token=devops_pat)
                zip_path = f"{path_clone}/{project_name}/tfs_repo_backup.zip"
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(zip_path), exist_ok=True)
                
                if backup_needs_update(zip_path):
                    # Download the project as a zip
                    tfs.download_repo_zip(project_name, zip_path)
                    logger.info(f"sync_data | downloaded TFS repo | project: {project_name} | zip_path: {zip_path}")
                    changes.add(f"{project_name}/tfs_repo_backup.zip")
                else:
                    logger.info(f"sync_data | skipping TFS repo download, recent backup exists | project: {project_name} | zip_path: {zip_path}")
            except Exception as exception:
                logger.error(f"sync_data | downloading TFS repo | project: {project_name} | exception: {exception}")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.warning(f"sync_data | deleted partially downloaded TFS repo zip | project: {project_name} | zip_path: {zip_path}")
                set_exit_code(1)
            
    return changes


def sync_github_data(github_token: str, github_owner: str, path_clone: str, repo_filter: set = None, force_archive: bool = False, include_forks: bool = False) -> set:
    github = GitHub(github_token, github_owner)
    owner = github.owner

    # GitHub accepts any username with a token as the password for basic auth
    git = Git("x-access-token", github_token)

    repos = github.list_repos()
    if not include_forks:
        # Forks are somebody else's work; skip them unless explicitly asked for
        repos = [repo for repo in repos if not repo.get('fork', False)]
    if repo_filter:
        available = {repo['name'] for repo in repos}
        for missing in sorted(repo_filter - available):
            logger.error(f"sync_github_data | repo in REPO_FILTER not found | owner: {owner} | repo: {missing}")
            set_exit_code(1)
        repos = [repo for repo in repos if repo['name'] in repo_filter]

    changes = set()
    for repo in repos:
        repo_name = repo['name']
        key = f"github/{owner}/git/{repo_name}"
        try:
            has_changes = git.sync(repo['remote_url'], f"{path_clone}/{key}")
            if has_changes or force_archive:
                changes.add(key)

            logger.info(f"sync_github_data | syncing repos | owner: {owner} | repo: {repo_name} | has_changes: {has_changes}")
        except Exception as exception:
            logger.error(f"sync_github_data | syncing repos | owner: {owner} | repo: {repo_name} | exception: {exception}")
            set_exit_code(1)
            continue

    return changes


def archive_changes(path_clone: str, path_archive: str, changes: set):
    if len(changes) == 0:
        logger.info("archive_changes | no changes detected")
        return

    for change in changes:
        if change.endswith('.zip'):
            # For already zipped files, just copy them
            source_path = f"{path_clone}/{change}"
            dest_path = f"{path_archive}/{change}"
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)  # Ensure the destination directory exists
            logger.info(f"archive_changes | copying zipped file: {change}")
            shutil.copy2(source_path, dest_path)
        else:
            # For unzipped changes, create a zip archive
            logger.info(f"archive_changes | archiving changes: {change}.zip")
            shutil.make_archive(f"{path_archive}/{change}", 'zip', f"{path_clone}/{change}")


def upload_changes_to_sharepoint(sharepoint_url: str, sharepoint_client_id: str, sharepoint_client_secret: str, path_archive: str, sharepoint_dir: str):
    # Get len of path_archive to substring absolute path
    len_substring_path = len(path_archive) + 1

    # Collect paths required to upload files to SharePoint
    archive_paths = get_archive_paths(path_archive)
    dir_paths = archive_paths['dir_paths']
    file_paths = archive_paths['file_paths']

    # Get SharePoint client
    shp = SharePoint(sharepoint_url, sharepoint_client_id, sharepoint_client_secret)

    # Ensure dir_paths exists in SharePoint
    for dir_path in dir_paths:
        logger.info(f"upload_changes_to_sharepoint | ensuring dir exists | sharepoint_dir: {sharepoint_dir} | dir_path: {dir_path}")
        shp.ensure_dir_exists(sharepoint_dir, dir_path)

    # Upload files to SharePoint
    for file_path in file_paths:
        full_dir_path = os.path.dirname(file_path)
        relative_dir_path = full_dir_path[len_substring_path:]

        logger.info(f"upload_changes_to_sharepoint | upload file | sharepoint_dir: {sharepoint_dir} | relative_dir_path: {relative_dir_path} | file_path: {file_path}")
        shp.upload_file(sharepoint_dir, relative_dir_path, file_path)

    clean_archive_path(path_archive)


def wait_for_debugger(debug_mode: str) -> None:
    # Check for debug mode, if we are we'll wait for the debugger to attach
    # in VS code, CTRL+SHIFT+D, click play next to 'Python Debugger: Remote Attach'
    if debug_mode == '1':
        print("Debug mode is on. Waiting for debugger to attach...")
        debugpy.listen(("0.0.0.0", 5678))
        debugpy.wait_for_client()
        print("Debugger attached!")


def main():
    source = get_source()

    if source == 'github':
        github_token, github_owner, path_clone, path_archive, repo_filter, force_archive, include_forks, debug_mode, copy_archives_to_sharepoint_enabled = get_github_env_vars()
        wait_for_debugger(debug_mode)

        # Sync local data with remote
        changes = sync_github_data(github_token, github_owner, path_clone, repo_filter, force_archive, include_forks)
    elif source == 'azure_devops':
        # Get ENV Variables
        devops_pat, devops_org_url, path_clone, path_archive, sharepoint_url, sharepoint_dir, sharepoint_client_id, sharepoint_client_secret, debug_mode, copy_archives_to_sharepoint_enabled = get_env_vars()
        wait_for_debugger(debug_mode)

        # Sync local data with remote
        changes = sync_data(devops_pat, devops_org_url, path_clone)
    else:
        raise Exception(f"Unknown SOURCE: {source} (expected 'github' or 'azure_devops')")

    # Archive changes found during sync
    archive_changes(path_clone, path_archive, changes)

    # Upload archived changes into sharepoint if enabled
    if copy_archives_to_sharepoint_enabled == '1':
        sharepoint_url, sharepoint_dir, sharepoint_client_id, sharepoint_client_secret = get_sharepoint_env_vars()
        upload_changes_to_sharepoint(sharepoint_url, sharepoint_client_id, sharepoint_client_secret, path_archive, sharepoint_dir)
    else:
        logger.info(f"Skipping upload to SharePoint as COPY_ARCHIVES_TO_SHAREPOINT_ENABLED is not '1' | archives kept in: {path_archive}")

    # Exit script with exit code
    sys.exit(get_exit_code())


if __name__ == "__main__":
    main()
