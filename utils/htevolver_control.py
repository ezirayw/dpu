import argparse
import logging
import sys

import socketio

from htevolver_client.interfaces.htevolver_interface import HTEvolverNamespace

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s\n",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    filename="./logs/htevolver_control.log",
)


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

    return parser.parse_args(), parser


def handle_stir(htevolver_client: HTEvolverNamespace, station_list: list[int]):
    stir_commands = [0] * 4
    for station in station_list:
        while True:
            stir_command = int(input("Enter stir command (0-100) for Smart station {0}: ".format(station)))
            if stir_command >= 0 and stir_command <= 300:
                stir_commands[int(station)] = stir_command
                break
            else:
                print("Invalid stir command, must be between 0 and 100")
    htevolver_client.update_parameter("stir", stir_commands, recurring=True, immediate=True)


def handle_led(htevolver_client: HTEvolverNamespace, station_list: list[int]):
    commands = {"left": [0] * 8, "right": [0] * 8}
    for station in station_list:
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart station {station}, vial set (0,1,2,8): "))
            if led_command == 0 or led_command == 4095:
                commands["left"][int(station)] = led_command
                break
            else:
                print("Invalid led command for vial set (0,1,2,8), must be 4095 or 0")
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart station {station}, vial set (6,7,12,13,14): "))
            if led_command == 0 or led_command == 4095:
                commands["left"][int(station) + 1] = led_command
                break
            else:
                print("Invalid led command for vial set (6,7,12,13,14), must be 4095 or 0")
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart station {station}, vial set (3,4,5,11): "))
            if led_command == 0 or led_command == 4095:
                commands["right"][int(station)] = led_command
                break
            else:
                print("Invalid led command for vial set (3,4,5,11), must be 4095 or 0")
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart station {station}, vial set (9,10,15,16,17): "))
            if led_command == 0 or led_command == 4095:
                commands["right"][int(station) + 1] = led_command
                break
            else:
                print("Invalid led command for vial set (9,10,15,16,17), must be 4095 or 0")
    htevolver_client.update_parameter("od_led_left", commands["left"], recurring=True, immediate=True)
    htevolver_client.update_parameter("od_led_right", commands["right"], recurring=True, immediate=True)


def handle_temp(htevolver_client: HTEvolverNamespace, station_list: list[int]):
    temp_commands = [0, 0, 0, 0]
    for station in station_list:
        while True:
            temp_command = int(input("Enter temp command (1300 - 2500 or 0 for OFF) for Smart station {0}: ".format(station)))
            if (temp_command >= 1500 and temp_command <= 2500) or (temp_command == 0):
                temp_commands[station] = temp_command
                break
            else:
                print("Invalid temp command, must be between 1300 and 2500 or 0")
    htevolver_client.update_parameter("temp", temp_commands, recurring=True, immediate=True)


def handle_temp_config(htevolver_client: HTEvolverNamespace, station_list: list[int]):
    config_commands = [0, 0, 0, 0]
    for station in station_list:
        while True:
            try:
                config_command = int(input("Enter temp config command (i.e. room temperature) for Smart station {0}: ".format(station)))
                if (config_command >= 2000 and config_command <= 2200) or (config_command == 0):
                    config_commands[station] = config_command
                    break
                else:
                    print("Invalid room temperature command, should be between 2000 and 2200")
            except ValueError:
                print("Value entered could not be converted into an integer, try again. ")
    htevolver_client.update_parameter("temp_config", config_commands, recurring=True, immediate=True)


if __name__ == "__main__":
    options, parser = get_options()
    evolver_ip = options.ip_address

    socketIO_eVOLVER = socketio.Client()
    htevolver_client = HTEvolverNamespace("/default_evolver", connect=True)
    socketIO_eVOLVER.register_namespace(htevolver_client)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=["/default_evolver"])

    try:
        while True:
            parameter = input("Enter eVOLVER parameter to configure (temp, stir, led, temp_config): ")
            if parameter in ["temp", "stir", "led", "temp_config"]:
                station_list = []
                while True:
                    stations = input("Enter target Smart stations (0-3), separated by spaces: ")
                    station_list = []
                    try:
                        station_list = [int(station) for station in stations.split(" ")]
                        break
                    except ValueError:
                        print("retry entering station list")

                while True:
                    if parameter == "temp":
                        handle_temp(htevolver_client, station_list)
                    if parameter == "stir":
                        handle_stir(htevolver_client, station_list)
                    if parameter == "led":
                        handle_led(htevolver_client, station_list)
                    if parameter == "temp_config":
                        handle_temp_config(htevolver_client, station_list)

                    response = input(f"Type 'return' to control another parameter or press Enter to send another {parameter} command: ")
                    if response == "return":
                        break

            else:
                print("Invalid parameter entered, try again")

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit("\nUser interrupt detected, exiting program")
