import azure.functions as func
import azurefunctions.extensions.bindings.blob as blob
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(
    arg_name="client",
    path="inputs/{date}/{job}/{jobtype}-job.json",
    connection="BlobStorageConnectionString",
    Source="EventGrid",
)
def BlobTrigger(client: blob.BlobClient):
    sdk = client.get_sdk_type()
    if sdk:
        logging.info(f"{sdk.get_blob_properties()}")
# @app.blob_output(arg_name="inFile", path="outputs/{date}/{job}/{job}.in", connection="BlobStorageConnectionString")
# @app.blob_output(arg_name="metrics", path="outputs/{date}/{job}/{jobtype}-metrics.json", connection="BlobStorageConnectionString")
# def BlobTrigger(blob: func.InputStream, outputBlob: func.Out[str], inFile: func.Out[str], metrics: func.Out[str]):
#     logging.info(f"{blob.name}\n")
#     inFile.set("TESTING this")
#     metrics.set("Metrics")
