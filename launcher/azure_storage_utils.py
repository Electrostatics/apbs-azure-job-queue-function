from azure.storage.blob import BlobServiceClient
import os
import logging

connection_string = os.environ["BlobStorageConnectionString"]


class AzureUtils:
    @staticmethod
    def copy_object(
        source_container_name,
        destination_container_name,
        source_object_name,
        dest_object_name,
        job_tag: str = "",
    ):
        storage_client = BlobServiceClient.from_connection_string(connection_string)
        source_path = source_object_name
        logging.info(f"Source path: {source_path}")
        dest_path = dest_object_name
        if job_tag != "":
            source_path = f"{job_tag}/{source_path}"
            logging.info(f"Source path: {source_path}")
            dest_path = f"{job_tag}/{dest_path}"
        logging.info(
            f"{job_tag}: Copying object from {source_container_name}/{source_path} to {destination_container_name}/{dest_path}"
        )
        source_client = storage_client.get_blob_client(
            source_container_name, source_path
        )
        dest_client = storage_client.get_blob_client(
            destination_container_name, dest_path
        )
        source_blob = source_client.download_blob().readall()
        out = dest_client.upload_blob(source_blob, overwrite=True)
        # NOTE: For some reason the below failed with a 401 error
        # The client could not write to the input container
        # out = dest_client.start_copy_from_url(source_client.url, requires_sync=True)
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
