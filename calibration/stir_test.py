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
            stir_commands = [0, 0, 0, 0]
            
            for quad in target_quads:
                stir_command = None
                while True:
                    stir_command = int(input("Enter stir command (0-100) for Smart Quad {0}: ".format(quad)))
                    if stir_command < 0 or stir_command > 100:
                        print("Invalid stir command, must be between 0 and 100")
                    else:
                        stir_commands[int(quad)] = stir_command
                        break

            EVOLVER_NS.update_stir_rate(stir_commands)

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit('\nuser interrupt detected, exiting stir_test.py')

