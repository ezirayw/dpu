import socketio
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    MESSAGE = ['20|1|1|60', '20|1|2|60', '20|1|3|60', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--']
    pump_time = 0
    
    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def fluid_command(self):
#        self.MESSAGE = self.MESSAGE.replace('*', str(self.pump_time))
        command = {'param': 'pump', 'value': self.MESSAGE,
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

            if int(pump_time):                
                EVOLVER_NS.pump_time = int(pump_time)
                EVOLVER_NS.fluid_command()
            else:
                print("Please enter a integer value")


    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

