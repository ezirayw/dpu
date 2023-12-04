import socketio
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    BASE_MESSAGE = ['$|1|1|*', '$|1|2|*', '$|1|3|*', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    OFF_MESSAGE = ['0|1|1|0', '0|1|2|0', '0|1|3|0', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    pump_time = 0
    frequency = 5

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def fluid_command(self, off=False):
        temp_message = [element.replace('*', str(self.pump_time)) for element in self.BASE_MESSAGE]
        MESSAGE = [element.replace('$', str(self.frequency)) for element in temp_message]
        command = {'param': 'pump', 'value': MESSAGE,
                   'recurring': False ,'immediate': True}
        if off == True:
            command = {'param': 'pump', 'value': self.OFF_MESSAGE,
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

            if int(pump_time):                
                EVOLVER_NS.pump_time = int(pump_time)
                EVOLVER_NS.frequency = int(frequency)
                EVOLVER_NS.fluid_command()
            if pump_time == '0':
                EVOLVER_NS.fluid_command(off=True)


    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

