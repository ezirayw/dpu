import socketio
import numpy as np
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

    def update_led(self, left_led_commands, right_led_commands):

        left_data = {'param': 'od_led_left', 'value': left_led_commands,
                'immediate': True, 'recurring': True}
        right_data = {'param': 'od_led_right', 'value': right_led_commands,
                'immediate': True, 'recurring': True}
       
        self.emit('command', left_data, namespace = '/dpu-evolver')
        self.emit('command', right_data, namespace = '/dpu-evolver')

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
    socketIO_eVOLVER.connect("http://{0}:{1}".format(evolver_ip, '8081'), namespaces=['/dpu-evolver'])
   
    try:
        while True:
            target_quads = input("Enter target Smart Quads (0-3), separated by spaces: ")
            target_quads = target_quads.split(' ')
            print(target_quads)
            left_led_commands = [0]*8
            right_led_commands = [0]*8

            
            for quad in target_quads:
                led_command = None
                while True:
                    led_command = int(input("Enter led command (4095 or 0) for Smart Quad {0}, vial set (0,1,2,8): ".format(quad)))
                    if led_command != 0 and led_command != 4095:
                        print("Invalid led command for vial set (0,1,2,8), must be 4095 or 0")
                    else:
                        left_led_commands[int(quad)] = led_command
                        break
                while True:
                    led_command = int(input("Enter led command (4095 or 0) for Smart Quad {0}, vial set (6,7,12,13,14): ".format(quad)))
                    if led_command != 0 and led_command != 4095:
                        print("Invalid led command for vial set (6,7,12,13,14), must be 4095 or 0")
                    else:
                        left_led_commands[int(quad)+1] = led_command
                        break
                while True:
                    led_command = int(input("Enter led command (4095 or 0) for Smart Quad {0}, vial set (3,4,5,11): ".format(quad)))
                    if led_command != 0 and led_command != 4095:
                        print("Invalid led command for vial set (3,4,5,11), must be 4095 or 0")
                    else:
                        right_led_commands[int(quad)] = led_command
                        break
                while True:
                    led_command = int(input("Enter led command (4095 or 0) for Smart Quad {0}, vial set (9,10,15,16,17): ".format(quad)))
                    if led_command != 0 and led_command != 4095:
                        print("Invalid led command for vial set (9,10,15,16,17), must be 4095 or 0")
                    else:
                        right_led_commands[int(quad)+1] = led_command
                        break
                        
            EVOLVER_NS.update_led(left_led_commands,right_led_commands)

    except KeyboardInterrupt:
        socketIO_eVOLVER.disconnect()
        sys.exit('\nuser interrupt detected, exiting led_test.py')

