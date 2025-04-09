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

    def update_stir_rate(self, MESSAGE, immediate = True):
        data = {'param': 'stir', 'value': MESSAGE,
                'immediate': immediate, 'recurring': True}
        self.emit('command', data, namespace = '/dpu-evolver')

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
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, 8081), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            input = int(input("Enter duty cycle percent: "))
            print(input)
            stir_commands = [input]*16
            EVOLVER_NS.update_stir_rate(stir_commands)

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit('\nuser interrupt detected, exiting stir_test.py')

