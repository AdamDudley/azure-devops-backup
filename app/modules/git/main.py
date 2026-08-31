import os
import base64
from git import Repo
from logzero import logger


class Git:
    def __init__(self, user_name: str, user_password: str) -> None:
        # Create Basic auth header
        auth_header_bytes = (f"{user_name}:{user_password}").encode("ascii")
        auth_header_base64_bytes = base64.b64encode(auth_header_bytes)
        auth_header_base64 = auth_header_base64_bytes.decode("ascii")
        self.auth_header = f"Authorization: Basic {auth_header_base64}"

    def sync(self, remote: str, path: str) -> bool:
        has_changes = False
        if os.path.isdir(path):
            has_changes = self.__update(path)
        else:
            has_changes = True
            self.__clone(remote, path)

        return has_changes

    def __auth_env(self) -> dict:
        # Supply the auth header through the environment for this one git process only.
        # (`git clone -c http.extraHeader=...` would persist the credential into the
        # mirror's config, which then ends up inside every backup archive.)
        return {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": self.auth_header,
        }

    def __clone(self, remote: str, path: str) -> None:
        Repo.clone_from(
            url=remote,
            to_path=path,
            mirror=True,
            env=self.__auth_env(),
        )

    def __update(self, path: str) -> bool:
        has_changes = False

        repo = Repo(path)
        self.__scrub_persisted_credentials(repo)

        with repo.git.custom_environment(**self.__auth_env()):
            for fetch_info in repo.remote().fetch(prune=True):
                if fetch_info.flags != fetch_info.HEAD_UPTODATE:
                    has_changes = True
                    break

        return has_changes

    @staticmethod
    def __scrub_persisted_credentials(repo: Repo) -> None:
        # Mirrors created by older versions of this tool carry the credential in their config
        with repo.config_writer() as config:
            if not config.has_section("http"):
                return
            # GitPython's parser is case-sensitive; git config keys are not
            for option in [o for o in config.options("http") if o.lower() == "extraheader"]:
                logger.warning(f"git | removing credential persisted in repo config | path: {repo.git_dir}")
                config.remove_option("http", option)
            if not [o for o in config.options("http") if o != "__name__"]:
                config.remove_section("http")
