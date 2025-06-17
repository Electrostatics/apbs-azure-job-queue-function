import azure.functions as func
from azure.identity import ManagedIdentityCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
import logging
import json
from time import time
import os

from launcher.azure_storage_utils import AzureUtils
from launcher.jobsetup import MissingFilesError
from launcher.pdb2pqr import PDB2PQRRunner
from launcher.apbs import APBSRunner

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def upload_status_file(filename: str, inital_status: dict):
    AzureUtils.put_object("outputs", filename, json.dumps(inital_status))


def get_job_info(tag: str, container: str, object_name: str) -> dict:
    return AzureUtils.get_azure_object_json(tag, container, object_name)


def build_status_dict(
    job_id: str,
    job_tag: str,
    job_type: str,
    status: str,
    inputfile_list: list,
    outputfile_list: list,
    message: str = "",
) -> dict:
    """Build a dictionary for the initial status

    :param job_id str: Identifier string for specific job
    :param job_type str: Name of job type (e.g. 'apbs', 'pdb2pqr')
    :param status str: A string indicating initial status of job
    :param inputfile_list list: List of current input files
    :param outputfile_list list: List of current output files
    :param message: Optional message to add to status
    :type message: optional

    :return: a JSON-compatible dictionary containing initial status
             info of the job
    :rtype: dict
    """

    # TODO: 2021/03/02, Elvis - add submission time to initial status
    # TODO: 2021/03/25, Elvis - Reconstruct format of status since
    #                           they're constructed on a per-job basis

    initial_status_dict = {
        "jobid": job_id,
        "jobtype": job_type,
        job_type: {
            "status": status,
            "startTime": time(),
            "endTime": None,
            "subtasks": [],
            "inputFiles": inputfile_list,
            "outputFiles": outputfile_list,
        },
        "metadata": {"versions": {}},
    }

    # if message is not None:
    if status == "invalid":
        initial_status_dict[job_type]["message"] = message
        initial_status_dict[job_type]["startTime"] = None
        initial_status_dict[job_type]["subtasks"] = None
        initial_status_dict[job_type]["inputFiles"] = None
        initial_status_dict[job_type]["outputFiles"] = None

    logging.info(f"{job_tag} Initial Status: {initial_status_dict}")
    return initial_status_dict


def start_container_job():
    logging.info("In start container job")
    client_id = os.getenv("CONTAINER_APP_CLIENT_ID")
    if client_id is None:
        logging.error("No client ID found for Managed Identity")
        return
    subscription_id = os.getenv("SUBSCRIPTION_ID")
    if subscription_id is None:
        logging.error("No subscription ID found for Managed Identity")
        return

    resource_group_name = os.getenv("RESOURCE_GROUP_NAME")
    if resource_group_name is None:
        logging.error("No resource group name found for Managed Identity")
        return
    job_name = os.getenv("JOB_NAME")
    if job_name is None:
        logging.error("No job name found for Managed Identity")
        return
    logging.info("Starting poll")
    try:
        credential = ManagedIdentityCredential(client_id=client_id)
        logging.info("Successful credential call")

        client = ContainerAppsAPIClient(credential, subscription_id)
        logging.info("Client created")

        logging.info("Checking job status")
        job_info = client.jobs.get(
            resource_group_name=resource_group_name, job_name=job_name
        )
        logging.info(f"Current info: {job_info}")

        poller = client.jobs.begin_start(
            resource_group_name=resource_group_name, job_name=job_name
        )
        logging.info("Poller created")
        logging.info(f"Poller status: {poller.status()}")
        logging.info("Waiting for job start")
        result = poller.result(timeout=150)
        logging.info(f"Job start status: {result}")
    except Exception as err:
        logging.error(f"Error starting container job: {type(err).__name__}: {err}")
        return


@app.blob_trigger(
    arg_name="client",
    path="inputs/{date}/{job}/{jobtype}-job.json",
    connection="BlobStorageConnectionString",
    Source="EventGrid",
)
@app.queue_output(
    arg_name="msg",
    queue_name="apbsbackendqueue",
    connection="OutputQueue",
)
def BlobTrigger(client: func.InputStream, msg: func.Out[str]):
    name = client.name
    if not name:
        logging.error("No name found for blob")
        return
    cleaned = name.replace("inputs/", "")
    split = name.split("/")
    job_id, file_name = split[-2:]
    date = split[-3]

    tag = f"{date}/{job_id}"
    type = split[-1].split("-")[0]

    logging.info(f"Job ID: {job_id}")
    logging.info(f"Date: {date}")
    logging.info(f"File Name: {file_name}")

    input_files = []
    output_files = []
    job_runner = None
    message = ""
    status = "pending"
    timeout_seconds = 0
    form = get_job_info(tag, "inputs", cleaned)["form"]
    if type == "pdb2pqr":
        logging.info("Running PDB2PQR job")
        # logging.info(f"Form: {form}")
        # AzureUtils.put_object("outputs", "form-test.json", json.dumps(form))
        # logging.info(f"Copying {cleaned} to outputs")
        # AzureUtils.copy_object("inputs", "outputs", file_name, file_name, tag)
        job_runner = PDB2PQRRunner(form, job_id, date)
        job_command_line_args = job_runner.prepare_job()
    elif type == "apbs":
        logging.info("Running APBS job")
        job_runner = APBSRunner(form, job_id, date)
        try:
            job_command_line_args = job_runner.prepare_job("outputs", "inputs")
        except MissingFilesError as err:
            logging.error(f"{tag} Error preparing APBS job: {err}")
            status = "failed"
            message = f"Files specified byut not found: {err.missing_files}"
    else:
        status = "invalid"
        message = "Invalid job type"
        logging.error(f"{tag} Invalid job type: {type}")

    if type in ("apbs", "pdb2pqr"):
        if job_runner is None:
            logging.error(f"{tag} Job runner is None")
            return
        input_files: list[str] = job_runner.input_files
        output_files: list[str] = job_runner.output_files
        timeout_seconds: int = job_runner.estimated_max_runtime
    status_filename = f"{type}-status.json"
    status_object = f"{tag}/{status_filename}"
    initial_status: dict = build_status_dict(
        job_id, tag, type, status, input_files, output_files, message
    )
    logging.info(f"Uploading {tag}/{status_filename} to outputs: {initial_status}")
    upload_status_file(status_object, initial_status)
    if status not in ("invalid", "failed"):
        if timeout_seconds == 0:
            timeout_seconds = 2000
        queue_message = {
            "job_date": date,
            "job_id": job_id,
            "job_tag": tag,
            "job_type": type,
            # TODO: change this to container
            "bucket_name": "inputs",
            "input_files": input_files,
            "command_line_args": job_command_line_args,
            "max_run_time": timeout_seconds,
        }
        logging.info(f"Queue Message: {queue_message}")
        msg.set(json.dumps(queue_message))
        logging.info("Message sent to queue")
        logging.info("Starting container job")
        start_container_job()
        logging.info("Container job started")
