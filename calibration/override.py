
import socketio
import argparse
import sys

# import all classes
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Override ROBOTICS_STATUS for HT_eVOLVER'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-m', '--mode', action='store', dest='mode',
                        help='Robotics mode to set ROBOTICS_STATUS to. Must be one of: idle, fill_tubing, priming, influx')
    parser.add_argument('-s', '--syringe_prime', action='store_true', dest='syringe_prime',
                        help='set syringe pump primed status. default is False')
    parser.add_argument('-e', '--efflux_ipp', action='store_true', dest='efflux_ipp',
                        help='set efflux ipps primed status. default is False')
    parser.add_argument('-i', '--ip_address', action='store', dest='ip_address', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-r', '--reset-arm', action='store_true', dest='reset_arm',
                        help='reset xArm settings')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    mode = options.mode
    prime_influx = options.syringe_prime
    prime_efflux = options.efflux_ipp
    reset_arm = options.reset_arm
    
    if mode is not None and mode not in ['idle', 'fill_tubing', 'priming', 'influx', 'pause', 'resume']:
        parser.print_help()
        sys.exit('Invalid mode. Must be one of: idle, fill_tubing, priming, influx')

    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics'])

    try:
        payload = {}
        payload['mode'] = options.mode
        payload['prime_status'] = {'influx': prime_influx, 'efflux': prime_efflux}
        payload['reset_xArm'] = reset_arm

        print(payload)
    
        ROBOTICS_NS.override_status(payload)
        socketIO_Robotics.wait()

    except KeyboardInterrupt:
        socketIO_Robotics.disconnect()
        sys.exit('exiting override.py, goodbye!')
