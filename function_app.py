import azure.functions as func
import azurefunctions.extensions.bindings.blob as blob
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(
    arg_name="client", path="outputs/{name}", connection="BlobStorageConnectionString"
)
def BlobTrigger(client: blob.BlobClient):
    sdk = client.get_sdk_type()
    if sdk is None:
        logging.error("Blob SDK is None")
    else:
        logging.info("Processing\n")
        logging.info(f"Propertes: {sdk.get_blob_properties()}\n")
