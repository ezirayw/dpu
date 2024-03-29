import socketio
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    BASE_MESSAGE_0 = ['$|1|1|*', '$|1|2|*', '$|1|3|*', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    BASE_MESSAGE_1 = ['--', '--', '--','$|2|1|*', '$|2|2|*', '$|2|3|*', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']

    OFF_MESSAGE_0 = ['0|1|1|0', '0|1|2|0', '0|1|3|0', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    OFF_MESSAGE_1 = ['--', '--', '--', '0|1|1|0', '0|1|2|0', '0|1|3|0', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    pump_time = 0
    frequency = 5
    layer = 0

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def fluid_command(self, off=False):
        if self.layer == 0:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE_1,
                'recurring': False ,'immediate': True}        
            self.emit('command', command, namespace='/dpu-evolver')

            temp_message = [element.replace('*', str(self.pump_time)) for element in self.BASE_MESSAGE_0]
            MESSAGE = [element.replace('$', str(self.frequency)) for element in temp_message]
            command = {'param': 'pump', 'value': MESSAGE,
                    'recurring': False ,'immediate': True}

            self.emit('command', command, namespace='/dpu-evolver')

        if self.layer == 1:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE_0,
                'recurring': False ,'immediate': True}        
            self.emit('command', command, namespace='/dpu-evolver')

            temp_message = [element.replace('*', str(self.pump_time)) for element in self.BASE_MESSAGE_1]
            MESSAGE = [element.replace('$', str(self.frequency)) for element in temp_message]
            command = {'param': 'pump', 'value': MESSAGE,
                    'recurring': False ,'immediate': True}

            self.emit('command', command, namespace='/dpu-evolver')
        
        if off == True:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE_0,
            'recurring': False ,'immediate': True}
            self.emit('command', command, namespace='/dpu-evolver')

            command = {'param': 'pump', 'value': self.OFF_MESSAGE_1,
            'recurring': False ,'immediate': True}
            self.emit('command', command, namespace='/dpu-evolver')

if __name__ == '__main__':

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format('192.168.1.15', '8081'), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            pump_time = input("Enter IPP pump time (seconds): ")
            frequency = input("Enter IPP actuation frequency: ")
            layer = input("Enter layer to flow through: ")

            if layer:
                EVOLVER_NS.layer = int(layer)
            if int(pump_time):                
                EVOLVER_NS.pump_time = int(pump_time)
                EVOLVER_NS.frequency = int(frequency)
                EVOLVER_NS.fluid_command()
            if pump_time == '0':
                EVOLVER_NS.fluid_command(off=True)


    except KeyboardInterrupt:
        print('exiting stir test, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

