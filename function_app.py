import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(
    arg_name="blob",
    path="inputs/{date}/{job}/{jobtype}-job.json",
    connection="BlobStorageConnectionString",
    Source="EventGrid",
)
@app.blob_output(arg_name="inFile", path="outputs/{date}/{job}/{job}.in", connection="BlobStorageConnectionString")
@app.blob_output(arg_name="metrics", path="outputs/{date}/{job}/{jobtype}-metrics.json", connection="BlobStorageConnectionString")
def BlobTrigger(blob: func.InputStream, outputBlob: func.Out[str], inFile: func.Out[str], metrics: func.Out[str]):
    logging.info(f"{blob.name}\n")
    inFile.set("TESTING this")
    metrics.set("Metrics")
