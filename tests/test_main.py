import os

import pytest
from unittest import mock

from app import main as app


@mock.patch("app.main.get_sharepoint_env_vars", return_value=("", "", "", ""))
@mock.patch("app.main.upload_changes_to_sharepoint")
@mock.patch("app.main.archive_changes")
@mock.patch("app.main.sync_data")
@mock.patch("app.main.get_env_vars")
def test__main__success(get_env_vars, sync_data, archive_changes, upload_changes_to_sharepoint, get_sharepoint_env_vars):
    """Check Main to complete with exit code 0 (success)"""

    get_env_vars.return_value = ("", "", "", "", "", "", "", "", "", "1")  # Add "1" at the end
    sync_data.return_value = set()
    archive_changes.return_value = None
    upload_changes_to_sharepoint.return_value = None

    # Try run script
    with pytest.raises(SystemExit) as e:
        app.main()

    # Check results
    assert e.type == SystemExit
    assert e.value.code == 0


@mock.patch("app.main.get_sharepoint_env_vars", return_value=("", "", "", ""))
@mock.patch("app.main.get_env_vars")
@mock.patch("app.main.sync_data")
@mock.patch("app.main.archive_changes")
@mock.patch("app.main.upload_changes_to_sharepoint")
def test__main__fail(upload_changes_to_sharepoint, archive_changes, sync_data, get_env_vars, get_sharepoint_env_vars):
    """Check Main to complete with exit code 1 (fail)"""

    get_env_vars.return_value = ("", "", "", "", "", "", "", "", "", "1")  # Add "1" at the end
    sync_data.return_value = set()
    archive_changes.return_value = None
    upload_changes_to_sharepoint.return_value = None

    # Set exit code
    app.set_exit_code(1)

    # Try run script
    with pytest.raises(SystemExit) as e:
        app.main()

    # Check results
    assert e.type == SystemExit
    assert e.value.code > 0


def test__get_env_vars__success():
    """Check if ENV Vars are returned properly"""

    # Set ENV Vars
    os.environ['DEVOPS_PAT'] = "DEVOPS_PAT"
    os.environ['DEVOPS_ORGANIZATION_URL'] = "DEVOPS_ORGANIZATION_URL"
    os.environ['PATH_CLONE'] = "PATH_CLONE"
    os.environ['PATH_ARCHIVE'] = "PATH_ARCHIVE"
    os.environ['SHAREPOINT_URL'] = "SHAREPOINT_URL"
    os.environ['SHAREPOINT_DIR'] = "SHAREPOINT_DIR"
    os.environ['SHAREPOINT_CLIENT_ID'] = "SHAREPOINT_CLIENT_ID"
    os.environ['SHAREPOINT_CLIENT_SECRET'] = "SHAREPOINT_CLIENT_SECRET"
    os.environ['DEBUG_MODE'] = "0"  # Add this line
    os.environ['COPY_ARCHIVES_TO_SHAREPOINT_ENABLED'] = "1"  # Add this line

    # Check return
    assert app.get_env_vars() == ("DEVOPS_PAT", "DEVOPS_ORGANIZATION_URL", "PATH_CLONE", "PATH_ARCHIVE", 
                                  "SHAREPOINT_URL", "SHAREPOINT_DIR", "SHAREPOINT_CLIENT_ID", 
                                  "SHAREPOINT_CLIENT_SECRET", "0", "1")  # Add "1" at the end


def test__get_env_vars__fail():
    """Check if Exception is raised when ENV Variable is missing"""

    # Delete env variables if are present
    for env_name in ['DEVOPS_PAT', 'DEVOPS_ORGANIZATION_URL', 'PATH_CLONE', 'PATH_ARCHIVE', 
                     'SHAREPOINT_URL', 'SHAREPOINT_DIR', 'SHAREPOINT_CLIENT_ID', 
                     'SHAREPOINT_CLIENT_SECRET', 'DEBUG_MODE', 'COPY_ARCHIVES_TO_SHAREPOINT_ENABLED']:  # Add 'COPY_ARCHIVES_TO_SHAREPOINT_ENABLED' to this list
        if env_name in os.environ:
            del os.environ[env_name]

    # Expect exception
    with pytest.raises(Exception):
        app.get_env_vars()


@mock.patch("app.main.AzureDevops.list_projects_name")
@mock.patch("app.main.AzureDevops.__init__", return_value=None)
@mock.patch("app.main.Git.__init__", return_value=None)
def test__sync_data__no_projects(git_init, devops_init, devops_list_projects_name):
    """Check if no changes are detected when no projects are found"""

    devops_list_projects_name.return_value = set()

    # Assert that no changes are found
    assert app.sync_data("", "", "") == set()


@mock.patch("app.main.AzureDevops.list_project_tfs_repos", new=mock.Mock(return_value=[]))
@mock.patch("app.main.AzureDevops.list_project_wikis")
@mock.patch("app.main.AzureDevops.list_project_repos")
@mock.patch("app.main.AzureDevops.list_projects_name")
@mock.patch("app.main.AzureDevops.__init__", return_value=None)
@mock.patch("app.main.Git.sync")
@mock.patch("app.main.Git.__init__", return_value=None)
def test__sync_data__no_changes(git_init, git_sync, devops_init, devops_list_projects_name, devops_list_project_repos, devops_list_project_wikis):
    """Check if no changes are returned when aren't detected"""

    devops_list_projects_name.return_value = ('Project_1', 'Project_2')
    devops_list_project_repos.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    devops_list_project_wikis.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    git_sync.return_value = False

    # Assert that no changes are found
    assert app.sync_data("", "", "") == set()


@mock.patch("app.main.AzureDevops.list_project_tfs_repos", new=mock.Mock(return_value=[]))
@mock.patch("app.main.AzureDevops.list_project_wikis")
@mock.patch("app.main.AzureDevops.list_project_repos")
@mock.patch("app.main.AzureDevops.list_projects_name")
@mock.patch("app.main.AzureDevops.__init__", return_value=None)
@mock.patch("app.main.Git.sync")
@mock.patch("app.main.Git.__init__", return_value=None)
def test__sync_data__has_changes(git_init, git_sync, devops_init, devops_list_projects_name, devops_list_project_repos, devops_list_project_wikis):
    """Check if changes are returned when they are detected"""

    devops_list_projects_name.return_value = ('Project_1', 'Project_2')
    devops_list_project_repos.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    devops_list_project_wikis.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    git_sync.return_value = True

    # Assert that changes are found
    # (2 projects x 2 gits x 2 wikis) = 8 changes in total
    assert len(app.sync_data("", "", "")) == 8


@mock.patch("app.main.AzureDevops.list_project_tfs_repos", new=mock.Mock(return_value=[]))
@mock.patch("app.main.AzureDevops.list_project_wikis")
@mock.patch("app.main.AzureDevops.list_project_repos")
@mock.patch("app.main.AzureDevops.list_projects_name")
@mock.patch("app.main.AzureDevops.__init__", return_value=None)
@mock.patch("app.main.Git.sync")
@mock.patch("app.main.Git.__init__", return_value=None)
def test__sync_data__fail(git_init, git_sync, devops_init, devops_list_projects_name, devops_list_project_repos, devops_list_project_wikis):
    """Check if exit code has changed and no changes are detected (because of fail during sync)"""

    devops_list_projects_name.return_value = ('Project_1', 'Project_2')
    devops_list_project_repos.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    devops_list_project_wikis.return_value = [{
        'name': "name_1",
        'remote_url': "remote_url_1",
        'ssh_url': "ssh_url_1"
    }, {
        'name': "name_2",
        'remote_url': "remote_url_2",
        'ssh_url': "ssh_url_2"
    }]
    git_sync.return_value = True
    git_sync.side_effect = Exception()

    # Assert that no changes are found (because all failed)
    assert app.sync_data("", "", "") == set()

    # Check if exit_code is set properly
    assert app.get_exit_code() > 0


@mock.patch("app.main.clean_archive_path")
@mock.patch("shutil.make_archive")
def test__archive_changes__no_changes(make_archive, clean_archive_path):
    """Check if archive path is purged and for each change, archive is made"""

    changes = set()
    app.archive_changes("", "", changes)

    assert clean_archive_path.call_count == 0
    assert make_archive.call_count == len(changes)


@mock.patch("shutil.make_archive")
def test__archive_changes__has_changes(make_archive):
    """Check if nothing happen because no changes"""

    changes = ("change_1", "change_2")
    app.archive_changes("", "", changes)

    assert make_archive.call_count == len(changes)


@mock.patch("app.main.clean_archive_path")
@mock.patch("app.main.get_archive_paths")
@mock.patch("app.main.SharePoint.upload_file")
@mock.patch("app.main.SharePoint.ensure_dir_exists")
@mock.patch("app.main.SharePoint.__init__", return_value=None)
def test__upload_changes_to_sharepoint__no_archives(sharepoint_init, sharepoint_ensure_dir_exists, sharepoint_upload_file, get_archive_paths, clean_archive_path):
    """Check if no archive being uploaded to sharepoint"""

    get_archive_paths.return_value = {
        "dir_paths": set(),
        "file_paths": set()
    }

    app.upload_changes_to_sharepoint("", "", "", "", "")

    assert sharepoint_ensure_dir_exists.call_count == 0
    assert sharepoint_upload_file.call_count == 0
    assert clean_archive_path.call_count == 1


@mock.patch("app.main.clean_archive_path")
@mock.patch("app.main.get_archive_paths")
@mock.patch("app.main.SharePoint.upload_file")
@mock.patch("app.main.SharePoint.ensure_dir_exists")
@mock.patch("app.main.SharePoint.__init__", return_value=None)
def test__upload_changes_to_sharepoint__has_archives(sharepoint_init, sharepoint_ensure_dir_exists, sharepoint_upload_file, get_archive_paths, clean_archive_path):
    """Check if every archive being uploaded to sharepoint"""

    get_archive_paths.return_value = {
        "dir_paths": ("dir_path_1", "dir_path_2"),
        "file_paths": ("file_path_1", "file_path_2", "file_path_3", "file_path_4", "file_path_5")
    }

    app.upload_changes_to_sharepoint("", "", "", "", "")

    assert sharepoint_ensure_dir_exists.call_count == 2
    assert sharepoint_upload_file.call_count == 5
    assert clean_archive_path.call_count == 1





# --- GitHub source -----------------------------------------------------------

def test__get_source__defaults_to_azure_devops(monkeypatch):
    monkeypatch.delenv('SOURCE', raising=False)
    assert app.get_source() == 'azure_devops'
    monkeypatch.setenv('SOURCE', ' GitHub ')
    assert app.get_source() == 'github'


def test__get_github_env_vars__success(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'tok')
    monkeypatch.setenv('PATH_CLONE', 'clone')
    monkeypatch.setenv('PATH_ARCHIVE', 'archive')
    monkeypatch.setenv('REPO_FILTER', 'ppg, ttt2 ,')
    monkeypatch.setenv('FORCE_ARCHIVE', '1')
    monkeypatch.delenv('INCLUDE_FORKS', raising=False)
    monkeypatch.delenv('GITHUB_OWNER', raising=False)
    monkeypatch.delenv('DEBUG_MODE', raising=False)
    monkeypatch.delenv('COPY_ARCHIVES_TO_SHAREPOINT_ENABLED', raising=False)

    assert app.get_github_env_vars() == ('tok', '', 'clone', 'archive', {'ppg', 'ttt2'}, True, False, '0', '0')


def test__get_github_env_vars__fail(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    monkeypatch.setenv('PATH_CLONE', 'clone')
    monkeypatch.setenv('PATH_ARCHIVE', 'archive')

    with pytest.raises(Exception, match="GITHUB_TOKEN"):
        app.get_github_env_vars()


@mock.patch("app.main.Git.sync")
@mock.patch("app.main.Git.__init__", return_value=None)
@mock.patch("app.main.GitHub.list_repos")
@mock.patch("app.main.GitHub.__init__", return_value=None)
def test__sync_github_data__filter_and_changes(github_init, list_repos, git_init, git_sync):
    """Only repos in the filter are synced; only changed ones are archived"""
    app.set_exit_code(0)
    app.GitHub.owner = "AdamDudley"
    list_repos.return_value = [
        {'name': 'ppg', 'remote_url': 'https://github.com/AdamDudley/ppg.git', 'ssh_url': ''},
        {'name': 'ttt2', 'remote_url': 'https://github.com/AdamDudley/ttt2.git', 'ssh_url': ''},
        {'name': 'other', 'remote_url': 'https://github.com/AdamDudley/other.git', 'ssh_url': ''},
    ]
    git_sync.side_effect = lambda remote, path: remote.endswith('ppg.git')

    changes = app.sync_github_data("tok", "", "/clone", repo_filter={'ppg', 'ttt2'})

    assert changes == {'github/AdamDudley/git/ppg'}
    assert git_sync.call_count == 2
    git_sync.assert_any_call('https://github.com/AdamDudley/ppg.git', '/clone/github/AdamDudley/git/ppg')
    assert app.get_exit_code() == 0


@mock.patch("app.main.Git.sync", return_value=False)
@mock.patch("app.main.Git.__init__", return_value=None)
@mock.patch("app.main.GitHub.list_repos")
@mock.patch("app.main.GitHub.__init__", return_value=None)
def test__sync_github_data__force_archive(github_init, list_repos, git_init, git_sync):
    """FORCE_ARCHIVE archives every repo even when nothing changed"""
    app.set_exit_code(0)
    app.GitHub.owner = "AdamDudley"
    list_repos.return_value = [
        {'name': 'ppg', 'remote_url': 'https://github.com/AdamDudley/ppg.git', 'ssh_url': ''},
    ]

    changes = app.sync_github_data("tok", "", "/clone", repo_filter=set(), force_archive=True)

    assert changes == {'github/AdamDudley/git/ppg'}


@mock.patch("app.main.Git.sync", return_value=True)
@mock.patch("app.main.Git.__init__", return_value=None)
@mock.patch("app.main.GitHub.list_repos")
@mock.patch("app.main.GitHub.__init__", return_value=None)
def test__sync_github_data__missing_filtered_repo_sets_exit_code(github_init, list_repos, git_init, git_sync):
    """A REPO_FILTER entry that does not exist is an error, but the rest still sync"""
    app.set_exit_code(0)
    app.GitHub.owner = "AdamDudley"
    list_repos.return_value = [
        {'name': 'ppg', 'remote_url': 'https://github.com/AdamDudley/ppg.git', 'ssh_url': ''},
    ]

    changes = app.sync_github_data("tok", "", "/clone", repo_filter={'ppg', 'does-not-exist'})

    assert changes == {'github/AdamDudley/git/ppg'}
    assert app.get_exit_code() == 1


@mock.patch("app.main.archive_changes")
@mock.patch("app.main.sync_github_data", return_value=set())
@mock.patch("app.main.get_github_env_vars", return_value=("tok", "", "clone", "archive", set(), False, False, "0", "0"))
@mock.patch("app.main.get_source", return_value="github")
def test__main__github_source(get_source, get_github_env_vars, sync_github_data, archive_changes):
    """Main routes to the GitHub sync when SOURCE=github and skips SharePoint by default"""
    app.set_exit_code(0)

    with pytest.raises(SystemExit) as e:
        app.main()

    assert e.value.code == 0
    sync_github_data.assert_called_once_with("tok", "", "clone", set(), False, False)
    archive_changes.assert_called_once_with("clone", "archive", set())


@mock.patch("app.main.get_source", return_value="bitbucket")
def test__main__unknown_source(get_source):
    with pytest.raises(Exception, match="Unknown SOURCE"):
        app.main()


@mock.patch("app.main.Git.sync", return_value=True)
@mock.patch("app.main.Git.__init__", return_value=None)
@mock.patch("app.main.GitHub.list_repos")
@mock.patch("app.main.GitHub.__init__", return_value=None)
def test__sync_github_data__skips_forks_by_default(github_init, list_repos, git_init, git_sync):
    app.set_exit_code(0)
    app.GitHub.owner = "AdamDudley"
    list_repos.return_value = [
        {'name': 'mine', 'remote_url': 'https://github.com/AdamDudley/mine.git', 'ssh_url': '', 'fork': False},
        {'name': 'theirs', 'remote_url': 'https://github.com/AdamDudley/theirs.git', 'ssh_url': '', 'fork': True},
    ]

    assert app.sync_github_data("tok", "", "/clone") == {'github/AdamDudley/git/mine'}
    assert app.sync_github_data("tok", "", "/clone", include_forks=True) == {'github/AdamDudley/git/mine', 'github/AdamDudley/git/theirs'}
