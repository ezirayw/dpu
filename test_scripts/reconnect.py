
import socketio
import argparse
import sys

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Reconnect to HT_eVOLVER robotics'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-x', '--xArm', action='store_true', dest='xarm',
                        help='reconnect to xArm')
    parser.add_argument('-o', '--octoprint', action='store_true',
                        help='reconnect to OctoPrint servers')
    parser.add_argument('-i', '--ip-address', action='store', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    xarm = options.xarm
    octoprint = options.octoprint

    if not xarm and not octoprint:
        parser.print_help()
        sys.exit('Neither xArm nor OctoPrint selected for reconnection so therefore exiting reconnect.py')

    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics_evolver')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics_evolver'])

    try:
        payload = {}
        payload['xArm'] = xarm
        payload['OctoPrint'] = octoprint
    
        ROBOTICS_NS.reconnect(payload)
        socketIO_Robotics.wait()

    except KeyboardInterrupt:
        socketIO_Robotics.disconnect()
        sys.exit('exiting reconnect.py, goodbye!')
