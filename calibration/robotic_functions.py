import os, json
import logging
import socketio
import time

class RoboticsNamespace(socketio.ClientNamespace):

    evolver_ns = None
    retreive_status = None
    running_routine = False
    status = {}
    pump_config = None
    logger = logging.getLogger(__name__)
    save_path = os.path.dirname(os.path.realpath(__file__))
    pump_config_path = os.path.join(save_path, 'pump_config.json')
    broadcast_counter = 0

    def on_connect(self, *args):
        self.logger.info('dpu connected to robotics_eVOLVER server')
        #print('dpu connected to robotics_eVOLVER server')
        self.request_robotics_status()

    def on_disconnect(self, *args):
        self.logger.info('dpu disconnected from robotics_eVOLVER server')
        #print('dpu disconnected from robotics_eVOLVER server')

    def on_reconnect(self, *args):
        self.logger.info('dpu reconnected to robotics_eVOLVER server')
        #print('dpu reconnected to robotics_eVOLVER server')

    def on_broadcast(self, data):
        self.logger.info('Robotics broadcast received')
        self.status = data

        if self.broadcast_counter == 2:
            self.broadcast_counter = 0

        if self.status['mode'] == 'idle' and self.running_routine == False:
            self.broadcast_counter += 1

    # experiment management functions
    def pause_experiment(self):
        self.logger.info('pausing experiment')
        #print('pausing experiment')
        self.emit('pause_robotics', {}, namespace = '/robotics')

    def resume_experiment(self):
        self.logger.info('resuming experiment')
        self.emit('resume_robotics', {}, namespace = '/robotics')

    def stop_experiment(self):
        self.logger.info('stopping experiment')
        self.emit('stop_robotics', {}, namespace = '/robotics')

    def exit_experiment(self):
        self.logger.info('exiting experiment')
        self.emit('exit_robotics', {}, namespace = '/robotics')
    
    def acknowledge_routine(self, data):
        self.logger.info(data)
        self.running_routine = False

    def acknowledge_retreival(self, data):
        self.logger.info(data)
        if data['type'] == 'pump':
            self.pump_config = data['data']
        if data['type'] == 'robotics':
            self.status = data['data']
        self.retreive_status = True

    def pipette(self, data):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('pipette syringe pumps')
            self.emit('pipette_routine', data, namespace = '/robotics', callback = self.acknowledge_routine)
        else:
            self.logger.warning('robotics not in idle mode, cannot pipette')

    def prime_influx_pumps(self, syringe_pumps={}):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('prime influx syringe pumps')
            self.emit('prime_influx_routine', syringe_pumps, namespace = '/robotics')
        else:
            self.logger.warning('robotics not in idle mode, cannot prime influx pumps')
    
    def prime_efflux_pumps(self, quads):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('prime efflux IPPs pumps')
            data = {'target_quads': quads}
            self.emit('prime_efflux_routine', data, namespace = '/robotics')            
        else:
            self.logger.warning('robotics not in idle mode, cannot prime efflux pumps')

    def start_dilutions(self, fluidic_commands, quads):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('dilution routine execution: %s' % fluidic_commands)
            #print('dilution routine execution: {}'.format(fluidic_commands))
            data = {'commands': fluidic_commands, 'target_quads': quads, 'mode': 'dilution'}
            self.emit('dilution_routine', data, namespace = '/robotics', callback = self.acknowledge_routine)
        else:
            self.logger.warning('robotics not in idle mode, cannot start dilutions')

    def fill_vials_syringe_pumps(self, fluidic_commands, quads):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('fill vials media and/or other fluids via syringe pumps: %s' % fluidic_commands)
            #print('setup vials with media prior to innoculation: {}'.format(fluidic_commands))
            data = {'commands': fluidic_commands, 'target_quads': quads, 'hardware': 'syringe_pumps'}
            self.emit('fill_vials_routine', data, namespace = '/robotics', callback=self.acknowledge_routine)
        else:
            self.logger.warning('robotics not in idle mode, cannot fill vials with robotic xArm')

    def fill_vials_ipp(self, quads):
        self.retreive_status = False
        self.request_robotics_status()
        while self.retreive_status == False:
            time.sleep(0.1)
        
        if self.status['mode'] == 'idle':
            self.running_routine = True
            self.logger.info('fill vials with media and/or other fluids via efflux IPPs')
            #print('fill vials with media and/or other fluids via efflux IPPs')
            data = {'target_quads': quads, 'hardware': 'ipp'}
            self.emit('fill_vials_routine', data, namespace = '/robotics', callback=self.acknowledge_routine)
        else:
            self.logger.warning('robotics not in idle mode, cannot fill vials with efflux IPPs')

    def request_pump_settings(self):
        self.logger.info('requesting pump settings')
        self.emit('request_pump_settings', {}, namespace = '/robotics', callback=self.acknowledge_retreival)
    
    def request_robotics_status(self):
        self.logger.info('requesting robotics status')
        self.emit('request_robotics_status', {}, namespace = '/robotics', callback=self.acknowledge_retreival)
    
    def stop_robotics(self):
        self.logger.info('stopping robotics')
        self.emit('stop_robotics', {}, namespace = '/robotics')

    def override_status(self, data):
        self.logger.info('overriding robotics status with following command: %s' % data)
        #print('overriding robotics status with following command: {}'.format(data))
        self.emit('override_robotics_status', data, namespace = '/robotics' )

    def reconnect(self, data):
        self.logger.info('reconnect to robotics with following command: %s' % data)
        #print('reconnect to robotics with following command: {}'.format(data))
        self.emit('reconnect_robotics', data, namespace = '/robotics' )

if __name__ == '__main__':
    #print('Please run eVOLVER.py instead')