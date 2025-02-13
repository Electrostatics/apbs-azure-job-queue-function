from dataclasses import dataclass
from typing import Optional

from .azure_storage_utils import AzureUtils
import logging
from re import split


@dataclass
class AzureCopyObject:
    source_object: str
    dest_object: str
    source_container: str = "inputs"
    dest_container: Optional[str] = None

    def __post_init__(self):
        if self.dest_container is None:
            self.dest_container = self.source_container

    def copy_object(self, tag: str):
        AzureUtils.copy_object(
            tag,
            self.source_container,
            self.dest_container,
            self.source_object,
            self.dest_object,
        )


def sanitize_file_name(job_tag: str, file_name: str):
    """Make sure that a file name does not have any special characters in it.

    Args:
        file_name (str): A file path the may include special characters.

    Returns:
        str: the filename without any spaces
    """
    # TODO: 2020/06/30, Elvis - log that sanitization is happening if
    #                           pattern is seen
    orig_name = file_name
    file_name = split(r"[/\\]", file_name)[-1]
    file_name = file_name.replace(" ", "_")
    # fileName = fileName.replace('-', '_')
    if orig_name != file_name:
        logging.warning(
            "%s Sanitized filename from '%s' to '%s'",
            job_tag,
            orig_name,
            file_name,
        )
    return file_name
