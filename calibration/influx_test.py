
import socketio
import time
import argparse
import sys
from robotic_functions import RoboticsNamespace
import logging
import os

def media_transform(pump_list, test, active_quads):
    dilutions = {}

    # scan through fluid command and convert dilution volumes to stepper motor steps based on volume --> steps calibration
    for pump in pump_list:
        pump_json = {}

        for quad in active_quads:
            pump_json[quad] = {}

            for vial in range(18):
                vial_name = 'vial_{0}'.format(vial)
                if test:
                    pump_json[quad][vial_name] = 0 # used for debugging fluidics
                else:
                    pump_json[quad][vial_name] = round(619.47 * 6)
        dilutions[pump] = pump_json
    return dilutions

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip_address', action='store', dest='ip_address', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-m', '--mode', action='store', dest='mode', required=True,
                        help='Set to either fill_vials or start_dilutions to select what mode to operate influx system in')
    parser.add_argument('-t', '--test-volume', action='store_true',
                        help='Add test flag to set influx volumes to 0 mL. Useful for testing purposes.')
    
    return parser.parse_args(), parser

if __name__ == '__main__':

    # setup command line parser
    options, parser = get_options()
    evolver_ip = options.ip_address
    mode = options.mode

    if mode not in ['fill_vials', 'start_dilutions']:
        parser.print_help()
        sys.exit('Invalid mode. Must be one of: fill_vials, start_dilutions')

    # turbidostat_vials = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17],'quad_1': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]}
    turbidostat_vials = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]}
    test_volume = options.test_volume
    test_pumps = {'base_media_0': {'quad_0': [0] * 18}}
    
    # efflux commands
    IPP_EFFLUX_MESSAGE = {}
    ipp_hz = 5 # frequency for IPP efflux pumps
    ipp_time = 90
    for quad in turbidostat_vials:
        IPP_EFFLUX_MESSAGE[quad] = {'frequency': ipp_hz, 'duration': ipp_time, 'polarity': 0}

    active_quads = list(turbidostat_vials.keys())
    SYRINGE_PUMP_MESSAGE = media_transform(test_pumps, test_volume, active_quads)

    fluidic_commands = {
        'syringe_pump_command': SYRINGE_PUMP_MESSAGE,
        'ipp_efflux_command': IPP_EFFLUX_MESSAGE}

    # setup logger
    logger = logging.getLogger('evolver')
    save_path = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(save_path, 'evolver.log')
    logging.basicConfig(format='%(asctime)s - %(name)s - [%(levelname)s] ''- %(message)s\n', datefmt='%Y-%m-%d %H:%M:%S', filename=filename, level=logging.INFO)

    # setup client namespaces for eVOLVER and robotics
    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics'])

    routine_number = 0
    while True:            
        try:                
            if ROBOTICS_NS.broadcast_counter == 2 and ROBOTICS_NS.running_routine == False:
                routine_number += 1
                logger.info('running routine number: %s', (routine_number))
                
                if mode == 'fill_vials':
                    ROBOTICS_NS.fill_vials_syringe_pumps(fluidic_commands, active_quads)
                if mode == 'start_dilutions':
                    ROBOTICS_NS.start_dilutions(fluidic_commands, active_quads)

        except KeyboardInterrupt:
            try:
                print('Ctrl-C detected')
                ROBOTICS_NS.pause_experiment()

                while True:
                    exit_key = input('Experiment paused. Press enter key to restart or hit Ctrl-C again to terminate experiment')
                    print('resuming experiment')
                    ROBOTICS_NS.resume_experiment()
                    break
            
            except KeyboardInterrupt:
                print('Second Ctrl-C detected, stopping experiment')                
                ROBOTICS_NS.exit_experiment()
                break
        
        except Exception as e:
            print('Error detected, stopping experiment')
            print(e)
            ROBOTICS_NS.stop_experiment()
            break
    
    socketIO_Robotics.disconnect()
    sys.exit('exiting influx_test.py, goodbye!')