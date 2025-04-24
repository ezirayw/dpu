import argparse
import datetime
import json
import logging
import os
import sys

import numpy as np
import socketio
from scipy.optimize import curve_fit

from htevolver_client.interfaces.calibration_interface import CalibrationData, GraphSettings, graph_data, serialize_data
from htevolver_client.interfaces.htevolver_interface import HTEvolverNamespace

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s\n",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    filename="./logs/htevolver_calibrate.log",
)


DEFAULT_VIALS_TEMP = [0, 5, 8, 9, 12, 17]
MAX_TEMP: int = 1500
MIN_TEMP: int = 2500
READ_NUM: int = 3
STANDARD_NUM_MIN: int = 2


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


def collect_temp_data(htevolver_client: HTEvolverNamespace, station_list: list[int], num_standards: int) -> dict[int, CalibrationData]:
    # create empty data structure for storing broadcast readings, calibration data, and temperature standards
    # account for room temperture, min, and max setpoints by adding 3 array lengths
    voltage_triplet: dict[int, np.ndarray] = {}
    calibration_data: dict[int, CalibrationData] = {}
    temperature_measurements: dict[int, np.ndarray] = {}
    setpoints: dict[int, np.ndarray] = {}
    calibration_steps = (num_standards * 2) + 3
    for station in station_list:
        voltage_triplet[station] = np.zeros(3)
        temperature_measurements[station] = np.zeros(len(DEFAULT_VIALS_TEMP))
        calibration_data[station] = CalibrationData(
            voltage=np.zeros(calibration_steps),
            standards=np.zeros(calibration_steps),
            standard_deviation=np.zeros(calibration_steps),
            coefficients=np.zeros(2),
        )
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
    while read_num < READ_NUM:
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
        for position_index, vial_position in enumerate(DEFAULT_VIALS_TEMP):
            while True:
                try:
                    temperature_input = float(input(f"Enter temperature (C) value for vial slot {vial_position} in station {station}: "))
                    if temperature_input >= 0:
                        validation = input(
                            f"Entered value is {temperature_input}. Press enter to commit this value or type 'return' to re-enter a temperature."
                        )
                        if validation == "":
                            break
                        else:
                            continue
                except ValueError:
                    print("Input a valid float number")
            temperature_measurements[station][position_index] = temperature_input

    # triplet voltage data and temperatures for room temperature collected, now store in the calibration data structure
    room_temp_step_num = int(np.floor(calibration_steps / 2))
    for station in station_list:
        calibration_data[station].voltage[room_temp_step_num] = np.nanmedian(voltage_triplet[station])
        calibration_data[station].standard_deviation[room_temp_step_num] = np.std(voltage_triplet[station], dtype=float)
        calibration_data[station].standards[room_temp_step_num] = np.mean(temperature_measurements[station])

    # using the room temperature setpoint, calculate all other setpoints
    for station in station_list:
        above_rt = np.delete(
            np.round(np.linspace(MAX_TEMP, calibration_data[station].voltage[room_temp_step_num], num_standards + 2)), -1
        )  # get rid of room_temp
        below_rt = np.round(np.linspace(calibration_data[station].voltage[room_temp_step_num], MIN_TEMP, num_standards + 2))
        setpoints[station] = np.append(above_rt, below_rt).astype(int)
        print(f"Setpoints for station {station}: {setpoints[station]} ")

    # proceed with the rest of the setpoints below and above room temp following same
    for step_num in range(calibration_steps):
        # skip room temperature setpoint since we already have it
        if step_num == room_temp_step_num:
            continue
        print(f"\n---- Starting temperature sweep step: {step_num}/{calibration_steps - 1} ----")
        temp_commands = [0] * 4
        for station in station_list:
            temp_commands[station] = int(setpoints[station][step_num])
        print(f"Sending setpoints: {temp_commands} to HT-eVOLVER...")
        htevolver_client.update_parameter("temp", temp_commands, immediate=True, recurring=True)

        while True:
            proceed = input("Wait for 30 mins to allow for heat equilibration...\nPress Enter to continue.")
            if proceed == "":
                break

        print("Temperature reading starting, do not move vials or exit...")
        current_counter = htevolver_client.broadcast_counter
        read_num = 0
        while read_num < READ_NUM:
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
            for position_index, vial_position in enumerate(DEFAULT_VIALS_TEMP):
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
            calibration_data[station].voltage[step_num] = np.nanmedian(voltage_triplet[station])
            calibration_data[station].standard_deviation[step_num] = np.std(voltage_triplet[station], dtype=float)
            calibration_data[station].standards[step_num] = np.mean(temperature_measurements[station])

    return calibration_data


def linear_fit(
    htevolver_client: HTEvolverNamespace, calibration_data: dict[int, CalibrationData], graph: bool = True
) -> dict[int, CalibrationData]:
    print("\nGenerating linear fit for collected Temperature data...")

    for station in calibration_data:
        coefficients, cov = curve_fit(htevolver_client.linear, calibration_data[station].standards, calibration_data[station].voltage)
        calibration_data[station].coefficients = coefficients
    if graph:
        max_values = np.array([np.max(calibration_data[station].voltage) for station in calibration_data])
        max_value = np.max(max_values)
        graph_settings = GraphSettings(param="Temperature", units="celsius", row=2, column=2, stop=max_value)
        graph_data(htevolver_client.linear, calibration_data, graph_settings)

    return calibration_data


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

    htevolver_client = HTEvolverNamespace("/default_evolver", stations=station_list, directory=calibration_directory, connect=True)
    socketIO_eVOLVER = socketio.Client()
    socketIO_eVOLVER.register_namespace(htevolver_client)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=["/default_evolver"])

    # start data collection procedure based on target calibration protocol
    collected_calibration_data = collect_temp_data(htevolver_client, station_list, int(options.standard_number))
    final_calibration_data = linear_fit(htevolver_client, collected_calibration_data, False)

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(htevolver_client.directory, f"calibration_data_{options.calibration_type}_{timestamp}.json")

    # Convert data to serializable format
    serializable_data = serialize_data(final_calibration_data)

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
