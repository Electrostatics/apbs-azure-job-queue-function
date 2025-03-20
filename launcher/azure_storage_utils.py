from azure.storage.blob import BlobServiceClient
import os
import logging

connection_string = os.environ["BlobStorageConnectionString"]


class AzureUtils:
    @staticmethod
    def copy_object(container_name: str, src: str, dest: str):
        src_data = AzureUtils.download_file_str(container_name, src)
        AzureUtils.put_object(container_name, dest, src_data)

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
