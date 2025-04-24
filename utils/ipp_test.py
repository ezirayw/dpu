import socketio
import sys
import argparse

EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    BASE_MESSAGE_0 = ['$|1|&|*', '$|1|2|*', '$|1|@|*', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    BASE_MESSAGE_1 = ['--', '--', '--','$|2|1|*', '$|2|2|*', '$|2|3|*', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']

    OFF_MESSAGE_0 = ['0|1|1|0', '0|1|2|0', '0|1|3|0', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    OFF_MESSAGE_1 = ['--', '--', '--', '0|1|1|0', '0|1|2|0', '0|1|3|0', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    
    pump_time = None
    frequency = None
    layer = None
    flow_direction = None

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def fluid_command(self):
        if self.layer == 0:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE_1, 'recurring': False ,'immediate': True}        
            #self.emit('command', command, namespace='/default_evolver')

            temp_message = [element.replace('*', str(self.pump_time)) for element in self.BASE_MESSAGE_0]
            if self.flow_direction == 0:
                temp_message = [element.replace('&', '1') for element in temp_message]
                temp_message = [element.replace('@', '3') for element in temp_message]
            if self.flow_direction == 1:
                temp_message = [element.replace('&', '3') for element in temp_message]
                temp_message = [element.replace('@', '1') for element in temp_message]
            MESSAGE = [element.replace('$', str(self.frequency)) for element in temp_message]
            command = {'param': 'pump', 'value': MESSAGE, 'recurring': False ,'immediate': True}

            self.emit('command', command, namespace='/default_evolver')

        if self.layer == 1:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE_0,
                'recurring': False ,'immediate': True}        
            self.emit('command', command, namespace='/default_evolver')

            temp_message = [element.replace('*', str(self.pump_time)) for element in self.BASE_MESSAGE_1]
            MESSAGE = [element.replace('$', str(self.frequency)) for element in temp_message]
            command = {'param': 'pump', 'value': MESSAGE,
                    'recurring': False ,'immediate': True}

            self.emit('command', command, namespace='/default_evolver')

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip_address', action='store', required=True,
                        help='IP address of eVOLVER to run experiment on.')
    return parser.parse_args(), parser


if __name__ == '__main__':

    options, parser = get_options()
    evolver_ip = options.ip_address

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/default_evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, '8081'), namespaces=['/default_evolver'])
   
    try:
        while True:
            pump_time = input("Enter IPP pump time (seconds): ")
            frequency = input("Enter IPP actuation frequency: ")
            layer = input("Enter layer to flow through: ")
            direction = input("Enter direction to flow: ")
        
            EVOLVER_NS.layer = int(layer)
            EVOLVER_NS.pump_time = int(pump_time)
            EVOLVER_NS.frequency = int(frequency)
            EVOLVER_NS.flow_direction = int(direction) # 0 for efflux, 1 for prime
            EVOLVER_NS.fluid_command()

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit('user interrupt detected, exiting ipp_test.py')
