import argparse
import os

import numpy as np

from interfaces.calibration_interface import CalibrationData, GraphSettings, graph_data, load_data
from interfaces.htevolver_interface import HTEvolverNamespace


def get_options():
    description = "Run an eVOLVER experiment from the command line"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "-f",
        "--calibration_file",
        action="store",
        required=True,
        help="Enter the absolute path of the calibration json data",
    )

    parser.add_argument(
        "-q",
        "--stations",
        action="store",
        nargs="*",
        type=lambda s: int(s),
        required=False,
        help="List of Smart Stations to iterate calibration protocol over (space separated), defaults to all if left blank",
    )

    return parser.parse_args(), parser


if __name__ == "__main__":
    options, parser = get_options()

    # Create a minimal HTEvolverNamespace object just for the linear function
    htevolver_client = HTEvolverNamespace("/default_evolver", stations=[0], connect=False)
    data_filepath = os.path.abspath(options.calibration_file)
    calibration_data = load_data(data_filepath)
    calibration_type = ""

    print(calibration_data)

    max_values = []
    for key, value in calibration_data.items():
        # Convert string keys back to integers
        station = int(key)
        # encountered vial data

        if isinstance(value, dict):
            calibration_type = "od"
            for vial_key, vial_data in value.items():
                # For nested dictionaries (in case of OD data)
                vial = int(vial_key)
                max_values.append(np.max(vial_data.standards))

        # encountered temp data
        if isinstance(value, CalibrationData):
            calibration_type = "temp"
            max_values.append(np.max(value.standards))
    max_value = np.max(max_values)

    # graph the calibration curves
    if calibration_type == "temp":
        graph_settings = GraphSettings(param="Temperature", units="Celsius", row=2, column=2, stop=max_value)
        graph_data(htevolver_client.linear, calibration_data, graph_settings)
    if calibration_type == "od":
        for station in calibration_data:
            graph_settings = GraphSettings(param="OD", units="OD600", row=3, column=6, stop=max_value)
            graph_data(htevolver_client.sigmoid, calibration_data[station], graph_settings)
