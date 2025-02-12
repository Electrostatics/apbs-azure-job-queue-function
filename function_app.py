import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(
    arg_name="blob",
    path="inputs/{date}/{job}/{name}",
    connection="BlobStorageConnectionString",
    Source="EventGrid",
)
@app.blob_output(arg_name="outputBlob", path="outputs/{date}/{job}/{name}", connection="BlobStorageConnectionString",)
@app.blob_output(arg_name="inFile", path="outputs/{date}/{job}/{job}.in", connection="BlobStorageConnectionString")
def BlobTrigger(blob: func.InputStream, outputBlob: func.Out[str], inFile: func.Out[str]):
    logging.info("BlobTrigger function processed blob\n")
    logging.info(f"{blob.name}\n")
    outputBlob.set(blob.read().decode("utf-8"))
    inFile.set("TESTING this")
