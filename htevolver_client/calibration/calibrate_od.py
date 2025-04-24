import argparse
import datetime
import json
import logging
import os
import sys
from typing import TypedDict

import matplotlib.pyplot as plt
import numpy as np
import socketio
from interfaces.htevolver_interface import HTEvolverNamespace

# from .htevolver_client import HTEvolverNamespace
from scipy.optimize import curve_fit

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s\n",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    filename="./logs/htevolver_calibrate.log",
)


DEFAULT_VIALS_OD = list(range(18))
DEFAULT_NUM_STANDARDS: int = 18
READ_NUM: int = 3
STANDARD_NUM_MIN: int = 3


class CalibrationData(TypedDict):
    voltage: np.ndarray
    standards: np.ndarray
    coefficients: np.ndarray
    standard_deviation: np.ndarray


def get_options():
    description = "Run an eVOLVER experiment from the command line"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "-i",
        "--ip_address",
        action="store",
        required=True,
        help="IP address of eVOLVER to run experiment on.",
    )

    parser.add_argument(
        "-s",
        "--standard_number",
        action="store",
        required=True,
        help="Number of standards to use, defaults to using 18",
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


def collect_od_data(
    htevolver_interface: HTEvolverNamespace, vial_list: list[int], station: int, num_standards: int
) -> dict[int, CalibrationData]:
    vial_list.sort()  # sort the vial_list prior to begining any processing

    # create empty data structure for storing a 3-element list per each vial and storing calibration data
    voltage_triplet: dict[int, np.ndarray] = {}
    calibration_data: dict[int, CalibrationData] = {}
    for vial in vial_list:
        voltage_triplet[vial] = np.zeros(3)
        calibration_data[vial] = {
            "voltage": np.zeros(num_standards),
            "standards": np.zeros(num_standards),
            "standard_deviation": np.zeros(num_standards),
            "coefficients": np.zeros(4),
        }

    # create emtpy data structure to store standards
    standards = np.zeros(num_standards)
    standards_mask = list(range(num_standards))

    # pad out standards mask to match length of vial_list
    if num_standards != len(vial_list):
        # padding = np.full(len(vial_list) - num_standards, np.nan)
        padding = [float("nan")] * (len(vial_list) - num_standards)
        standards_mask.extend(padding)  # ignore pyright here

    # get standards from user
    print("\nEnsure that standards are prepared before continuing")
    for index in range(len(standards)):
        standard_input = None
        while True:
            try:
                standard_input = float(input(f"Enter OD value for standard_{index}: "))
                if standard_input >= 0:
                    break
            except ValueError:
                print("Input a valid float number")
        standards[index] = standard_input

    # store standards in calibration data structure
    for vial in calibration_data:
        calibration_data[vial]["standards"] = standards

    while True:
        proceed = input(
            f"\nPlace standards in Smart Station vial slots in ascending order according to vial list entered. \nExample, standard_0: {standards[0]} OD600 in vial_slot: {min(vial_list)} & standard_{len(standards) - 1}: {standards[-1]} OD600 in vial_slot: {max(standards_mask)}. \nPress Enter to start procedure: "
        )
        if proceed == "":
            break

    # enter for loop which will collect 3 broadcast readings, store the median value, and instruct the user to rearrange standards
    # number of steps in the procedure is deteremined by the number of desired vial_positions to calibrate
    for step_num in range(len(vial_list)):
        print(f"\n---- Starting calibration procedure step: {step_num}/{len(vial_list) - 1} ----")
        current_counter = htevolver_client.broadcast_counter
        read_num = 0
        print("Readings starting, do not move vials or exit...")
        while read_num < READ_NUM:
            # check to see if last stored counter matches client tracked broadcast_couter (change indicates new readings have arrived)
            if current_counter != htevolver_client.broadcast_counter:
                # add data to triplet structure and increment broadcast counter check and read number
                print(f"New broadcast detected, storing voltage values for read {read_num}")
                for vial in voltage_triplet:
                    # voltage_triplet[vial][read_num] = htevolver_client.od_data[-1][od_key][od_index]
                    voltage_triplet[vial][read_num] = htevolver_client.od_data[-1][station][vial]["voltage"]
                current_counter += 1
                read_num += 1

        # all triplet data is collected, now store the median in the calibration data structure as the representative voltage value
        for vial in calibration_data:
            # check if a standard is in the vial position before storing
            if not np.isnan(standards_mask[vial]):
                data_index = standards_mask[vial]
                calibration_data[vial]["voltage"][data_index] = np.nanmedian(voltage_triplet[vial])
                calibration_data[vial]["standard_deviation"][data_index] = np.std(voltage_triplet[vial], dtype=float)

        # instruct user to rearrange vials and continue to next step in the procedure
        print(
            f"Done collecting voltage photodiode data, calculating and storing median values for calibration procedure step: {step_num}/{len(vial_list) - 1}"
        )
        while True:
            proceed = input(
                "Rearrange standards by moving up one position and snaking highest standard index to lowest vial position. Press Enter when done: "
            )
            if proceed == "":
                break

        print(f"\nCurrent state of standards mask: {standards_mask}")
        print("Current state of calibration_data structure")
        for vial in calibration_data:
            print(calibration_data[vial])
        # adjust standards_mask for next step
        standards_mask.insert(0, standards_mask.pop())
    return calibration_data


def sigmoid_fit(
    htevolver_client: HTEvolverNamespace, calibration_data: dict[int, CalibrationData], graph: bool = True
) -> dict[int, CalibrationData]:
    print("\nGenerating sigmoid fit for collected OD data...")
    for vial in calibration_data:
        # p0 = [62721, 62721, 0, -1]
        # maxfev=1000000000
        print(calibration_data[vial]["voltage"])
        coefficients, cov = curve_fit(
            htevolver_client.sigmoid, calibration_data[vial]["standards"], calibration_data[vial]["voltage"], maxfev=1000000000
        )
        calibration_data[vial]["coefficients"] = coefficients
    if graph:
        # calculate the highest value recorded during the calibration for the graph settings
        max_values = np.array([np.max(calibration_data[vial]["voltage"]) for vial in calibration_data])
        max_value = np.max(max_values)
        graph_settings = {"start": 0, "stop": max_value, "num": 500}  # [min, max, num] for np.linspace()
        graph_data(htevolver_client.sigmoid, calibration_data, graph_settings)

    return calibration_data


def graph_data(func, calibration_data: dict[int, CalibrationData], graph_settings: dict[str, int]):
    linear_space = np.linspace(graph_settings["start"], graph_settings["stop"], num=graph_settings["num"])
    plt.figure()
    fig, ax = plt.subplots(3, 6)
    fig.suptitle(f"OD600 Calibration Fits for HT-eVOLVER Smart Station:{0}")
    for vial in calibration_data:
        ax[vial].set_title(f"Vial:{vial}")
        ax[vial].scatter(calibration_data[vial]["standards"], calibration_data[vial]["voltage"], s=2, color="black")
        ax[vial].errorbar(
            calibration_data[vial]["standards"],
            calibration_data[vial]["voltage"],
            xerr=calibration_data[vial]["standard_deviation"],
            fmt="none",
        )
        ax[vial].plot(linear_space, func(linear_space, *calibration_data[vial]["coefficients"]), linewidth=2, color="red")
        ax[vial].ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    plt.show()


# Convert numpy arrays to lists for JSON serialization
def prepare_for_serialization(data):
    if isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, dict):
        return {k: prepare_for_serialization(v) for k, v in data.items()}
    elif isinstance(data, list) or isinstance(data, tuple):
        return [prepare_for_serialization(item) for item in data]
    else:
        return data


def load_calibration_data(filename: str) -> dict[int, CalibrationData]:
    """
    Load calibration data from a JSON file.

    Args:
        filename (str): Path to the JSON file containing calibration data

    Returns:
        dict[int, CalibrationData]: Dictionary of calibration data indexed by station/vial
    """
    try:
        with open(filename, "r") as f:
            serialized_data = json.load(f)

        # Convert data back to numpy arrays
        calibration_data = {}
        for key, value in serialized_data.items():
            # Convert string keys back to integers
            station = int(key)
            calibration_data[station] = {}

            if isinstance(value, dict):
                for station_key, station_data in value.items():
                    # For nested dictionaries (in case of OD data)
                    vial = int(station_key)
                    calibration_data[station][vial] = {
                        "voltage": np.array(station_data["voltage"]),
                        "standards": np.array(station_data["standards"]),
                        "standard_deviation": np.array(station_data["standard_deviation"]),
                        "coefficients": np.array(station_data["coefficients"]),
                    }
            else:
                # For direct station data (in case of temp data)
                calibration_data[station] = {
                    "voltage": np.array(value["voltage"]),
                    "standards": np.array(value["standards"]),
                    "standard_deviation": np.array(value["standard_deviation"]),
                    "coefficients": np.array(value["coefficients"]),
                }

        return calibration_data
    except Exception as e:
        print(f"Error loading calibration data: {e}")
        return {}


if __name__ == "__main__":
    options, parser = get_options()
    evolver_ip = options.ip_address
    current_directory = os.getcwd()
    calibration_directory = os.path.join(current_directory, "calibration_data")

    if int(options.standard_number) >= STANDARD_NUM_MIN:
        print(f"more standards are needed, must be at least {STANDARD_NUM_MIN}")
        sys.exit(2)

    if not os.path.exists(calibration_directory):
        os.makedirs(calibration_directory)

    station_list: list[int] = []
    if options.stations != []:
        station_list = options.stations
    else:
        station_list = [0, 1, 2, 3]

    htevolver_client = HTEvolverNamespace("/default_evolver", stations=station_list, directory=calibration_directory, supress_save=True)
    socketIO_eVOLVER = socketio.Client()
    socketIO_eVOLVER.register_namespace(htevolver_client)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=["/default_evolver"])

    # start data collection procedure based on target calibration protocol
    collected_calibration_data = {}
    final_calibration_data = {}

    for station in station_list:
        vial_list: list[int] = []
        while True:
            vials = input(
                f"\nEnter list of vials to calibrate for station: {station} using spaces OR leave empty to use default. Press enter to continue: "
            )
            if vials == "":
                vial_list = DEFAULT_VIALS_OD
                break
            else:
                try:
                    vial_list = [int(vial) for vial in vials.split(" ")]
                    vial_list.sort()
                    break
                except ValueError:
                    print("Invalid list, try again")
        print(vial_list)
        collected_calibration_data = collect_od_data(htevolver_client, vial_list, station, int(options.standard_number))
        final_calibration_data[station] = sigmoid_fit(htevolver_client, collected_calibration_data, True)

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(htevolver_client.directory, f"calibration_data_{options.calibration_type}_{timestamp}.json")

    # Convert data to serializable format
    serializable_data = prepare_for_serialization(final_calibration_data)

    # Write to file
    try:
        with open(filename, "w") as f:
            json.dump(serializable_data, f, indent=4)
    except TypeError as e:
        print(f"Error serializing data: {e}")
        # Handle any remaining serialization issues
        with open(filename, "w") as f:
            serializable_data_str = str(serializable_data)
            f.write(serializable_data_str)
    print(f"Calibration data saved to {filename}")
