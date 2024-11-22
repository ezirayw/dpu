import socketio
import sys
import argparse


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def update_temp(self, MESSAGE, immediate = True):
        #BASE_MESSAGE = ['1879','1856','1800','1800']
        data = {'param': 'temp', 'value': MESSAGE,
                'immediate': immediate, 'recurring': True}
        self.emit('command', data, namespace = '/dpu-evolver')

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-i', '--ip_address', action='store', dest='ip_address', required=True,
                        help='IP address of eVOLVER to run experiment on.')

    return parser.parse_args(), parser

if __name__ == '__main__':

    options, parser = get_options()
    evolver_ip = options.ip_address

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            target_quads = input("Enter target Smart Quads (0-3), separated by spaces: ")
            target_quads = target_quads.split(' ')
            print(target_quads)
            temp_commands = [0, 0, 0, 0]
            
            for quad in target_quads:
                temp_command = None
                while True:
                    temp_command = int(input("Enter temp command (0-100) for Smart Quad {0}: ".format(quad)))
                    if temp_command < 0 or temp_command > 100:
                        print("Invalid temp command, must be between 0 and 100")
                    else:
                        temp_commands[int(quad)] = temp_command
                        break

            EVOLVER_NS.update_temp(temp_commands)

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit('user interrupt detected, exiting temp_test.py')

