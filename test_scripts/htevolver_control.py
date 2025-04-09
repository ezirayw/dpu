import socketio
import sys
import argparse
from evolver_functions import EvolverNamespace

EVOLVER_NS = None


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


def handle_stir(evolver_ns: EvolverNamespace):
    target_quads = input("Enter target Smart Quads (0-3), separated by spaces: ")
    quad_indices = [int(quad) for quad in target_quads.split(" ")]
    print(quad_indices)
    stir_commands = [0] * 4

    for quad in quad_indices:
        stir_command = None
        while True:
            stir_command = int(input("Enter stir command (0-100) for Smart Quad {0}: ".format(quad)))
            if stir_command < 0 or stir_command > 300:
                print("Invalid stir command, must be between 0 and 100")
            else:
                stir_commands[int(quad)] = stir_command
                break
    evolver_ns.update_stir(stir_commands, recurring=True, immediate=True)


def handle_led(evolver_ns: EvolverNamespace):
    target_quads = input("Enter target Smart Quads (0-3), separated by spaces: ")
    quad_indices = [int(quad) for quad in target_quads.split(" ")]
    print(quad_indices)
    commands = {"left": [0] * 8, "right": [0] * 8}

    for quad in quad_indices:
        led_command = None
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart Quad {quad}, vial set (0,1,2,8): "))
            if led_command != 0 and led_command != 4095:
                print("Invalid led command for vial set (0,1,2,8), must be 4095 or 0")
            else:
                commands["left"][int(quad)] = led_command
                break
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart Quad {quad}, vial set (6,7,12,13,14): "))
            if led_command != 0 and led_command != 4095:
                print("Invalid led command for vial set (6,7,12,13,14), must be 4095 or 0")
            else:
                commands["left"][int(quad) + 1] = led_command
                break
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart Quad {quad}, vial set (3,4,5,11): "))
            if led_command != 0 and led_command != 4095:
                print("Invalid led command for vial set (3,4,5,11), must be 4095 or 0")
            else:
                commands["right"][int(quad)] = led_command
                break
        while True:
            led_command = int(input(f"Enter led command (4095 or 0) for Smart Quad {quad}, vial set (9,10,15,16,17): "))
            if led_command != 0 and led_command != 4095:
                print("Invalid led command for vial set (9,10,15,16,17), must be 4095 or 0")
            else:
                commands["right"][int(quad) + 1] = led_command
                break
    evolver_ns.update_led(commands, recurring=True, immediate=True)


def handle_temp(evolver_ns: EvolverNamespace):
    target_quads = input("Enter target Smart Quads (0-3), separated by spaces: ")
    quad_indices = [int(quad) for quad in target_quads.split(" ")]
    print(quad_indices)
    temp_commands = [0x7FFFFFFF, 0x7FFFFFFF, 0x7FFFFFFF, 0x7FFFFFFF]

    for quad in quad_indices:
        temp_command = None
        while True:
            temp_command = int(input("Enter temp command (1300 - 2500) for Smart Quad {0}: ".format(quad)))
            if temp_command < 1500 or temp_command > 2500:
                print("Invalid temp command, must be between 1300 and 2500")
            else:
                temp_commands[quad] = temp_command
                break
    evolver_ns.update_temp(temp_commands, recurring=True, immediate=True)


if __name__ == "__main__":
    options, parser = get_options()
    evolver_ip = options.ip_address

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace("/default_evolver")
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=["/default_evolver"])

    try:
        while True:
            command_type = input("Enter eVOLVER parameter to configure (temp, stir, led): ")
            if command_type not in ["temp", "stir", "led"]:
                print("Invalid parameter entered, try again")
            else:
                if command_type == "temp":
                    while True:
                        handle_temp(EVOLVER_NS)
                        response = input("Type 'return' to control another parameter or press enter to send a new temp command: ")
                        if response == "return":
                            break
                if command_type == "stir":
                    while True:
                        handle_stir(EVOLVER_NS)
                        response = input("Type 'return' to control another parameter or press enter to send a new stir command: ")
                        if response == "return":
                            break
                if command_type == "led":
                    while True:
                        handle_led(EVOLVER_NS)
                        response = input("Type 'return' to control another parameter or press enter to send a new LED command: ")
                        if response == "return":
                            break

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit("\nUser interrupt detected, exiting program")
