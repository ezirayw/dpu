
import socketio
import argparse
import sys

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Override ROBOTICS_STATUS for HT_eVOLVER'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip_address', action='store', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-m', '--mode', action='store',
                        help='Set Robotics server mode. Must be found in "modes" section of robotics_server_conf')
    parser.add_argument('-s', '--syringe_prime', action='store',
                        help='Set syringe pump primed status. Must be a boolean value.')
    parser.add_argument('-e', '--efflux_ipp', action='store',
                        help='Set efflux ipps primed status. Must be a boolean value.')
    parser.add_argument('-r', '--reset_arm', action='store_true',
                        help='Reset xArm state and align end effector. Default is False (no reset)')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    mode = options.mode
    prime_influx = options.syringe_prime
    prime_efflux = options.efflux_ipp
    reset_arm = options.reset_arm

    if prime_influx not in [None, '0', '1'] and prime_efflux not in [None, '0', '1']:
        parser.print_help()
        sys.exit('Invalid prime status entered. Must be either 0 (False) or 1 (True) or left empty.')
    
    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics_evolver')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics_evolver'])

    try:
        payload = {}
        if mode:
            payload['mode'] = options.mode
        
        if prime_influx != None or prime_efflux != None:
            payload['prime_status'] = {}            
            if prime_influx != None:
                payload['prime_status']['influx'] = bool(prime_influx)
            if prime_efflux != None:
                payload['prime_status']['efflux'] = bool(prime_efflux)
        
        if reset_arm:
            payload['reset_xArm'] = reset_arm

        print(payload)
    
        ROBOTICS_NS.override_status(payload)
        socketIO_Robotics.wait()

    except KeyboardInterrupt:
        socketIO_Robotics.disconnect()
        sys.exit('exiting override.py, goodbye!')
