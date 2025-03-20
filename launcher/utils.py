from dataclasses import dataclass
from typing import Optional
from io import StringIO

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
        return AzureUtils.copy_object(
            source_container_name=self.source_container,
            destination_container_name=self.dest_container,
            source_object_name=self.source_object,
            dest_object_name=self.dest_object,
            job_tag=tag,
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


def apbs_extract_input_files(job_tag, infile_text):
    # Read only the READ section of infile,
    # extracting out the files needed for APBS
    read_start = False
    read_end = False
    file_list = []
    for whole_line in StringIO(f"{infile_text}"):
        line = whole_line.strip()

        if read_start and read_end:
            break

        elif not read_start and not read_end:
            if not line.startswith("#"):
                split_line = line.split()
                if len(split_line) > 0:
                    if split_line[0].upper() == "READ":
                        # print('ENTERING READ SECTION')
                        read_start = True
                    elif split_line[0].upper() == "END":
                        # print('LEAVING READ SECTION')
                        read_end = True

        elif read_start:
            if not line.startswith("#"):
                split_line = line.split()
                if len(split_line) > 0:
                    if split_line[0].upper() == "END":
                        # print('LEAVING READ SECTION')
                        read_end = True
                    else:
                        for arg in line.split()[2:]:
                            file_list.append(arg)

    logging.debug("%s Input files: %s", job_tag, file_list)
    return file_list


def apbs_infile_creator(job_tag, apbs_options: dict) -> str:
    """
    Creates a new APBS input file, using the data from the form
    """

    # apbsOptions['tempFile'] = "apbsinput.in"
    apbsinput_io = StringIO()

    # writing READ section to file
    apbsinput_io.write("read\n")
    apbsinput_io.write(
        f"\t{apbs_options['readType']} "
        f"{apbs_options['readFormat']} "
        f"{apbs_options['pqrPath']}{apbs_options['pqrFileName']}\n"
    )
    apbsinput_io.write("end\n")

    # writing ELEC section to file
    apbsinput_io.write("elec\n")
    apbsinput_io.write(f"\t{apbs_options['calcType']}\n")
    if apbs_options["calcType"] != "fe-manual":
        apbsinput_io.write(
            f"\tdime {apbs_options['dimeNX']} "
            f"{apbs_options['dimeNY']} {apbs_options['dimeNZ']}\n"
        )
    if apbs_options["calcType"] == "mg-para":
        apbsinput_io.write(
            f"\tpdime {apbs_options['pdimeNX']} "
            f"{apbs_options['pdimeNY']} {apbs_options['pdimeNZ']}\n"
        )
        apbsinput_io.write(f"\tofrac {apbs_options['ofrac']}\n")
        if apbs_options["asyncflag"]:
            apbsinput_io.write(f"\tasync {apbs_options['async']}\n")

    if apbs_options["calcType"] == "mg-manual":
        apbsinput_io.write(
            f"\tglen {apbs_options['glenX']} "
            f"{apbs_options['glenY']} {apbs_options['glenZ']}\n"
        )
    if apbs_options["calcType"] in ["mg-auto", "mg-para", "mg-dummy"]:
        apbsinput_io.write(
            f"\tcglen {apbs_options['cglenX']} "
            f"{apbs_options['cglenY']} {apbs_options['cglenZ']}\n"
        )
    if apbs_options["calcType"] in ["mg-auto", "mg-para"]:
        apbsinput_io.write(
            f"\tfglen {apbs_options['fglenX']} "
            f"{apbs_options['fglenY']} {apbs_options['fglenZ']}\n"
        )

        if apbs_options["coarseGridCenterMethod"] == "molecule":
            apbsinput_io.write(
                f"\tcgcent mol {apbs_options['coarseGridCenterMoleculeID']}\n"
            )
        elif apbs_options["coarseGridCenterMethod"] == "coordinate":
            apbsinput_io.write(
                f"\tcgcent {apbs_options['cgxCent']} "
                f"{apbs_options['cgyCent']} {apbs_options['cgzCent']}\n"
            )

        if apbs_options["fineGridCenterMethod"] == "molecule":
            apbsinput_io.write(
                f"\tfgcent mol {apbs_options['fineGridCenterMoleculeID']}\n"
            )
        elif apbs_options["fineGridCenterMethod"] == "coordinate":
            apbsinput_io.write(
                f"\tfgcent {apbs_options['fgxCent']} "
                f"{apbs_options['fgyCent']} {apbs_options['fgzCent']}\n"
            )

    if apbs_options["calcType"] in ["mg-manual", "mg-dummy"]:
        if apbs_options["gridCenterMethod"] == "molecule":
            apbsinput_io.write(f"\tgcent mol {apbs_options['gridCenterMoleculeID']}\n")
        elif apbs_options["gridCenterMethod"] == "coordinate":
            apbsinput_io.write(
                f"\tgcent {apbs_options['gxCent']} "
                f"{apbs_options['gyCent']} {apbs_options['gzCent']}\n"
            )

    for i in range(3):
        charge_key: str = f"charge{i}"
        concentration_key: str = f"conc{i}"
        radius_key: str = f"radius{i}"
        if (
            (charge_key in apbs_options)
            and (concentration_key in apbs_options)
            and (radius_key in apbs_options)
        ):
            apbsinput_io.write(
                f"\tion charge {apbs_options[charge_key]} conc {apbs_options[concentration_key]} radius {apbs_options[radius_key]}\n"
            )

    apbsinput_io.write(f"\tmol {apbs_options['mol']}\n")
    apbsinput_io.write(f"\t{apbs_options['solveType']}\n")
    apbsinput_io.write(f"\tbcfl {apbs_options['boundaryConditions']}\n")
    apbsinput_io.write(f"\tpdie {apbs_options['biomolecularDielectricConstant']}\n")
    apbsinput_io.write(f"\tsdie {apbs_options['dielectricSolventConstant']}\n")
    apbsinput_io.write(f"\tsrfm {apbs_options['dielectricIonAccessibilityModel']}\n")
    apbsinput_io.write(f"\tchgm {apbs_options['biomolecularPointChargeMapMethod']}\n")
    apbsinput_io.write(f"\tsdens {apbs_options['surfaceConstructionResolution']}\n")
    apbsinput_io.write(f"\tsrad {apbs_options['solventRadius']}\n")
    apbsinput_io.write(f"\tswin {apbs_options['surfaceDefSupportSize']}\n")
    apbsinput_io.write(f"\ttemp {apbs_options['temperature']}\n")
    apbsinput_io.write(f"\tcalcenergy {apbs_options['calcEnergy']}\n")
    apbsinput_io.write(f"\tcalcforce {apbs_options['calcForce']}\n")
    for idx in range(3):
        ch_str = f"charge{idx}"
        conc_str = f"conc{idx}"
        rad_str = f"radius{idx}"
        if (
            ("chStr" in apbs_options)
            and ("concStr" in apbs_options)
            and ("radStr" in apbs_options)
        ):
            # ion charge {charge} conc {conc} radius {radius}
            apbsinput_io.write(
                f"\tion charge {apbs_options[ch_str]} "
                f"conc {apbs_options[conc_str]} "
                f"radius {apbs_options[rad_str]}\n"
            )

    if apbs_options["writeCharge"]:
        apbsinput_io.write(
            f"\twrite charge {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-charge\n"
        )

    if apbs_options["writePot"]:
        apbsinput_io.write(
            f"\twrite pot {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-pot\n"
        )

    if apbs_options["writeSmol"]:
        apbsinput_io.write(
            f"\twrite smol {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-smol\n"
        )

    if apbs_options["writeSspl"]:
        apbsinput_io.write(
            f"\twrite sspl {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-sspl\n"
        )

    if apbs_options["writeVdw"]:
        apbsinput_io.write(
            f"\twrite vdw {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-vdw\n"
        )

    if apbs_options["writeIvdw"]:
        apbsinput_io.write(
            f"\twrite ivdw {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-ivdw\n"
        )

    if apbs_options["writeLap"]:
        apbsinput_io.write(
            f"\twrite lap {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-lap\n"
        )

    if apbs_options["writeEdens"]:
        apbsinput_io.write(
            f"\twrite edens {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-edens\n"
        )

    if apbs_options["writeNdens"]:
        apbsinput_io.write(
            f"\twrite ndens {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-ndens\n"
        )

    if apbs_options["writeQdens"]:
        apbsinput_io.write(
            f"\twrite qdens {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-qdens\n"
        )

    if apbs_options["writeDielx"]:
        apbsinput_io.write(
            f"\twrite dielx {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-dielx\n"
        )

    if apbs_options["writeDiely"]:
        apbsinput_io.write(
            f"\twrite diely {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-diely\n"
        )

    if apbs_options["writeDielz"]:
        apbsinput_io.write(
            f"\twrite dielz {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-dielz\n"
        )

    if apbs_options["writeKappa"]:
        apbsinput_io.write(
            f"\twrite kappa {apbs_options['writeFormat']} "
            f"{apbs_options['writeStem']}-kappa\n"
        )

    apbsinput_io.write("end\n")
    apbsinput_io.write("quit")

    # input.close()
    apbsinput_io.seek(0)

    # Return contents of updated input file
    logging.debug("%s Created APBS Input file", job_tag)
    return apbsinput_io.read()
