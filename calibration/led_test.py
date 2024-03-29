import socketio
import numpy as np
import sys


EVOLVER_NS = None

class EvolverNamespace(socketio.ClientNamespace):

    left_vials = [[0, 1, 2], [6, 7, 8], [12, 13, 14]]
    right_vials = [[3, 4, 5], [9, 10, 11], [15, 16, 17]]
    channel_map = [[0, 1, 4], [2, 3, 6], [8, 9, 12], [10, 11, 14]]

    BASE_MESSAGE = ['0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0']

    def on_connect(self, *args):
        pass

    def on_disconnect(self, *args):
        pass
    def on_reconnect(self, *args):
        pass

    def update_led(self, quad, vial_selection):
        LEFT_MESSAGE = self.BASE_MESSAGE
        RIGHT_MESSAGE = self.BASE_MESSAGE

        if quad == 4:
            for i in range(len(self.BASE_MESSAGE)):
                LEFT_MESSAGE[i] = '4095'
                RIGHT_MESSAGE[i] = '4095'
        else:
            active_channels = self.channel_map[quad]
            for vial in vial_selection:
                index = None
                if any(vial in sub for sub in self.left_vials):
                    index = np.where(self.left_vials==vial)
                    channel = active_channels[index[0]]
                    LEFT_MESSAGE[channel] = '0'
                if any(vial in sub for sub in self.right_vials):
                    index = np.where(self.right_vials==vial)
                    channel = active_channels[index[0]]
                    RIGHT_MESSAGE[channel] = '0'

        left_data = {'param': 'od_led_left', 'value': LEFT_MESSAGE,
                'immediate': True, 'recurring': True}
        right_data = {'param': 'od_led_right', 'value': RIGHT_MESSAGE,
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
            vial_selection = input("Enter vial(s) or 4 for entire quad: ")
            EVOLVER_NS.update_led(int(quad), int(vial_selection))

    except KeyboardInterrupt:
        print('Experiment stopped, goodbye!')
        socketIO_eVOLVER.disconnect()
        sys.exit(0)

