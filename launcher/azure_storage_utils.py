import logging
import os
import json
from typing import Optional

from azure.storage.blob import BlobServiceClient


class AzureUtils:
    _connection_string: Optional[str] = None

    # This enables us to cache the connection string when we need it rather than failing on import
    @classmethod
    def _get_connection_string(cls) -> str:
        if cls._connection_string is None:
            cls._connection_string = os.environ.get("BlobStorageConnectionString")
        if not cls._connection_string:
            raise ValueError("Missing BlobStorageConnectionString environment variable")
        return cls._connection_string

    @staticmethod
    def copy_object(container_name: str, src: str, dest: str):
        src_data = AzureUtils.download_file_str(container_name, src)
        AzureUtils.put_object(container_name, dest, src_data)

    @classmethod
    def download_file_str(cls, bucket_name: str, object_name: str) -> str:
        connection_string = cls._get_connection_string()
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(bucket_name, object_name)
        return blob_client.download_blob().readall().decode("utf-8")

    @classmethod
    def put_object(cls, container_name: str, object_name: str, body):
        connection_string = cls._get_connection_string()
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(container_name, object_name)
        blob_client.upload_blob(body, overwrite=True)
        logging.info(f"Output: {blob_client}")

    @classmethod
    def object_exists(cls, bucket_name: str, object_name: str) -> bool:
        connection_string = cls._get_connection_string()
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(bucket_name, object_name)
        try:
            blob_client.get_blob_properties()
            return True
        except:
            return False

    @classmethod
    def get_azure_object_json(cls, tag: str, container: str, object_name: str) -> dict:
        resp = {}
        connection_string = cls._get_connection_string()
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(container, object_name)
        out = blob_client.download_blob().readall().decode("utf-8")
        try:
            resp = json.loads(out)
            logging.info(f"{tag}: Found JSON object data: {resp}")
        except Exception as err:
            logging.error(f"{tag}: Error parsing JSON object data: {err}")
        return resp
