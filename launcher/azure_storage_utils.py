from azure.storage.blob import BlobServiceClient
import os
import logging

connection_string = os.environ["BlobStorageConnectionString"]


class AzureUtils:
    @staticmethod
    def copy_object(container_name: str, src: str, dest: str):
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        # Download the src info
        src_blob_client = storage_client.get_blob_client(container_name, src)
        src_info = src_blob_client.download_blob().readall().decode("utf-8")

        # Upload the src info to the dest
        dest_blob_client = storage_client.get_blob_client(container_name, dest)
        out = dest_blob_client.upload_blob(src_info, overwrite=True)
        logging.info(f"Output: {out}")

    @staticmethod
    def download_file_str(bucket_name: str, object_name: str) -> str:
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(bucket_name, object_name)
        return blob_client.download_blob().readall().decode("utf-8")

    @staticmethod
    def put_object(container_name: str, object_name: str, body):
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(container_name, object_name)
        blob_client.upload_blob(body, overwrite=True)
        logging.info(f"Output: {blob_client}")

    @staticmethod
    def object_exists(bucket_name: str, object_name: str) -> bool:
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = storage_client.get_blob_client(bucket_name, object_name)
        try:
            blob_client.get_blob_properties()
            return True
        except:
            return False
