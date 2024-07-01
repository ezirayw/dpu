
import socketio
import argparse
import sys

# import all classes
from robotic_functions import RoboticsNamespace

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
                    #pump_json[quad][vial_name] = round(619.47 * 6.435)
                    pump_json[quad][vial_name] = round(299)
        dilutions[pump] = pump_json
    return dilutions

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-t', '--test-volume', action='store_true',
                           help='Disable to dispense volumes with syringe pumps')
    
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    test_volume = options.test_volume
    test_pumps = {'base_media':
                  {'quad_1': [0] * 18}
                  }

    #turbidostat_vials = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17],'quad_1': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]}
    turbidostat_vials = {'quad_0': [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17]}
    IPP_EFFLUX_MESSAGE = ['--'] * 48
    IPP_ADDRESSES = {
        'quad_0': [0, 1, 2],
        'quad_1': [3, 4,5],
        'quad_2': [8, 9, 10],
        'quad_3': [11, 12, 13]
    }
    
    ipp_number = 1
    ipp_hz = 20 # frequency for IPP efflux pumps
    ipp_time = 120
    ipp_index = 1
    for quad in turbidostat_vials:
        for ipp_address in IPP_ADDRESSES[quad]:
            IPP_EFFLUX_MESSAGE[ipp_address] = '{0}|{1}|{2}|{3}'.format(ipp_hz, ipp_number, ipp_index, ipp_time)
            ipp_index = ipp_index + 1
                # setup efflux variables for next quad calculations
        ipp_number += 1

    if evolver_ip is None:
        print('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)

    socketIO_Robotics = socketio.Client(handle_sigint=False)
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_Robotics.register_namespace(ROBOTICS_NS)
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, 8080), namespaces=['/robotics'])

    active_quads = list(turbidostat_vials.keys())
    SYRINGE_PUMP_MESSAGE = media_transform(test_pumps, test_volume,active_quads)

    fluidic_commands = {
        'syringe_pump_message': SYRINGE_PUMP_MESSAGE,
        'ipp_efflux_message': IPP_EFFLUX_MESSAGE
    }
    
    ROBOTICS_NS.start_dilutions(fluidic_commands, active_quads)
    #ROBOTICS_NS.setup_vials(fluidic_commands, active_quads)

    while True:
        try:
            socketIO_Robotics.wait()        
        
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
                ROBOTICS_NS.stop_experiment()
                break
        
        except Exception as e:
            print('Error detected, stopping experiment')
            print(e)
            ROBOTICS_NS.stop_experiment()
            break
    
    socketIO_Robotics.disconnect()


