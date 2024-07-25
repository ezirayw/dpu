
import socketio
import argparse
import sys

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Reconnect to HT_eVOLVER robotics'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-x', '--xarm', action='store_true', dest='xarm',
                        help='reconnect to xArm')
    parser.add_argument('-o', '--octoprint', action='store_true', dest='octoprint',
                        help='reconnect to OctoPrint servers')
    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    xarm = options.xarm
    octoprint = options.octoprint
    
    if evolver_ip is None:
        print('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)

    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics'])

    try:
        payload = {}
        payload['xarm'] = xarm
        payload['octoprint'] = octoprint
    
        ROBOTICS_NS.reconnect(payload)
        socketIO_Robotics.wait()

    except KeyboardInterrupt:
        print('exiting override, goodbye!')
        sys.exit()
