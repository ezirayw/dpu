import socketio
import time
import argparse
import sys
from robotic_functions import RoboticsNamespace
import logging
import os


class EvolverNamespace(socketio.ClientNamespace):
    def on_connect(self, *args):
        print('robotics_eVOLVER connected to base_eVOLVER server')

    def on_disconnect(self, *args):
        print('robotics_eVOLVER disconnected from base_eVOLVER server')

    def on_reconnect(self, *args):
        print("robotics_eVOLVER reconnected to base_eVOLVER as server")

    def fluid_command(self, MESSAGE):
        print('fluid command: %s' % MESSAGE)
        command = {'param': 'pump', 'value': MESSAGE,
                    'recurring': False ,'immediate': True}
        self.emit('command', command, namespace='/dpu-evolver')

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')  
    return parser.parse_args(), parser

if __name__ == '__main__':

    # setup logger
    logger = logging.getLogger('evolver')
    save_path = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(save_path, 'evolver.log')
    logging.basicConfig(format='%(asctime)s - %(name)s - [%(levelname)s] ''- %(message)s\n', datefmt='%Y-%m-%d %H:%M:%S', filename=filename, level=logging.INFO)

    # extract command line inputs from parser
    options, parser = get_options()
    evolver_ip = options.ip_address
    if evolver_ip is None:
        print('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)

    # SETUP FLUIDIC COMMANDS
    # TURBIDOSTAT_VIALS = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17],'quad_1': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]}
    PUMP_MESSAGE = ['--'] * 48
    TURBIDOSTAT_VIALS = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15]}
    IPP_ADDRESSES = {
        'quad_0': [16, 17, 18],
        'quad_1': [19, 20, 21],
        'quad_2': [24, 25, 26],
        'quad_3': [27, 28, 29]
    }

    # influx command variables for peristaltic pumps
    time_in = 2
    
    # efflux command variables for IPPs
    ipp_number = 1
    ipp_hz = 20 # frequency for IPP efflux pumps
    ipp_time = 120
    ipp_index = 1
    
    for quad in TURBIDOSTAT_VIALS:

        # write peristaltic pump commands for influx
        for vial in TURBIDOSTAT_VIALS[quad]:
            # calculate time to run influx pumps
            PUMP_MESSAGE[vial] = str(time_in)

        # write IPP commands for efflux
        for ipp_address in IPP_ADDRESSES[quad]:
            PUMP_MESSAGE[ipp_address] = '{0}|{1}|{2}|{3}'.format(ipp_hz, ipp_number, ipp_index, ipp_time)
            ipp_index = ipp_index + 1
                # setup efflux variables for next quad calculations
        ipp_number += 1

    # relevant data to build fluidic commands
    active_quads = list(TURBIDOSTAT_VIALS.keys())
    fluidic_commands = {
        'syringe_pump_message': None,
        'ipp_efflux_message': PUMP_MESSAGE}

    # setup client namespaces for eVOLVER and robotics
    socketIO_eVOLVER = socketio.Client(handle_sigint=False)
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')

    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/dpu-evolver'])

    last_time = None
    routine_number = 0
    while True:            
        try:                
            if EVOLVER_NS.broadcast_counter == 2 and EVOLVER_NS.running_routine == False:
                routine_number += 1
                logger.info('running routine number: %s', (routine_number))
                EVOLVER_NS.start_dilutions(fluidic_commands, active_quads)
    
        except KeyboardInterrupt:
            try:
                print('Ctrl-C detected')
                EVOLVER_NS.pause_experiment()

                while True:
                    exit_key = input('Experiment paused. Press enter key to restart or hit Ctrl-C again to terminate experiment')
                    print('resuming experiment')
                    EVOLVER_NS.resume_experiment()
                    break
            
            except KeyboardInterrupt:
                print('Second Ctrl-C detected, stopping experiment')                
                EVOLVER_NS.stop_experiment()
                break
        
        except Exception as e:
            print('Error detected, stopping experiment')
            print(e)
            EVOLVER_NS.stop_experiment()
            break
    
    socketIO_eVOLVER.disconnect()