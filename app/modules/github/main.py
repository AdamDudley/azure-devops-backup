import requests


class GitHub:
    """Minimal GitHub REST client: lists repos the token owner has access to."""

    API_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str = "") -> None:
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self.owner = owner or self.__authenticated_user()

    def __authenticated_user(self) -> str:
        response = self.session.get(f"{self.API_URL}/user")
        response.raise_for_status()
        return response.json()["login"]

    def list_repos(self) -> list:
        """Return repos owned by `owner` (private included when the token allows) as
        [{'name': ..., 'remote_url': ...}], sorted by name."""
        result = list()
        page = 1
        while True:
            response = self.session.get(
                f"{self.API_URL}/user/repos",
                params={"affiliation": "owner", "per_page": 100, "page": page},
            )
            response.raise_for_status()
            repos = response.json()
            if not repos:
                break
            for repo in repos:
                if repo["owner"]["login"].lower() != self.owner.lower():
                    continue
                result.append({
                    "name": repo["name"],
                    "remote_url": repo["clone_url"],
                    "ssh_url": repo["ssh_url"],
                    "fork": bool(repo.get("fork", False)),
                })
            page += 1

        return sorted(result, key=lambda r: r["name"].lower())
