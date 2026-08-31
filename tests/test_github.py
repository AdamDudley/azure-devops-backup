from unittest import mock

from app.modules.github.main import GitHub


def _response(payload, status=200):
    resp = mock.Mock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _repo(name, owner="AdamDudley", fork=False):
    return {
        "name": name,
        "fork": fork,
        "owner": {"login": owner},
        "clone_url": f"https://github.com/{owner}/{name}.git",
        "ssh_url": f"git@github.com:{owner}/{name}.git",
    }


@mock.patch("app.modules.github.main.requests.Session")
def test__github__resolves_owner_from_token(session_cls):
    session = session_cls.return_value
    session.get.return_value = _response({"login": "AdamDudley"})

    gh = GitHub("token")

    assert gh.owner == "AdamDudley"
    session.get.assert_called_once_with("https://api.github.com/user")


@mock.patch("app.modules.github.main.requests.Session")
def test__github__list_repos_paginates_and_filters_owner(session_cls):
    session = session_cls.return_value
    session.get.side_effect = [
        _response([_repo("zeta"), _repo("forked-thing", owner="someone-else")]),
        _response([_repo("alpha", fork=True)]),
        _response([]),
    ]

    repos = GitHub("token", owner="AdamDudley").list_repos()

    assert [r["name"] for r in repos] == ["alpha", "zeta"]
    assert repos[0]["remote_url"] == "https://github.com/AdamDudley/alpha.git"
    assert repos[0]["fork"] is True and repos[1]["fork"] is False
    assert session.get.call_count == 3
