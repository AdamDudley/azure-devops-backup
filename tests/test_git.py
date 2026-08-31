import os
import subprocess

import pytest
from git import Repo

from app.modules.git.main import Git


def _commit(repo_path, name):
    with open(os.path.join(repo_path, name), "w") as f:
        f.write(name)
    subprocess.run(["git", "-C", repo_path, "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", repo_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", name],
                   check=True, capture_output=True)


@pytest.fixture
def source_repo(tmp_path):
    path = tmp_path / "source"
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    _commit(str(path), "first")
    return path


def test__git__sync_clone_then_update(source_repo, tmp_path):
    git = Git("user", "secret-token")
    mirror = str(tmp_path / "mirror")

    # First sync clones and reports changes
    assert git.sync(str(source_repo), mirror) is True
    assert Repo(mirror).bare

    # Nothing new: no changes
    assert git.sync(str(source_repo), mirror) is False

    # New commit upstream: changes detected and mirrored
    _commit(str(source_repo), "second")
    assert git.sync(str(source_repo), mirror) is True
    assert Repo(mirror).head.commit.message.strip() == "second"


def test__git__credentials_never_persisted_in_mirror(source_repo, tmp_path):
    """The auth header must not be written into the mirror's config (it ends up in the backup zip)."""
    git = Git("user", "secret-token")
    mirror = str(tmp_path / "mirror")

    git.sync(str(source_repo), mirror)

    with open(os.path.join(mirror, "config")) as f:
        config = f.read().lower()
    assert "extraheader" not in config
    assert "secret-token" not in config


def test__git__scrubs_credentials_persisted_by_old_versions(source_repo, tmp_path):
    """Mirrors cloned by the old `clone -c http.extraHeader=...` code carry the token; update must remove it."""
    git = Git("user", "secret-token")
    mirror = str(tmp_path / "mirror")
    git.sync(str(source_repo), mirror)
    subprocess.run(["git", "-C", mirror, "config", "http.extraHeader", "Authorization: Basic leaked"], check=True)

    git.sync(str(source_repo), mirror)

    with open(os.path.join(mirror, "config")) as f:
        assert "extraheader" not in f.read().lower()
