import sys
import os
import time
from numpy.matlib import astype
import socketio
import argparse
import yaml
import numpy as np
from scipy.optimize import curve_fit
from typing import TypedDict
import matplotlib.pyplot as plt
import json
import datetime
from htevolver_client import HTEvolverNamespace

DEFAULT_VIALS_TEMP = [0, 5, 8, 9, 12, 17]
DEFAULT_VIALS_OD = list(range(18))
DEFAULT_NUM_STANDARDS: int = 18
MAX_TEMP: int = 1500
MIN_TEMP: int = 2500
READ_NUM: int = 3


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
        "-c",
        "--calibration_type",
        action="store",
        required=True,
        help="Enter the type of calibration you are running, i.e. temp or density",
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


def collect_temp_data(
    htevolver_client: HTEvolverNamespace, station_list: list[int], num_standards: int, config: dict
) -> dict[int, CalibrationData]:
    # create empty data structure for storing broadcast readings, calibration data, and temperature standards
    # account for room temperture, min, and max setpoints by adding 3 array lengths
    voltage_triplet: dict[int, np.ndarray] = {}
    calibration_data: dict[int, CalibrationData] = {}
    temperature_measurements: dict[int, np.ndarray] = {}
    setpoints: dict[int, np.ndarray] = {}
    calibration_steps = (num_standards * 2) + 3
    for station in station_list:
        voltage_triplet[station] = np.zeros(3)
        temperature_measurements[station] = np.zeros(len(config["default_vials_temp"]))
        calibration_data[station] = {
            "voltage": np.zeros(calibration_steps),
            "standards": np.zeros(calibration_steps),
            "standard_deviation": np.zeros(calibration_steps),
            "coefficients": np.zeros(2),
        }
    # start with collecting room temperature
    for station in station_list:
        while True:
            proceed = input(f"Place vials filled with 6mL of water in all vial slots in Smart Station:{station}.\nPress Enter to continue.")
            if proceed == "":
                break

    while True:
        proceed = input("\nWait for 30 mins to allow for room tempterature equilibration...\nPress Enter to continue.")
        if proceed == "":
            break

    print("Room temperature reading starting, do not move vials or exit...")
    current_counter = htevolver_client.broadcast_counter
    read_num = 0
    while read_num < conf["read_num"]:
        # check to see if last stored counter matches client tracked broadcast_couter (change indicates new readings have arrived)
        if current_counter != htevolver_client.broadcast_counter:
            # add data to triplet structure and increment broadcast counter check and read number
            print(f"New broadcast detected, storing voltage values for read {read_num}")
            for station in station_list:
                voltage_triplet[station][read_num] = htevolver_client.temp_data[-1][station]["voltage"]
            current_counter += 1
            read_num += 1

    # measure and enter the temperature of 6 vials in celsius (i.e. standards)
    for station in station_list:
        temperature_input = None
        print(f"\nMeasure vial temperatures for station {station} with probe to generate temperature standards")
        for position_index, vial_position in enumerate(config["default_vials_temp"]):
            while True:
                try:
                    temperature_input = float(input(f"Enter temperature (C) value for vial slot {vial_position} in station {station}: "))
                    if temperature_input >= 0:
                        break
                except ValueError:
                    print("Input a valid float number")
            temperature_measurements[station][position_index] = temperature_input

    # triplet voltage data and temperatures for room temperature collected, now store in the calibration data structure
    room_temp_step_num = int(np.floor(calibration_steps / 2))
    for station in station_list:
        calibration_data[station]["voltage"][room_temp_step_num] = np.nanmedian(voltage_triplet[station])
        calibration_data[station]["standard_deviation"][room_temp_step_num] = np.std(voltage_triplet[station], dtype=float)
        calibration_data[station]["standards"][room_temp_step_num] = np.mean(temperature_measurements[station])

    # using the room temperature setpoint, calculate all other setpoints
    for station in station_list:
        above_rt = np.delete(
            np.round(np.linspace(config["max_temp"], calibration_data[station]["voltage"][room_temp_step_num], num_standards + 2)), -1
        )  # get rid of room_temp
        below_rt = np.round(np.linspace(calibration_data[station]["voltage"][room_temp_step_num], config["min_temp"], num_standards + 2))
        setpoints[station] = np.append(above_rt, below_rt).astype(int)
        print(f"Setpoints for station {station}: {setpoints[station]} ")

    # proceed with the rest of the setpoints below and above room temp following same
    for step_num in range(calibration_steps):
        # skip room temperature setpoint since we already have it
        if step_num == room_temp_step_num:
            continue
        print(f"\n---- Starting temperature sweep step: {step_num}/{calibration_steps - 1} ----")
        temp_commands = [0x7FFFFFFF] * 4
        for station in station_list:
            temp_commands[station] = int(setpoints[station][step_num])
        print(f"Sending setpoints: {temp_commands} to HT-eVOLVER...")
        htevolver_client.update_temp(temp_commands, immediate=True, recurring=True)

        while True:
            proceed = input("Wait for 30 mins to allow for heat equilibration...\nPress Enter to continue.")
            if proceed == "":
                break

        print("Temperature reading starting, do not move vials or exit...")
        current_counter = htevolver_client.broadcast_counter
        read_num = 0
        while read_num < conf["read_num"]:
            # check to see if last stored counter matches client tracked broadcast_couter (change indicates new readings have arrived)
            if current_counter != htevolver_client.broadcast_counter:
                # add data to triplet structure and increment broadcast counter check and read number
                print(f"New broadcast detected, storing voltage values for read {read_num}")
                for station in station_list:
                    voltage_triplet[station][read_num] = htevolver_client.temp_data[-1][station]["voltage"]
                current_counter += 1
                read_num += 1

        # measure and enter the temperature of 6 vials in celsius (i.e. standards)
        for station in station_list:
            temperature_input = None
            print(f"\nMeasure vial temperatures for station {station} with probe to generate temperature standards")
            for position_index, vial_position in enumerate(config["default_vials_temp"]):
                while True:
                    try:
                        temperature_input = float(
                            input(f"Enter temperature (C) value for vial slot {vial_position} on station {station}: ")
                        )
                        if temperature_input >= 0:
                            break
                    except ValueError:
                        print("Input a valid float number")
                temperature_measurements[station][position_index] = temperature_input

        # triplet voltage data and temperatures for setpoint collected, now store in the calibration data structure
        print(
            f"Done collecting voltage temperature data, calculating and storing median values for calibration procedure step: {step_num}/{calibration_steps - 1}"
        )
        for station in station_list:
            calibration_data[station]["voltage"][step_num] = np.nanmedian(voltage_triplet[station])
            calibration_data[station]["standard_deviation"][step_num] = np.std(voltage_triplet[station], dtype=float)
            calibration_data[station]["standards"][step_num] = np.mean(temperature_measurements[station])

    return calibration_data


def collect_od_data(
    htevolver_client: HTEvolverNamespace, vial_list: list[int], station: int, num_standards: int
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
        standards_mask.extend(padding)

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
        while read_num < conf["read_num"]:
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
        print(calibration_data[vial])
        # p0 = [62721, 62721, 0, -1]
        # maxfev=1000000000
        calibration_data[vial]["coefficients"] = curve_fit(
            htevolver_client.sigmoid, calibration_data[vial]["standards"], calibration_data[vial]["voltage"]
        )
    if graph:
        # calculate the highest value recorded during the calibration for the graph settings
        max_values = np.array([np.max(calibration_data[vial]["voltage"]) for vial in calibration_data])
        max_value = np.max(max_values)
        graph_settings = {"start": 0, "stop": max_value, "num": 500}  # [min, max, num] for np.linspace()
        graph_data("od_90", htevolver_client.sigmoid, calibration_data, graph_settings)

    return calibration_data


def linear_fit(
    htevolver_client: HTEvolverNamespace, calibration_data: dict[int, CalibrationData], graph: bool = True
) -> dict[int, CalibrationData]:
    print("\nGenerating linear fit for collected Temperature data...")
    print(calibration_data)

    for station in calibration_data:
        calibration_data[station]["coefficients"] = curve_fit(
            htevolver_client.linear, calibration_data[station]["standards"], calibration_data[station]["voltage"]
        )

    if graph:
        max_values = np.array([np.max(calibration_data[station]["voltage"]) for station in calibration_data])
        max_value = np.max(max_values)
        graph_settings = {"start": 0, "stop": max_value, "num": 500}  # [min, max, num] for np.linspace()
        graph_data("temp", htevolver_client.linear, calibration_data, graph_settings)

    return calibration_data


def graph_data(param: str, func, calibration_data: dict[int, CalibrationData], graph_settings: dict[str, int]):
    print(param)
    linear_space = np.linspace(graph_settings["start"], graph_settings["stop"], num=graph_settings["num"])
    plt.figure()
    if param == "od":
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
    if param == "temp":
        fig, ax = plt.subplots(2, 2)
        fig.suptitle("Temperature Calibration Fits for HT-eVOLVER")
        for station in calibration_data:
            plt.title(f"Smart Station:{station}")
            plt.scatter(calibration_data[station]["standards"], calibration_data[station]["voltage"], s=2, color="black")
            plt.errorbar(
                calibration_data[station]["standards"],
                calibration_data[station]["voltage"],
                xerr=calibration_data[station]["standard_deviation"],
                fmt="none",
            )
            plt.plot(linear_space, func(linear_space, *calibration_data[station]["coefficients"]), linewidth=2, color="red")
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
    if not os.path.exists(calibration_directory):
        os.makedirs(calibration_directory)
    htevolver_client = HTEvolverNamespace("/default_evolver", stations=[0], directory=calibration_directory)
    conf = {}

    if options.calibration_type not in ["temp", "temperature", "density", "od"]:
        print(f"valid calibration not entered, must be in {conf['valid_calibrations']}")
        sys.exit(2)

    socketIO_eVOLVER = socketio.Client()
    socketIO_eVOLVER.register_namespace(htevolver_client)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=["/default_evolver"])

    station_list: list[int] = []
    if options.stations != []:
        station_list = options.stations
    else:
        station_list = [0, 1, 2, 3]

    # start data collection procedure based on target calibration protocol
    collected_calibration_data = {}
    final_calibration_data = {}
    if options.calibration_type in ["temp", "temperature"]:
        collected_calibration_data = collect_temp_data(htevolver_client, station_list, int(options.standard_number), conf)
        final_calibration_data = linear_fit(htevolver_client, collected_calibration_data, False)

    if options.calibration_type in ["density", "OD", "od"]:
        for station in station_list:
            vial_list: list[int] = []
            while True:
                vials = input(
                    f"\nEnter list of vials to calibrate for station: {station} using spaces OR leave empty to use default. Press enter to continue: "
                )
                if vials == "":
                    vial_list = conf["default_vial_list"]
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
    filename = f"calibration_data_{options.calibration_type}_{timestamp}.json"

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
