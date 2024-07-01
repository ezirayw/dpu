import socketio
import numpy as np
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    left_vials = [[0, 1, 2], [6, 7, 8], [12, 13, 14]]
    right_vials = [[3, 4, 5], [9, 10, 11], [15, 16, 17]]
    channel_map = [[0, 1, 4], [2, 3, 6], [8, 9, 12], [10, 11, 14]]

    LEFT_MESSAGE = ['4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095']
    RIGHT_MESSAGE = ['4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095','4095']


    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def update_led(self, quad, vial_selection):
        if quad == 4:
            for i in range(16):
                self.LEFT_MESSAGE[i] = '4095'
                self.RIGHT_MESSAGE[i] = '4095'
        else:
            active_channels = self.channel_map[quad]
            for vial in vial_selection:
                index = None
                if any(vial in sub for sub in self.left_vials):  # Check if vial is in any sublist in self.left_vials
                    index = next((i for i, sub in enumerate(self.left_vials) if vial in sub), None)
                    channel = active_channels[index]
                    self.LEFT_MESSAGE[channel] = '0'
                if any(vial in sub for sub in self.right_vials):  # Check if vial is in any sublist in self.right_vials
                    index = next((i for i, sub in enumerate(self.right_vials) if vial in sub), None)
                    channel = active_channels[index]
                    self.RIGHT_MESSAGE[channel] = '0'

        left_data = {'param': 'od_led_left', 'value': self.LEFT_MESSAGE,
                'immediate': True, 'recurring': True}
        right_data = {'param': 'od_led_right', 'value': self.RIGHT_MESSAGE,
                'immediate': True, 'recurring': True}
       
        self.emit('command', left_data, namespace = '/dpu-evolver')
        self.emit('command', right_data, namespace = '/dpu-evolver')



if __name__ == '__main__':

    socketIO_eVOLVER = socketio.Client()
    EVOLVER_NS = EvolverNamespace('/dpu-evolver')
    socketIO_eVOLVER.register_namespace(EVOLVER_NS)
    socketIO_eVOLVER.connect("http://{0}:{1}".format('192.168.1.15', '8081'), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            quad = input("Enter quad number (0, 1, 2, or 3, OR 4 for all): ")
            vial_selection = list(map(int, input("Enter vial(s) or 4 for entire quad: ").split(',')))  # Convert comma-separated input to a list of integers
            EVOLVER_NS.update_led(int(quad), vial_selection)

    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

