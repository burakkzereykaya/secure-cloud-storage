from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

from app.core.config import settings

def get_blob_service_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING,
    )

def upload_encrypted_file(data:bytes, blob_path:str) -> str:
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(
        settings.AZURE_CONTAINER_NAME,
    )
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass

    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER_NAME,
        blob=blob_path,
    )

    blob_client.upload_blob(data,overwrite=True)
    return blob_path

def download_encrypted_file(blob_path:str) -> bytes:
    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER_NAME,
        blob=blob_path,
    )
    return blob_client.download_blob().readall()
