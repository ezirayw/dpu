import os, json
import logging
import socketio

# logger setup
logger = logging.getLogger(__name__)

SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
PUMP_CONFIG_PATH = os.path.join(SAVE_PATH, 'pump_config.json')

class RoboticsNamespace(socketio.ClientNamespace):

    evolver_ns = None
    status = {'mode': None}
    running_routine = False
    pump_config = None

    def on_connect(self, *args):
        logger.info('dpu connected to robotics_eVOLVER server')
        print('dpu connected to robotics_eVOLVER server')

    def on_disconnect(self, *args):
        logger.info('dpu disconnected from robotics_eVOLVER server')
        print('dpu disconnected from robotics_eVOLVER server')

    def on_reconnect(self, *args):
        logger.info('dpu reconnected to robotics_eVOLVER server')
        print('dpu reconnected to robotics_eVOLVER server')

    def on_broadcast(self, data):
        logger.info('Robotics broadcast received')
        print('Robotics broadcast received')
        self.status = data

    # experiment management functions
    def pause_experiment(self):
        logger.info('pausing experiment')
        print('pausing experiment')
        self.emit('pause_robotics', {}, namespace = '/robotics')

    def resume_experiment(self):
        logger.info('resuming experiment')
        self.emit('resume_robotics', {}, namespace = '/robotics')

    def stop_experiment(self):
        logger.info('stopping experiment')
        self.emit('stop_robotics', {}, namespace = '/robotics')
    
    def acknowledge_routine(self, data):
        logger.info(data)
        #print(data)
        self.running_routine = False

    def acknowledge_retreival(self, data):
        logger.info(data)
        #print(data)
        if data['type'] == 'pump':
            self.pump_config = data['data']
        if data['type'] == 'robotics':
            self.status = data['data']

    # robotic feature functions functions
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
        self.emit('fill_tubing_routine', {}, namespace = '/robotics')

    def prime_pumps(self):
        logger.info('prime pumps for dilution events')
        self.emit('prime_pumps_routine', {}, namespace = '/robotics')

    def start_dilutions(self, fluidic_commands, quads):
        logger.info('dilution routine execution: %s' % fluidic_commands)
        print('dilution routine execution: {}'.format(fluidic_commands))
        data = {'message': fluidic_commands, 'active_quads': quads, 'mode': 'dilution', 'wash':True}
        self.running_routine = True
        self.emit('influx_routine', data, namespace = '/robotics', callback = self.acknowledge_routine)

    def setup_vials(self, fluidic_commands, quads):
        logger.info('setup vials with media prior to innoculation: %s' % fluidic_commands)
        print('setup vials with media prior to innoculation: {}'.format(fluidic_commands))
        data = {'message': fluidic_commands, 'active_quads': quads, 'mode': 'setup', 'wash': True}
        self.running_routine = True
        self.emit('influx_routine', data, namespace = '/robotics', callback=self.acknowledge_routine)

    def request_pump_settings(self):
        logger.info('requesting pump settings')
        self.emit('request_pump_settings', {}, namespace = '/robotics', callback=self.acknowledge_retreival)
    
    def request_robotics_status(self):
        logger.info('requesting robotics status')
        self.emit('request_robotics_status', {}, namespace = '/robotics', callback=self.acknowledge_retreival)
    
    def stop_robotics(self):
        logger.info('stopping robotics')
        self.emit('stop_robotics', {}, namespace = '/robotics')

    def override_status(self, data):
        logger.info('overriding robotics status with following command: %s' % data)
        print('overriding robotics status with following command: {}'.format(data))
        self.emit('override_robotics_status', data, namespace = '/robotics' )

if __name__ == '__main__':
    print('Please run eVOLVER.py instead')
    logger.info('Please run eVOLVER.py instead')