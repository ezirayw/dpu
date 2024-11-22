
import socketio
import argparse
import sys
import time

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip_address', action='store', dest='ip_address', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-m', '--mode', action='store', dest='mode', required=True,
                        help="Enter 'prime' to prime syringe pumps or 'pipette' for primed pipetting actions")
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    mode = options.mode
    evolver_ip = options.ip_address

    if mode not in ['prime', 'pipette']:
        parser.print_help()
        sys.exit('Invalid mode. Must be one of: prime, pipette')

    socketIO_Robotics = socketio.Client()
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics'])
    while ROBOTICS_NS.status == {}: # wait for status to be received
        time.sleep(0.1)

    if mode == 'prime':
        try:
            # check to make sure syringe pumps are not already primed
            if ROBOTICS_NS.status['prime_status']['influx'] == False:
                print("Syringe pumps confirmed not to be primed, running priming protocol")
                not_filled = True
                while not_filled:
                    fill_cycles = int(input("Enter number of pipette cycles to run: "))
                    pipette_volume = int(input("Enter volume to pipette in syringe pump steps: "))
                    print("Running {0} pipette cycles".format(fill_cycles))
                    for cycle in range(fill_cycles):
                        print(cycle)
                        ROBOTICS_NS.pipette({'base_media_0': pipette_volume})
                        while ROBOTICS_NS.running_routine == True:
                            time.sleep(0.1)

                    while True:
                        check = input("Is tubing filled with fluid? Enter y/n: ")
                        if check == 'y' or check == 'n':
                            break
                        else:
                            print("Must enter either y or n.")
                    if check == 'y':
                        not_filled = False
                    if check == 'n':
                        not_filled = True
                
                print("Tubing is filled and syringe pumps are ready to prime")
                ROBOTICS_NS.prime_influx_pumps()
                socketIO_Robotics.disconnect()
                sys.exit("Syringe pump priming protocol complete")
            else:
                socketIO_Robotics.disconnect()
                sys.exit("Syringe pumps are already primed, override status to re-run pipette protocol")
        
        except KeyboardInterrupt:
            socketIO_Robotics.disconnect()
            sys.exit('\nuser interrupt detected, exiting pipette.py')

    if mode == 'pipette':
        if ROBOTICS_NS.status['prime_status']['influx'] == True:                
            try:
                fill_cycles = input("Enter number of pipette cycles to run: ")
                fill_cycles = int(fill_cycles)
                print("Running {0} pipette cycles".format(fill_cycles))
                for cycle in range(fill_cycles):
                    print(cycle)
                    pipette_command = {'base_media_0': 300}
                    ROBOTICS_NS.pipette(pipette_command)
                    while ROBOTICS_NS.running_routine == True:
                        time.sleep(0.1)
            
            except KeyboardInterrupt:
                socketIO_Robotics.disconnect()
                sys.exit('\nuser interrupt detected, exiting pipette.py')
        else:
            socketIO_Robotics.disconnect()
            sys.exit("Syringe pumps are not primed, re-run in prime mode to execute priming protocol prior to any pipetting")

