
import socketio
import argparse
import sys
import time

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-m', '--mode', action='store', dest='mode',
                    help="enter 'prime' to prime efflux ipps or 'pump' to run use efflux ipps")
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    mode = options.mode

    socketIO_Robotics = socketio.Client()
    ROBOTICS_NS = RoboticsNamespace('/robotics_evolver')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format('192.168.1.15', 8080), namespaces=['/robotics_evolver'])
    while ROBOTICS_NS.status == {}: # wait for status to be received
        time.sleep(0.1)

    if mode == 'prime':
        # check to make sure syringe pumps are not already primed
        if ROBOTICS_NS.status['prime_status']['efflux'] == False:
            ipp_efflux_command = {}
            try:
                while True:
                    quad = input("Enter quad to prime IPP efflux: ")
                    quads = []
                    quads.append('quad_{0}'.format(quad))
                    print('Running efflux IPPs in reverse according to default config to prime efflux IPPs')
                    ROBOTICS_NS.prime_efflux_pumps()
            
            except KeyboardInterrupt:
                socketIO_Robotics.disconnect()
                sys.exit('\nuser interrupt detected, exiting pipette.py')

    if mode == 'ipp':
        if ROBOTICS_NS.status['prime_status']['efflux'] == True:
            ipp_efflux_command = {}
            try:
                while True:
                    quad = input("Enter quad to run IPP efflux: ")
                    duration = int(input("Enter IPP pump time (seconds): "))
                    frequency = int(input("Enter IPP actuation frequency: "))
                    polarity = int(input("Enter IPP actuation polarity (0 or 1): "))
                    
                    quad_name = 'quad_' + quad
                    ipp_efflux_command[quad_name] = {'frequency': frequency, 'duration': duration, 'polarity': polarity}

                    print('Running IPP efflux on quad {0} for {1} seconds at {2} Hz in {3} direction'.format(quad, duration, frequency))
                    ROBOTICS_NS.efflux_ipp(ipp_efflux_command)
            
            except KeyboardInterrupt:
                socketIO_Robotics.disconnect()
                sys.exit('\nUser interrupt detected, exiting pipette.py')