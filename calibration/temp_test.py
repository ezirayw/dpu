import socketio
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    BASE_MESSAGE = ['1879','1856','1800','1800']
    temp_input = 0

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def update_temp(self, immediate = True):
        MESSAGE = self.BASE_MESSAGE
        #for index in range(4):
         #   if MESSAGE[index] == '*':
          #      MESSAGE[index] = str(self.temp_input)
        data = {'param': 'temp', 'value': MESSAGE,
                'immediate': immediate, 'recurring': True}
        self.emit('command', data, namespace = '/dpu-evolver')


if __name__ == '__main__':

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format('192.168.1.15', '8081'), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            temp = input("Enter temp command: ")
        
            EVOLVER_NS.temp_input = int(temp)                
            EVOLVER_NS.update_temp()



    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

