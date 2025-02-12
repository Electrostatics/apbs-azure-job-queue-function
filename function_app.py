import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(
    arg_name="blob",
    path="outputs/{name}",
    connection="BlobStorageConnectionString",
    Source="EventGrid",
)
def BlobTrigger(blob: func.InputStream):
    logging.info("BlobTrigger function processed blob\n")
    logging.info(f"{blob.name}\n")
