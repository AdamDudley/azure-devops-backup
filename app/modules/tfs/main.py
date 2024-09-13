import os
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_0.tfvc.models import TfvcVersionDescriptor, TfvcItemRequestData


class Tfs:
    def __init__(self, organization_url: str, personal_access_token: str) -> None:
        credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        self.tfvc_client = self.connection.clients.get_tfvc_client()

    def sync(self, project: str, path: str) -> bool:
        has_changes = False
        if os.path.isdir(path):
            has_changes = self.__update(project, path)
        else:
            has_changes = True
            self.__clone(project, path)
        return has_changes

    def __clone(self, project: str, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        zip_content = self.__download_repo_zip(project)
        with open(path, 'wb') as zip_file:
            zip_file.write(zip_content)

    def __update(self, project: str, path: str) -> bool:
        self.__clone(project, path)
        return True

    def __download_repo_zip(self, project: str) -> bytes:
        item_request_data = {
            "scopePath": "$/",
            "recursionLevel": "Full",
            "includeContentMetadata": True,
            "latestProcessedChange": True,
            "versionDescriptor": {
                "versionType": "Latest"
            }
        }

        try:
            response = self.tfvc_client.get_items_batch_zip(item_request_data=item_request_data, project=project)
            return response
        except Exception as e:
            raise ValueError(f"Error downloading repo zip: {str(e)}")

    def download_repo_zip(self, project: str, zip_path: str) -> None:
        item_request_data = TfvcItemRequestData(
            include_content_metadata=True,
            include_links=True,
            item_descriptors=[
                {
                    "path": f"$/{project}",  # Use the project name in the path
                    "recursionLevel": "Full"
                }
            ]
        )

        try:
            response = self.tfvc_client.get_items_batch_zip(item_request_data=item_request_data, project=project)
            
            # Save the zip file
            with open(zip_path, 'wb') as zip_file:
                for chunk in response:
                    zip_file.write(chunk)
            
            print(f"Repository zip file for project '{project}' downloaded successfully to {zip_path}")
        except Exception as e:
            raise ValueError(f"Error downloading repo zip for project '{project}': {str(e)}")

