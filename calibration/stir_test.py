import socketio
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    BASE_MESSAGE = ['*','*',0,0]
    stir_input = 0

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def update_stir_rate(self, immediate = True):
        MESSAGE = self.BASE_MESSAGE
        for index in range(4):
            if MESSAGE[index] == '*':
                MESSAGE[index] = int(self.stir_input)
        data = {'param': 'stir', 'value': MESSAGE,
                'immediate': immediate, 'recurring': True}
        self.emit('command', data, namespace = '/dpu-evolver')


if __name__ == '__main__':

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format('192.168.1.15', '8081'), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            stir_command = input("Enter stir command (0-100): ")
        
            EVOLVER_NS.stir_input = int(stir_command)                
            EVOLVER_NS.update_stir_rate()



    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

