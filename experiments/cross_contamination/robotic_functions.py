import os, json
import logging
import socketio

# logger setup
logger = logging.getLogger(__name__)

SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
PUMP_SETTINGS_PATH = os.path.join(SAVE_PATH, 'pump_settings.json')

class RoboticsNamespace(socketio.ClientNamespace):

    evolver_ns = None
    status = {'mode': None}

    def on_connect(self, *args):
        logger.info('dpu connected to robotics_eVOLVER server')

    def on_disconnect(self, *args):
        logger.info('dpu disconnected from robotics_eVOLVER server')

    def on_reconnect(self, *args):
        logger.info('dpu reconnected to robotics_eVOLVER server')

    def on_broadcast(self, data):
        logger.info('Robotics broadcast received')
        self.status = data

    def on_active_pump_settings(self, data):
        logger.info("received active pump settings")
        with open(PUMP_SETTINGS_PATH, 'w') as f:
            json.dump(data['data'], f)

    def arm_test(self):
        logger.info('running arm test')
        self.emit('arm_test', {}, namespace='/robotics')

    def move_to_quad(self, quad):
        logger.info('moving arm to quad {0}'.format(quad))
        self.emit('move_to_quad', {'quad': quad}, namespace = '/robotics')

    def reset_arm(self):
        logger.info('resetting arm to home position')
        self.emit('reset_arm', {}, namespace = '/robotics')

    def fill_tubing(self):
        logger.info('fill tubing lines with fluid')
        self.emit('fill_tubing', {}, namespace = '/robotics')

    def prime_pumps(self):
        logger.info('prime pumps for dilution events')
        self.emit('prime_pump', {}, namespace = '/robotics')

    def start_dilutions(self, fluidic_commands, quads):
        logger.info('dilution routine execution: %s', fluidic_commands)
        data = {'message': fluidic_commands, 'active_quads': quads, 'mode': 'dilution', 'wash':True}
        self.emit('influx_snake', data, namespace = '/robotics')

    def setup_vials(self, fluidic_commands, quads):
        logger.info('setup vials with media prior to innoculation: %s', fluidic_commands)
        data = {'message': fluidic_commands, 'active_quads': quads, 'mode': 'setup'}
        self.emit('influx_snake', data, namespace = '/robotics')

    def request_pump_settings(self):
        logger.info('requesting active pump settings')
        self.emit('get_pump_settings', {}, namespace = '/robotics')
    
    def request_robotics_status(self):
        logger.info('requesting robotics status')
        self.emit('request_robotics_status', {}, namespace = '/robotics')
    
    def stop_robotics(self):
        logger.info('stopping robotics')
        self.emit('stop_robotics', {}, namespace = '/robotics')

    def update(self):
        logger.info('updating...')


if __name__ == '__main__':
    print('Please run eVOLVER.py instead')
    logger.info('Please run eVOLVER.py instead')