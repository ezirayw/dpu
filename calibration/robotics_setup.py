
import socketio
import argparse
import sys
# tell interpreter where to look

sys.path.insert(0,"../experiment/template")
# import all classes
from robotic_functions import RoboticsNamespace
from robotic_functions import PUMP_SETTINGS_PATH
from custom_script import ROBOTICS_PORT

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')
    return parser.parse_args(), parser



if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    if evolver_ip is None:
        print('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)

    socketIO_Robotics = socketio.Client()
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, ROBOTICS_PORT), namespaces=['/robotics'])

    try:
        check_fill_tubing = input("Is the tubing filled with desired fluid? Enter y/n: ")
        if check_fill_tubing == 'y':
            check_pump_calibration = input("Is the pump calibrated? Enter y/n: ")
            if check_pump_calibration == 'y':
                print("Robotic arm ready to handle eVOLVER fluidic functions")

        if check_fill_tubing == 'n':
            not_filled = True
            while not_filled:
                fill_cycles = input("Enter number of fill cycles to run: ")
                fill_cycles = int(fill_cycles)
                print("Running {0} number of fill tubing cycles".format(fill_cycles))
                for cycle in range(fill_cycles):
                    print(cycle)
                    ROBOTICS_NS.fill_tubing()
                while True:
                    re_check = input("Is tubing filled with fluid? Enter y/n: ")
                    if re_check == 'y' or re_check == 'n':
                        break
                    else:
                        print("Must enter either y or n.")
                        pass
                if re_check == 'y':
                    not_filled = False
                if re_check == 'n':
                    not_filled = True
            print("Tubing is filled and ready to prime")
            print("Priming pump. Important to prevent flyover events across vials")
            ROBOTICS_NS.prime_pumps()

    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_Robotics.disconnect()
        sys.exit(1)
