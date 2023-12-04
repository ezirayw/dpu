import socketio
import argparse
import sys
# tell interpreter where to look

sys.path.insert(0,"../experiment/template")
from custom_script import ROBOTICS_PORT, EVOLVER_PORT
from robotic_functions import RoboticsNamespace

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')
    parser.add_argument('-t', '--time', action='store',
                        help='time (in minutes) for IPPs to run.')
    parser.add_argument('-p', '--pressure-range', action='store', nargs='+', dest='pressure_range',
                        help='minimum and maximum psi values for IPP valves')
    parser.add_argument('-z', '--hz-range', action='store', nargs='+', dest='hz_range',
                        help='minimum and maximum Hz values for IPP actuation')
    parser.add_argument('-s', '--steps', action='store', nargs='+',
                        help='step values for pressure and hz')
    parser.add_argument('-q', '--quads', action='store', nargs='+',
                        help='target Smart Quads for efflux calibration')
    return parser.parse_args(), parser

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

if __name__ == '__main__':
    options, parser = get_options()

    evolver_ip = options.ip_address
    ipp_time = options.time
    psi_range = [int(pressure) for pressure in options.pressure_range]
    psi_step = int(options.steps[0])
    
    hz_range = [int(hz) for hz in options.hz_range]
    hz_step = int(options.steps[1])
    active_quads = options.quads
    if evolver_ip is None:
        print('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)


    socketIO_eVOLVER = socketio.Client()
    socketIO_Robotics = socketio.Client()

    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    ROBOTICS_NS = RoboticsNamespace('/robotics')

    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_Robotics.register_namespace(ROBOTICS_NS)

    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, EVOLVER_PORT), namespaces=['/dpu-evolver'])
    socketIO_Robotics.connect("http://{0}:{1}".format(evolver_ip, ROBOTICS_PORT), namespaces=['/robotics'])   

    BASE_MESSAGE = ['*|1|1|$', '*|1|2|$', '*|1|3|$', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    OFF_MESSAGE = [command.replace('*', '0') for command in BASE_MESSAGE]
    OFF_MESSAGE = [command.replace('$', '0') for command in OFF_MESSAGE]
    fluidic_commands = {
        'syringe_pump_message': {'base_media': {'quad_0': {'vial_0': 350, 'vial_1': 350, 'vial_2': 350, 'vial_3': 350, 'vial_4': 350, 'vial_5': 350, 'vial_6': 350, 'vial_7': 350, 'vial_8': 350, 'vial_9': 350, 'vial_10': 350, 'vial_11': 350, 'vial_12': 350, 'vial_13': 350, 'vial_14': 350, 'vial_15': 350, 'vial_16': 350, 'vial_17': 350}}},
        'ipp_efflux_message': OFF_MESSAGE
        }
    
    try:
        # cycle through all IPP actuation frequencies for each IPP psi
        psi_current = psi_range[0]
        while psi_current <= psi_range[1]:
            # ask user to check if correct psi settings have been set for IPPs
            check_psi = None
            while check_psi == None:
                check_psi = input("Make sure that IPPs are set to the following pressure via the pressure regulator: {0} psi. Press enter to continue to dilutions.".format(psi_current))
            hz_current = hz_range[0]
            while hz_current <= hz_range[1]:
                # send dilution command to add excess volume to vials
                first_dilutions = None
                while first_dilutions == None:
                    first_dilutions = input("Press enter to start first round of dilutions.")
                ROBOTICS_NS.start_dilutions(fluidic_commands, ["quad_0"], test=False)
                second_dilutions = None

                # ask user if dilutions are complete and start efflux
                dilutions_check = None
                while dilutions_check == None:
                    dilutions_check = input("Did first round of dilutions finish for Smart Quad:{0}? Press enter to continue".format(0))

                while second_dilutions == None:
                    second_dilutions = input("Press enter to start second round of dilutions.")
                ROBOTICS_NS.start_dilutions(fluidic_commands, ["quad_0"], test=False)         

                # ask user if dilutions are complete and start efflux
                dilutions_check = None
                while dilutions_check == None:
                    dilutions_check = input("Did second round of dilutions finish for Smart Quad:{0}? Press enter to continue".format(0))           

                start_efflux = None
                while start_efflux == None:
                    # ask if user is ready to start efflux pumping                 
                    start_efflux = input("Current efflux settings are: {0} Hz  {1} psi  {2} seconds. Press enter to start efflux".format(hz_current,psi_current, ipp_time))        
                
                # send commmand to run IPPs at user specified duration
                ON_MESSAGE = [command.replace('*', str(hz_current)) for command in BASE_MESSAGE]
                ON_MESSAGE = [command.replace('$', str(ipp_time)) for command in ON_MESSAGE]
                EVOLVER_NS.fluid_command(ON_MESSAGE)

                next_step = None
                while next_step == None:
                    # ask if user is ready to go to next set of efflux parameters
                    next_step = input("Has flow rate data been collected? Press enter to continue to next parameter set")
                
                # increment hz by user specified step
                hz_current += hz_step
            
            # increment psi by user specified step
            psi_current += psi_step

    except KeyboardInterrupt:
        print('Efflux calibration stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        socketIO_Robotics.disconnect()
        sys.exit(1)