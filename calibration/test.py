
import socketio
import argparse
import sys

def get_options():
    description = 'Override ROBOTICS_STATUS for HT_eVOLVER'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-m', '--mode', action='store', dest='mode',
                        help='Robotics mode to set ROBOTICS_STATUS to. Must be one of: idle, fill_tubing, priming, influx')
    parser.add_argument('-p', '--syringe_prime', action='store_true', dest='syringe_prime',
                        help='set syringe pump primed status. Must be one of: True, False')
    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-r', '--reset-arm', action='store_true', dest='reset_arm',
                        help='reset xArm settings')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    mode = options.mode
    prime = options.syringe_prime
    reset_arm = options.reset_arm

    try:
        print(evolver_ip)
        print(mode)
        print(prime)
        print(reset_arm)

    except KeyboardInterrupt:
        print('exiting override, goodbye!')
        sys.exit()
