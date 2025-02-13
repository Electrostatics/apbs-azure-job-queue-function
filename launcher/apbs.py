"""A class to interpret/prepare an APBS job submission for job queue."""

from io import StringIO
from locale import atof, atoi
from os.path import splitext
import logging

# from .s3_utils import S3Utils
from .azure_storage_utils import AzureUtils as S3Utils

from .jobsetup import JobSetup, MissingFilesError
from .utils import (
    apbs_extract_input_files,
    apbs_infile_creator,
)


class APBSRunner(JobSetup):
    def __init__(self, form: dict, job_id: str, job_date: str):
        super().__init__(job_id, job_date)
        self.form = None
        self.infile_name = None
        self.command_line_args = None
        self.infile_support_filenames = []
        self.estimated_max_runtime = 7200

        if "filename" in form:
            self.infile_name = form["filename"]
            self.infile_support_filenames = form["support_files"]

        elif form is not None:
            if "output_scalar" in form:
                # Unravels output parameters from form
                for option in form["output_scalar"]:
                    form[option] = option
                form.pop("output_scalar")

            for key, value in form.items():
                if not isinstance(value, str):
                    # TODO: 2021/03/03, Elvis - Eliminate need to cast all
                    #   items as string (see 'self.fieldStorageToDict()')
                    form[key] = str(value)

            self.form = form
            self.apbs_options = self.field_storage_to_dict(form)
            # TODO: catch error if something wrong happens
            #   in fieldStorageToDict handle in tesk_proxy_service

    def prepare_job(self, output_bucket_name: str, input_bucket_name: str) -> str:
        """Setup the APBS job to run."""
        # taken from mainInput()
        infile_name = self.infile_name
        form = self.form
        job_id = self.job_id
        job_date = self.job_date
        job_tag = f"{job_date}/{job_id}"

        # downloading necessary files
        if infile_name is not None:
            # If APBS directly run, verify necessary files exist in S3
            infile_object_name = f"{job_date}/{job_id}/{infile_name}"

            # Check S3 for .in file existence; add to missing list if not
            self.add_input_file(infile_name)
            if not S3Utils.object_exists(input_bucket_name, infile_object_name):
                logging.error(
                    "%s Missing APBS input file '%s'",
                    job_tag,
                    infile_name,
                )
                self.add_missing_file(infile_name)

            # Get list of expected supporting files
            expected_files_list = self.infile_support_filenames

            # Check if additional expected files exist in S3
            for name in expected_files_list:
                object_name = f"{job_tag}/{name}"
                self.add_input_file(str(name))
                if not S3Utils.object_exists(input_bucket_name, object_name):
                    logging.error(
                        "%s Missing APBS input file '%s'",
                        job_tag,
                        name,
                    )
                    self.add_missing_file(str(name))

            # Set and return command line args
            self.command_line_args = infile_name

            if len(self._missing_files) > 0:
                raise MissingFilesError(
                    f"File(s) specified  missing from storage: {self._missing_files}",
                    self._missing_files,
                )

            return self.command_line_args

        elif form is not None:
            # Using APBS input file name from PDB2PQR run
            infile_name = f"{job_id}.in"

            apbs_options = self.apbs_options

            # Get text for infile string
            infile_str = S3Utils.download_file_str(
                output_bucket_name, f"{job_tag}/{infile_name}"
            )

            # Extracts PQR file name from the '*.in' file within storage bucket
            pqr_file_name = apbs_extract_input_files(job_tag, infile_str)[0]
            apbs_options["pqrFileName"] = pqr_file_name

            # Get contents of updated APBS input file, based on form
            apbs_options["tempFile"] = "apbsinput.in"
            new_infile_contents = apbs_infile_creator(job_tag, apbs_options)

            # Get contents of PQR file from PDB2PQR run
            pqrfile_text = S3Utils.download_file_str(
                output_bucket_name, f"{job_tag}/{pqr_file_name}"
            )

            # Remove waters from molecule (PQR file) if requested by the user
            try:
                if "removewater" in form and form["removewater"] == "on":
                    pqr_filename_root, pqr_filename_ext = splitext(pqr_file_name)

                    water_pqrname = f"{pqr_filename_root}-water{pqr_filename_ext}"

                    # Add lines to new PQR text, skipping lines with water
                    nowater_pqrfile_text = "".join(
                        line
                        for line in StringIO(pqrfile_text)
                        if "WAT" not in line and "HOH" not in line
                    )

                    # Send original PQR file (with water) to S3 output bucket
                    S3Utils.put_object(
                        output_bucket_name,
                        f"{job_tag}/{water_pqrname}",
                        pqrfile_text.encode("utf-8"),
                    )
                    self.add_output_file(f"{job_id}/{water_pqrname}")

                    # Replace PQR file text with version with water removed
                    pqrfile_text = nowater_pqrfile_text

            except Exception as err:
                logging.exception(
                    "%s Failed to remove water molecules: %s",
                    self.job_tag,
                    err,
                )
                raise

            # Upload *.pqr and *.in file to input bucket
            logging.debug(
                "%s Write file to S3: %s",
                job_tag,
                f"{job_tag}/{apbs_options['tempFile']}",
            )
            S3Utils.put_object(
                input_bucket_name,
                f"{job_tag}/{apbs_options['tempFile']}",
                new_infile_contents.encode("utf-8"),
            )
            logging.debug(
                "%s Write file to S3: %s",
                job_tag,
                f"{job_tag}/{pqr_file_name}",
            )
            S3Utils.put_object(
                input_bucket_name,
                f"{job_tag}/{pqr_file_name}",
                pqrfile_text.encode("utf-8"),
            )

            # Set input files for status reporting
            self.add_input_file(pqr_file_name)
            self.add_input_file(apbs_options["tempFile"])

            # Return command line args
            self.command_line_args = apbs_options["tempFile"]  # 'apbsinput.in'
            return self.command_line_args

    def field_storage_to_dict(self, form: dict) -> dict:
        """Converts the CGI input from the web interface to a dictionary"""
        apbs_options = {"writeCheck": 0, "writeCharge": False}

        if "writecharge" in form and form["writecharge"] != "":
            apbs_options["writeCheck"] += 1
            apbs_options["writeCharge"] = True

        apbs_options["writePot"] = False
        if "writepot" in form and form["writepot"] != "":
            apbs_options["writeCheck"] += 1
            apbs_options["writePot"] = True

        apbs_options["writeSmol"] = False
        if "writesmol" in form and form["writesmol"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeSmol"] = True

        apbs_options["asyncflag"] = False
        if "asyncflag" in form and form["asyncflag"] == "on":
            apbs_options["async"] = atoi(form["async"])
            apbs_options["asyncflag"] = True

        apbs_options["writeSspl"] = False
        if "writesspl" in form and form["writesspl"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeSspl"] = True

        apbs_options["writeVdw"] = False
        if "writevdw" in form and form["writevdw"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeVdw"] = True

        apbs_options["writeIvdw"] = False
        if "writeivdw" in form and form["writeivdw"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeIvdw"] = True

        apbs_options["writeLap"] = False
        if "writelap" in form and form["writelap"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeLap"] = True

        apbs_options["writeEdens"] = False
        if "writeedens" in form and form["writeedens"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeEdens"] = True

        apbs_options["writeNdens"] = False
        if "writendens" in form and form["writendens"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeNdens"] = True

        apbs_options["writeQdens"] = False
        if "writeqdens" in form and form["writeqdens"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeQdens"] = True

        apbs_options["writeDielx"] = False
        if "writedielx" in form and form["writedielx"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeDielx"] = True

        apbs_options["writeDiely"] = False
        if "writediely" in form and form["writediely"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeDiely"] = True

        apbs_options["writeDielz"] = False
        if "writedielz" in form and form["writedielz"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeDielz"] = True

        apbs_options["writeKappa"] = False
        if "writekappa" in form and form["writekappa"] == "on":
            apbs_options["writeCheck"] += 1
            apbs_options["writeKappa"] = True

        if apbs_options["writeCheck"] > 4:
            # TODO: 2021/03/02, Elvis - validation error;
            #       please raise exception here
            logging.error(
                "%s Please select a maximum of four write statements.",
                self.job_tag,
            )

        # READ section variables
        apbs_options["readType"] = "mol"
        apbs_options["readFormat"] = "pqr"
        apbs_options["pqrPath"] = ""
        # apbsOptions['pqrFileName'] = form['pdb2pqrid']+'.pqr'

        # ELEC section variables
        apbs_options["calcType"] = form["type"]

        apbs_options["ofrac"] = atof(form["ofrac"])

        apbs_options["dimeNX"] = atoi(form["dimenx"])
        apbs_options["dimeNY"] = atoi(form["dimeny"])
        apbs_options["dimeNZ"] = atoi(form["dimenz"])

        apbs_options["cglenX"] = atof(form["cglenx"])
        apbs_options["cglenY"] = atof(form["cgleny"])
        apbs_options["cglenZ"] = atof(form["cglenz"])

        apbs_options["fglenX"] = atof(form["fglenx"])
        apbs_options["fglenY"] = atof(form["fgleny"])
        apbs_options["fglenZ"] = atof(form["fglenz"])

        apbs_options["glenX"] = atof(form["glenx"])
        apbs_options["glenY"] = atof(form["gleny"])
        apbs_options["glenZ"] = atof(form["glenz"])

        apbs_options["pdimeNX"] = atof(form["pdimex"])
        apbs_options["pdimeNY"] = atof(form["pdimey"])
        apbs_options["pdimeNZ"] = atof(form["pdimez"])

        if form["cgcent"] == "mol":
            apbs_options["coarseGridCenterMethod"] = "molecule"
            apbs_options["coarseGridCenterMoleculeID"] = atoi(form["cgcentid"])
        elif form["cgcent"] == "coord":
            apbs_options["coarseGridCenterMethod"] = "coordinate"
            apbs_options["cgxCent"] = atoi(form["cgxcent"])
            apbs_options["cgyCent"] = atoi(form["cgycent"])
            apbs_options["cgzCent"] = atoi(form["cgzcent"])

        if form["fgcent"] == "mol":
            apbs_options["fineGridCenterMethod"] = "molecule"
            apbs_options["fineGridCenterMoleculeID"] = atoi(form["fgcentid"])
        elif form["fgcent"] == "coord":
            apbs_options["fineGridCenterMethod"] = "coordinate"
            apbs_options["fgxCent"] = atoi(form["fgxcent"])
            apbs_options["fgyCent"] = atoi(form["fgycent"])
            apbs_options["fgzCent"] = atoi(form["fgzcent"])

        # added conditional to avoid checking 'gcent' for incompatible methods
        if apbs_options["calcType"] in ["mg-manual", "mg-dummy"]:
            if form["gcent"] == "mol":
                apbs_options["gridCenterMethod"] = "molecule"
                apbs_options["gridCenterMoleculeID"] = atoi(form["gcentid"])
            elif form["gcent"] == "coord":
                apbs_options["gridCenterMethod"] = "coordinate"
                apbs_options["gxCent"] = atoi(form["gxcent"])
                apbs_options["gyCent"] = atoi(form["gycent"])
                apbs_options["gzCent"] = atoi(form["gzcent"])

        for i in range(3):
            charge_key: str = f"charge{i}"
            concentration_key: str = f"conc{i}"
            radius_key: str = f"radius{i}"
            if form[charge_key] and form[concentration_key] and form[radius_key]:
                apbs_options[charge_key] = atof(form[charge_key])
                apbs_options[concentration_key] = atof(form[concentration_key])
                apbs_options[radius_key] = atof(form[radius_key])

        apbs_options["mol"] = atoi(form["mol"])
        apbs_options["solveType"] = form["solvetype"]
        apbs_options["boundaryConditions"] = form["bcfl"]
        apbs_options["biomolecularDielectricConstant"] = atof(form["pdie"])
        apbs_options["dielectricSolventConstant"] = atof(form["sdie"])
        apbs_options["dielectricIonAccessibilityModel"] = form["srfm"]
        apbs_options["biomolecularPointChargeMapMethod"] = form["chgm"]
        apbs_options["surfaceConstructionResolution"] = atof(form["sdens"])
        apbs_options["solventRadius"] = atof(form["srad"])
        apbs_options["surfaceDefSupportSize"] = atof(form["swin"])
        apbs_options["temperature"] = atof(form["temp"])
        apbs_options["calcEnergy"] = form["calcenergy"]
        apbs_options["calcForce"] = form["calcforce"]

        for idx in range(3):
            ch_str = f"charge{idx}"
            conc_str = f"conc{idx}"
            rad_str = f"radius{idx}"
            if form[ch_str] != "":
                apbs_options[ch_str] = atoi(form[ch_str])
            if form[conc_str] != "":
                apbs_options[conc_str] = atof(form[conc_str])
            if form[rad_str] != "":
                apbs_options[rad_str] = atof(form[rad_str])
        apbs_options["writeFormat"] = form["writeformat"]
        # apbsOptions['writeStem'] = apbsOptions['pqrFileName'][:-4]
        apbs_options["writeStem"] = form["pdb2pqrid"]

        logging.debug("%s Setting APBS Options: %s", self.job_tag, apbs_options)
        return apbs_options
