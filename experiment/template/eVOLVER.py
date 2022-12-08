#!/usr/bin/env python3

import os
import sys
import time
import pickle
import shutil
import logging
import argparse
import numpy as np
import json
import traceback
from scipy import stats
from socketIO_client import SocketIO, BaseNamespace
from nbstreamreader import NonBlockingStreamReader as NBSR

import custom_script
from custom_script import EXP_NAME
from custom_script import EVOLVER_PORT, OPERATION_MODE
from custom_script import STIR_INITIAL_HT, TEMP_INITIAL_HT

import fluidic_client
from fluidic_client import XARM_PORT

# Should not be changed
# vials to be considered/excluded should be handled
# inside the custom functions
QUADS = {'quad_0': [x for x in range(18)], 'quad_1': [x for x in range(18)], 'quad_2': [x for x in range(18)], 'quad_3': [x for x in range(18)]}

SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
EXP_DIR = os.path.join(SAVE_PATH, EXP_NAME)
OD_CAL_PATH = os.path.join(SAVE_PATH, 'od_cal.json')
TEMP_CAL_PATH = os.path.join(SAVE_PATH, 'temp_cal.json')
PUMP_CAL_PATH = os.path.join(SAVE_PATH, 'pump_cal.json')
SYRINGE_PUMP_CAL_PATH = os.path.join(SAVE_PATH, 'syringe_pump_cal.json')
PUMP_SETTINGS_PATH = os.path.join(SAVE_PATH, 'pump_settings.json')
JSON_PARAMS_FILE = os.path.join(SAVE_PATH, 'eVOLVER_parameters.json')

SIGMOID = 'sigmoid'
LINEAR = 'linear'
THREE_DIMENSION = '3d'

logger = logging.getLogger('eVOLVER')

paused = False

EVOLVER_NS = None

class EvolverNamespace(BaseNamespace):
    start_time = None
    use_blank = False
    OD_initial = None
    experiment_params = None
    ip_address = None
    base_url = None
    exp_dir = SAVE_PATH

    def on_connect(self, *args):
        print("Connected to eVOLVER as client")
        logger.info('connected to eVOLVER as client')

    def on_disconnect(self, *args):
        print("Disconected from eVOLVER as client")
        logger.info('disconnected to eVOLVER as client')

    def on_reconnect(self, *args):
        print("Reconnected to eVOLVER as client")
        logger.info("reconnected to eVOLVER as client")

    def on_broadcast(self, data):
        logger.info('Broadcast received')
        if 'dummy' in data:
            print('skipping, dpu received dummy broadcast')
            return
        elapsed_time = round((time.time() - self.start_time) / 3600, 4)
        logger.info('Elapsed time: %.4f hours' % elapsed_time)
        print("{0}: {1} Hours".format(EXP_NAME, elapsed_time))
        # are the calibrations in yet?
        if not self.check_for_calibrations():
            logger.warning('Calibration files still missing, skipping custom functions')
            return

        if not self.check_for_pump_settings():
            logger.warning('Pump settings still missing, skipping custom functions')
            return

        with open(OD_CAL_PATH) as f:
            od_cal = json.load(f)
        with open(TEMP_CAL_PATH) as f:
            temp_cal = json.load(f)

        # apply calibrations
        # update temperatures if needed
        data = self.transform_data(data, QUADS, od_cal, temp_cal)
        if data is None:
            logger.error('could not tranform raw data, skipping user-defined functions')
            return

        # should we "blank" the OD?
        if self.use_blank and self.OD_initial is None:
            logger.info('setting initial OD reading')
            self.OD_initial = np.array([[float(x) for x in quad] for quad in data['transformed']['od']])
        elif self.OD_initial is None:
            self.OD_initial = np.zeros(len(QUADS), len(QUADS['quad_0']))

        data['transformed']['od'] = np.array([[float(x) for x in quad] for quad in data['transformed']['od']])
        data['transformed']['od'] = np.subtract(data['transformed']['od'], self.OD_initial)
        #data['transformed']['od'] = (data['transformed']['od'] - self.OD_initial)

        # save data
        try:
            self.save_data(data['transformed']['od'], elapsed_time, QUADS, 'OD')
            self.save_data(data['transformed']['temp'], elapsed_time, QUADS, 'temp')

            for param in od_cal['params']:
                self.save_data(data['data'].get(param, []), elapsed_time, QUADS, param + '_raw')
            for param in temp_cal['params']:
                self.save_data(data['data'].get(param, []), elapsed_time, QUADS, param + '_raw')
        except OSError:
            logger.info("Broadcast received before experiment initialization - skipping custom function...")
            return

        # run custom functions
        test = True
        self.custom_functions(data, QUADS, elapsed_time, test)
        # save variables
        self.save_variables(self.start_time, self.OD_initial)

        # Restart logging for db/gdrive syncing
        logging.shutdown()
        logging.getLogger('eVOLVER')

    def on_activecalibrations(self, data):
        print('Calibrations recieved')
        logger.info('Calibrations recieved')
        for calibration in data:
            if calibration['calibrationType'] == 'od':
                file_path = OD_CAL_PATH
            elif calibration['calibrationType'] == 'temperature':
                file_path = TEMP_CAL_PATH
            elif calibration['calibrationType'] == 'pump':
                file_path = PUMP_CAL_PATH
            elif calibration['calibrationType'] == 'syringe_pump':
                file_path = SYRINGE_PUMP_CAL_PATH
            else:
                continue
            for fit in calibration['fits']:
                if fit['active']:
                    with open(file_path, 'w') as f:
                        json.dump(fit, f)
                    # Create raw data directories and files for params needed
                    for param in fit['params']:
                        for quad in QUADS:
                            current_quad = int(quad.split("_")[1])
                            if not os.path.isdir(os.path.join(EXP_DIR, quad, param + '_raw')) and (param != 'pump' or param!='syringe_pump'):
                                os.makedirs(os.path.join(EXP_DIR, quad, param + '_raw'))
                            for vial in QUADS[quad]:
                                exp_str = "Experiment: {0} quad-{1}_vial-{2}, {3}".format(EXP_NAME, current_quad, vial, time.strftime("%c"))
                                self._create_file(vial, quad, param + '_raw', defaults=[exp_str])
                        break

    def request_calibrations(self):
        logger.debug('requesting active calibrations')
        self.emit('getactivecal',
                  {}, namespace = '/dpu-evolver')

    def request_pump_settings(self):
        pump_settings = fluidic_client.get_pump_settings(self.base_url)
        with open(PUMP_SETTINGS_PATH, "w") as f:
            json.dump(pump_settings, f)

    def transform_data(self, data, quads, od_cal, temp_cal):
        od_data_2 = None
        if od_cal['type'] == THREE_DIMENSION:
            od_data_2 = data['data'].get(od_cal['params'][1], None)

        #OD data formatting from left/right to quad/vial
        od_data_left = [[],[],[],[]]
        od_data_right = [[],[],[],[]]
        vial_indexes = [[0,1,2,3,4,5,6,7,8],[9,10,11,12,13,14,15,16,17],[18,19,20,21,22,23,24,25,26],[27,28,29,30,31,32,33,34,35]]
        for group in range(len(vial_indexes)):
            od_data_left[group] = [data['data'].get('od_90_left', None)[i] for i in vial_indexes[group]]
            od_data_right[group] = [data['data'].get('od_90_right', None)[i] for i in vial_indexes[group]]

        od_data = [[],[],[],[]]
        for quad in range(len(od_data)):
            od_data[quad].extend([float(od_data_left[quad][0]), float(od_data_left[quad][1]), float(od_data_left[quad][2]), float(od_data_right[quad][0]), float(od_data_right[quad][1]), float(od_data_right[quad][2])]);
            od_data[quad].extend([float(od_data_left[quad][3]), float(od_data_left[quad][4]), float(od_data_left[quad][5]), float(od_data_right[quad][3]), float(od_data_right[quad][4]), float(od_data_right[quad][5])]);
            od_data[quad].extend([float(od_data_left[quad][6]), float(od_data_left[quad][7]), float(od_data_left[quad][8]), float(od_data_right[quad][6]), float(od_data_right[quad][7]), float(od_data_right[quad][8])]);

        temp_data = data['data'].get(temp_cal['params'][0], None)
        set_temp_data = data['config'].get('temp', {}).get('value', None)

        if od_data is None or temp_data is None or set_temp_data is None:
            print('Incomplete data recieved, Error with measurement')
            logger.error('Incomplete data received, error with measurements')
            return None
        if 'NaN' in od_data or 'NaN' in temp_data or 'NaN' in set_temp_data:
            print('NaN recieved, Error with measurement')
            logger.error('NaN received, error with measurements')
            return None

        #od_data = np.array([float(x) for x in od_data])
        #if od_data_2:
            #od_data_2 = np.array([float(x) for x in od_data_2])
        for x in range(len(temp_data)):
            quad_key = 'quad_{0}'.format(x)
            temp_data[x] = [float(temp_data[x])] * len(quads[quad_key])
            set_temp_data[x] = [float(set_temp_data[x])] * len(quads[quad_key])
        temp_data = np.array(temp_data)
        set_temp_data = np.array(set_temp_data)
        temps = [[], [], [], []]
        for quad in range(len(quads)):
            temp_coefficients = temp_cal['coefficients'][quad]
            quad_key = 'quad_{0}'.format(quad)
            for vial in quads[quad_key]:
                file_name =  "quad-{0}_vial-{1}_temp_config.txt".format(quad,vial)
                file_path = os.path.join(EXP_DIR, quad_key, 'temp_config', file_name)
                temp_set_data = np.genfromtxt(file_path, delimiter=',')
                temp_set = temp_set_data[len(temp_set_data)-1][1]
                temps[quad].append(temp_set)
                od_coefficients = od_cal['coefficients'][quad][vial]
                try:
                    if od_cal['type'] == SIGMOID:
                        #convert raw photodiode data into ODdata using calibration curve
                        od_data[quad][vial] = np.real(od_coefficients[2] -
                                            ((np.log10((od_coefficients[1] -
                                                        od_coefficients[0]) /
                                                        (float(od_data[quad][vial]) -
                                                        od_coefficients[0])-1)) /
                                                        od_coefficients[3]))
                        if not np.isfinite(od_data[quad][vial]):
                            od_data[quad][vial] = 'NaN'
                            logger.debug('OD from quad %d vial %d: %s' % (quad, vial, od_data[quad][vial]))
                        else:
                            logger.debug('OD from quad %d vial %d: %.3f' % (quad, vial, od_data[quad][vial]))
                    elif od_cal['type'] == THREE_DIMENSION:
                        od_data[quad][vial] = np.real(od_coefficients[0] +
                                            (od_coefficients[1]*od_data[x]) +
                                            (od_coefficients[2]*od_data_2[x]) +
                                            (od_coefficients[3]*(od_data[x]**2)) +
                                            (od_coefficients[4]*od_data[x]*od_data_2[x]) +
                                            (od_coefficients[5]*(od_data_2[x]**2)))
                    else:
                        logger.error('OD calibration not of supported type!')
                        od_data[quad][vial] = 'NaN'
                except ValueError:
                    print("OD Read Error")
                    logger.error('OD read error for vial %d, setting to NaN' % x)
                    od_data[quad][vial] = 'NaN'
                try:
                    temp_data[quad][vial] = (float(temp_data[quad][vial]) * temp_coefficients[0]) + temp_coefficients[1]
                    logger.debug('temperature from quad_%d vial_%d: %.3f' % (quad, vial, temp_data[quad][vial]))
                except ValueError:
                    print("Temp Read Error")
                    logger.error('temperature read error for quad_%d vial_%d, setting to NaN' % (quad, vial))
                    temp_data[quad][vial]  = 'NaN'
                try:
                    set_temp_data[quad][vial] = (float(set_temp_data[quad][vial]) * temp_coefficients[0]) + temp_coefficients[1]
                    logger.debug('set_temperature from quad_%d vial_%d: %.3f' % (quad, vial, set_temp_data[quad][vial]))
                except ValueError:
                    print("Set Temp Read Error")
                    logger.error('set temperature read error for quad_%d vial_%d, setting to NaN' % (quad, vial))
                    set_temp_data[quad][vial]  = 'NaN'

        temps = np.array(temps)
        # update temperatures only if difference with expected
        # value is above 0.2 degrees celsius
        delta_t = np.abs(set_temp_data - temps).max()
        if delta_t > 0.2:
            logger.info('updating temperatures (max. deltaT is %.2f)' % delta_t)
            coefficients = temp_cal['coefficients']
            raw_temperatures = [None] * len(quads)
            for quad in range(len(quads)):
                raw_temperatures[quad] = str(int((temps[quad][0] - temp_cal['coefficients'][x][1]) / temp_cal['coefficients'][x][0]))
            self.update_temperature(raw_temperatures)
        else:
            # config from server agrees with local config
            # report if actual temperature doesn't match
            delta_t = np.abs(temps - temp_data).max()
            if delta_t > 0.2:
                logger.debug('actual temperature doesn\'t match configuration (yet? max deltaT is %.2f)' % delta_t)
                logger.debug('temperature config: %s' % temps)
                logger.debug('actual temperatures: %s' % temp_data)

        # add a new field in the data dictionary
        data['transformed'] = {}
        data['transformed']['od'] = od_data
        data['transformed']['temp'] = temp_data
        return data

    def update_stir_rate(self, stir_rates, immediate = False):
        data = {'param': 'stir', 'value': stir_rates,
                'immediate': immediate, 'recurring': True}
        logger.debug('stir rate command: %s' % data)
        self.emit('command', data, namespace = '/dpu-evolver')

    def update_temperature(self, temperatures, immediate = False):
        data = {'param': 'temp', 'value': temperatures,
                'immediate': immediate, 'recurring': True}
        logger.debug('temperature command: %s' % data)
        self.emit('command', data, namespace = '/dpu-evolver')

    def fluid_command(self, MESSAGE):
        logger.debug('fluid command: %s' % MESSAGE)
        command = {'param': 'pump', 'value': MESSAGE,
                   'recurring': False ,'immediate': True}
        self.emit('command', command, namespace='/dpu-evolver')

    def ipp_command(self, addr, vial, rate):
        #self.stop_all_pumps(regular = False, ipp = False)
        time.sleep(2)
        message = ['--'] * 48
        message[addr] = "{0}|{1}|{2}".format(rate, 1, 1)
        message[addr+1] = "{0}|{1}|{2}".format(rate, 1, 2)
        message[addr+2] = "{0}|{1}|{2}".format(rate, 1, 3)
        self.fluid_command(message)
        time.sleep(2)
        message = ['--'] * 48
        if vial == 'all':
            for addr in IPP_SELECT_ADDRS:
                message[addr] = 60
        else:
            message[IPP_SELECT_ADDRS[int(vial)]] = 40
        self.fluid_command(message)

    def arm_fluid_command(self, MESSAGE, active_quads):
        logger.debug('arm fluid command')
        command = {'pump_commands': MESSAGE, 'recurring': False, 'active_quads':active_quads}
        #fluidic_client.influx(base_url, command, active_quads)

    def update_chemo(self, data, vials, bolus_in_s, period_config, immediate = False):
        current_pump = data['config']['pump']['value']

        MESSAGE = {'fields_expected_incoming': 49,
                   'fields_expected_outgoing': 49,
                   'recurring': True,
                   'immediate': immediate,
                   'value': ['--'] * 48,
                   'param': 'pump'}

        for x in vials:
            # stop pumps if period is zero
            if period_config[x] == 0:
                # influx
                MESSAGE['value'][x] = '0|0'
                # efflux
                MESSAGE['value'][x + 16] = '0|0'
            else:
                # influx
                MESSAGE['value'][x] = '%.2f|%d' % (bolus_in_s[x], period_config[x])
                # efflux
                MESSAGE['value'][x + 16] = '%.2f|%d' % (bolus_in_s[x] * 2,
                                                        period_config[x])

        if MESSAGE['value'] != current_pump:
            logger.info('updating chemostat: %s' % MESSAGE)
            self.emit('command', MESSAGE, namespace = '/dpu-evolver')

    def stop_all_pumps(self, ):
        data = {'param': 'pump',
                'value': ['0'] * 48,
                'recurring': False,
                'immediate': True}
        logger.info('stopping all pumps')
        self.emit('command', data, namespace = '/dpu-evolver')

    def _create_file(self, vial, quad, param, directory=None, defaults=None):
        if defaults is None:
            defaults = []
        if directory is None:
            directory = param
        current_quad = int(quad.split("_")[1])
        file_name =  "quad-{0}_vial-{1}_{2}.txt".format(current_quad, vial, param)
        file_path = os.path.join(EXP_DIR, quad, directory, file_name)
        text_file = open(file_path, "w")
        for default in defaults:
            text_file.write(default + '\n')
        text_file.close()

    def initialize_exp(self, quads, experiment_params, log_name, quiet, verbose, ip_address, always_yes = False):
        self.ip_address = ip_address
        self.experiment_params = experiment_params
        self.base_url = "http://" + self.ip_address + ":" + str(XARM_PORT)
        logger.info('initializing experiment')

        if os.path.exists(EXP_DIR):
            setup_logging(log_name, quiet, verbose)
            logger.info('found an existing experiment')
            exp_continue = None
            if always_yes:
                exp_continue = 'y'
            else:
                while exp_continue not in ['y', 'n']:
                    exp_continue = input('Continue from existing experiment? (y/n): ')
        else:
            exp_continue = 'n'

        if exp_continue == 'n':
            if os.path.exists(EXP_DIR):
                exp_overwrite = None
                if always_yes:
                    exp_overwrite = 'y'
                else:
                    while exp_overwrite not in ['y', 'n']:
                        exp_overwrite = input('Directory aleady exists. '
                                            'Overwrite with new experiment? (y/n): ')
                logger.info('data directory already exists')
                if exp_overwrite == 'y':
                    logger.info('deleting existing data directory')
                    shutil.rmtree(EXP_DIR)
                else:
                    print('Change experiment name in custom_script.py '
                        'and then restart...')
                    logger.warning('not deleting existing data directory, exiting')
                    sys.exit(1)

            start_time = time.time()

            self.request_calibrations()
            self.request_pump_settings()

            logger.debug('creating data directories')
            for quad in quads:
                current_quad = int(quad.split("_")[1])
                os.makedirs(os.path.join(EXP_DIR, quad, 'OD'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'temp'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'temp_config'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'pump_log'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'syringe-pump_log'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'ODset'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'growthrate'))
                os.makedirs(os.path.join(EXP_DIR, quad, 'chemo_config'))
                for vial in quads[quad]:
                    exp_str = "Experiment: {0} quad-{1}_vial-{2}, {3}".format(EXP_NAME, quad, vial, time.strftime("%c"))
                    # make OD file
                    self._create_file(vial, quad, 'OD', defaults=[exp_str])
                    # make temperature data file
                    self._create_file(vial, quad, 'temp')
                    # make temperature configuration file
                    self._create_file(vial, quad, 'temp_config', defaults=[exp_str, "0,{0}".format(TEMP_INITIAL_HT[current_quad])])
                    # make pump log file
                    self._create_file(vial, quad, 'pump_log', defaults=[exp_str, "0,0"])
                    # make syringe pump log file
                    self._create_file(vial, quad, 'syringe-pump_log', defaults=[exp_str, "0,0"])
                    # make ODset file
                    self._create_file(vial, quad, 'ODset', defaults=[exp_str, "0,0"])
                    # make growth rate file
                    self._create_file(vial, quad, 'gr', defaults=[exp_str, "0,0"], directory='growthrate')
                    # make chemostat file
                    self._create_file(vial, quad, 'chemo_config', defaults=["0,0,0", "0,0,0"], directory='chemo_config')

            stir_rate = STIR_INITIAL_HT
            temp_values = TEMP_INITIAL_HT
            if self.experiment_params:
                stir_rate = list(map(lambda x: x['stir'], self.experiment_params['vial_configuration']))
                temp_values = list(map(lambda x: x['temp'], self.experiment_params['vial_configuration']))
            self.update_stir_rate(stir_rate)
            self.update_temperature(temp_values)

            if always_yes:
                exp_blank = 'y'
            else:
                exp_blank = input('Calibrate vials to blank? (y/n): ')
            if exp_blank == 'y':
                # will do it with first broadcast
                self.use_blank = True
                logger.info('will use initial OD measurement as blank')
            else:
                self.use_blank = False
                self.OD_initial = np.zeros((len(quads), 18))
        else:
            # load existing experiment
            pickle_name =  "{0}.pickle".format(EXP_NAME)
            pickle_path = os.path.join(EXP_DIR, pickle_name)
            logger.info('loading previous experiment data: %s' % pickle_path)
            with open(pickle_path, 'rb') as f:
                loaded_var  = pickle.load(f)
            x = loaded_var
            start_time = x[0]
            self.OD_initial = x[1]

        # copy current custom script to txt file
        backup_filename = '{0}_{1}.txt'.format(EXP_NAME,
                                            time.strftime('%y%m%d_%H%M'))
        shutil.copy(os.path.join(SAVE_PATH, 'custom_script.py'), os.path.join(EXP_DIR,
                                                    backup_filename))
        logger.info('saved a copy of current custom_script.py as %s' %
                    backup_filename)

        return start_time

    def check_for_calibrations(self):
        result = True
        if not os.path.exists(OD_CAL_PATH) or not os.path.exists(TEMP_CAL_PATH) or not os.path.exists(PUMP_CAL_PATH) or not os.path.exists(SYRINGE_PUMP_CAL_PATH):
            # log and request again
            logger.warning('Calibrations not received yet, requesting again')
            self.request_calibrations()
            result = False
        return result

    def check_for_pump_settings(self):
        result = True
        if not os.path.exists(PUMP_SETTINGS_PATH):
            # log and request again
            logger.warning('Pump settings not received yet, requesting again')
            self.request_pump_settings()
            result = False
        return result


    def save_data(self, data, elapsed_time, quads, parameter):
        if len(data) == 0:
            return
        for quad in quads:
            current_quad = int(quad.split("_")[1])
            for vial in quads[quad]:
                file_name =  "quad-{0}_vial-{1}_{2}.txt".format(current_quad, vial, parameter)
                file_path = os.path.join(EXP_DIR, quad, parameter, file_name)
                text_file = open(file_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time, data[current_quad][vial]))
                text_file.close()

    def save_variables(self, start_time, OD_initial):
        # save variables needed for restarting experiment later
        save_path = os.path.dirname(os.path.realpath(__file__))
        pickle_name = "{0}.pickle".format(EXP_NAME)
        pickle_path = os.path.join(EXP_DIR, pickle_name)
        logger.debug('saving all variables: %s' % pickle_path)
        with open(pickle_path, 'wb') as f:
            pickle.dump([start_time, OD_initial], f)

    def get_step_rate(self):
        syringe_pump_cal = None
        with open(SYRINGE_PUMP_CAL_PATH) as f:
            syringe_pump_cal = json.load(f)
        return syringe_pump_cal['coefficients']

    def get_pump_settings(self):
        pump_settings = None
        with open(PUMP_SETTINGS_PATH) as f:
            pump_settings = json.load(f)
        return pump_settings

    def calc_growth_rate(self, vial, gr_start, elapsed_time):
        ODfile_name =  "vial{0}_OD.txt".format(vial)
        # Grab Data and make setpoint
        OD_path = os.path.join(EXP_DIR, 'OD', ODfile_name)
        OD_data = np.genfromtxt(OD_path, delimiter=',')
        raw_time = OD_data[:, 0]
        raw_OD = OD_data[:, 1]
        raw_time = raw_time[np.isfinite(raw_OD)]
        raw_OD = raw_OD[np.isfinite(raw_OD)]

        # Trim points prior to gr_start
        trim_time = raw_time[np.nonzero(np.where(raw_time > gr_start, 1, 0))]
        trim_OD = raw_OD[np.nonzero(np.where(raw_time > gr_start, 1, 0))]

        # Take natural log, calculate slope
        log_OD = np.log(trim_OD)
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            trim_time[np.isfinite(log_OD)],
            log_OD[np.isfinite(log_OD)])
        logger.debug('growth rate for vial %s: %.2f' % (vial, slope))

        # Save slope to file
        file_name =  "vial{0}_gr.txt".format(vial)
        gr_path = os.path.join(EXP_DIR, 'growthrate', file_name)
        text_file = open(gr_path, "a+")
        text_file.write("{0},{1}\n".format(elapsed_time, slope))
        text_file.close()

    def tail_to_np(self, path, window=10, BUFFER_SIZE=512):
        """
        Reads file from the end and returns a numpy array with the data of the last 'window' lines.
        Alternative to np.genfromtxt(path) by loading only the needed lines instead of the whole file.
        """
        f = open(path, 'rb')
        if window == 0:
            return []

        f.seek(0, os.SEEK_END)
        remaining_bytes = f.tell()
        size = window + 1  # Read one more line to avoid broken lines
        block = -1
        data = []

        while size > 0 and remaining_bytes > 0:
            if remaining_bytes - BUFFER_SIZE > 0:
                # Seek back one whole BUFFER_SIZE
                f.seek(block * BUFFER_SIZE, os.SEEK_END)
                # read BUFFER
                bunch = f.read(BUFFER_SIZE)
            else:
                # file too small, start from beginning
                f.seek(0, 0)
                # only read what was not read
                bunch = f.read(remaining_bytes)

            bunch = bunch.decode('utf-8')
            data.append(bunch)
            size -= bunch.count('\n')
            remaining_bytes -= BUFFER_SIZE
            block -= 1

        data = ''.join(reversed(data)).splitlines()[-window:]

        if len(data) < window:
            # Not enough data
            return np.asarray([])

        for c, v in enumerate(data):
            data[c] = v.split(',')

        try:
            data = np.asarray(data, dtype=np.float64)
            return data
        except ValueError:
            # It is reading the header
            return np.asarray([])

    def custom_functions(self, data, vials, elapsed_time, test):
        # load user script from custom_script.py
        mode = self.experiment_params['function'] if self.experiment_params else OPERATION_MODE
        if mode == 'turbidostat':
            custom_script.turbidostat(self, data, vials, elapsed_time)
        elif mode == 'chemostat':
            custom_script.chemostat(self, data, vials, elapsed_time)
        elif mode == 'growthcurve':
            custom_script.growth_curve(self, data, vials, elapsed_time)
        else:
            # try to load the user function
            # if failing report to user
            logger.info('user-defined operation mode %s' % mode)
            try:
                func = getattr(custom_script, mode)
                func(self, data, vials, elapsed_time, test)
            except AttributeError:
                logger.error('could not find function %s in custom_script.py' %
                            mode)
                print('Could not find function %s in custom_script.py '
                    '- Skipping user defined functions'%
                    mode)

    def stop_exp(self):
        self.stop_all_pumps()

def setup_logging(filename, quiet, verbose):
    if quiet:
        logging.basicConfig(level=logging.CRITICAL + 10)
    else:
        if verbose == 0:
            level = logging.INFO
        elif verbose >= 1:
            level = logging.DEBUG
        logging.basicConfig(format='%(asctime)s - %(name)s - [%(levelname)s] '
                            '- %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            filename=filename,
                            level=level)

def get_options():
    description = 'Run an eVOLVER experiment from the command line'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-y', '--always-yes', action='store_true',
                        default=False,
                        help='Answer yes to all questions '
                             '(i.e. continues from existing experiment, '
                             'overwrites existing data and blanks OD '
                             'measurements)')
    parser.add_argument('-l', '--log-name',
                        default=os.path.join(EXP_DIR, 'evolver.log'),
                        help='Log file name directory (default: %(default)s)')
    parser.add_argument('-i', '--ip-address', action='store', dest='ip_address',
                        help='IP address of eVOLVER to run experiment on.')

    log_nolog = parser.add_mutually_exclusive_group()
    log_nolog.add_argument('-v', '--verbose', action='count',
                           default=0,
                           help='Increase logging verbosity level to DEBUG '
                                '(default: INFO)')
    log_nolog.add_argument('-q', '--quiet', action='store_true',
                           default=False,
                           help='Disable logging to file entirely')
    return parser.parse_args(), parser

if __name__ == '__main__':
    options, parser = get_options()


    #changes terminal tab title in OSX
    print('\x1B]0;eVOLVER EXPERIMENT: PRESS Ctrl-C TO PAUSE\x07')

    experiment_params = None
    if os.path.exists(JSON_PARAMS_FILE):
        with open(JSON_PARAMS_FILE) as f:
            experiment_params = json.load(f)
    evolver_ip = experiment_params['ip'] if experiment_params is not None else options.ip_address
    if evolver_ip is None:
        logger.error('No IP address found. Please provide on the command line or through the GUI.')
        parser.print_help()
        sys.exit(2)

    socketIO = SocketIO(evolver_ip, EVOLVER_PORT)
    EVOLVER_NS = socketIO.define(EvolverNamespace, '/dpu-evolver')

    # start by stopping any existing chemostat
    EVOLVER_NS.stop_all_pumps()
    #
    EVOLVER_NS.start_time = EVOLVER_NS.initialize_exp(QUADS,
                                                      experiment_params,
                                                      options.log_name,
                                                      options.quiet,
                                                      options.verbose,
                                                      evolver_ip,
                                                      options.always_yes
                                                      )

    # Using a non-blocking stream reader to be able to listen
    # for commands from the electron app.
    nbsr = NBSR(sys.stdin)
    paused = False

    # logging setup

    reset_connection_timer = time.time()
    while True:
        try:
            # infinite loop

            # check if a message has come in from the DPU
            message = nbsr.readline()
            if 'stop-script' in message:
                logger.info('Stop message received - halting all pumps');
                EVOLVER_NS.stop_exp()
                socketIO.disconnect()
            if 'pause-script' in message:
                print('Pausing experiment', flush = True)
                logger.info('Pausing experiment in dpu')
                paused = True
                EVOLVER_NS.stop_exp()
                socketIO.disconnect()

            if 'continue-script' in message:
                print('Restarting experiment', flush = True)
                logger.info('Restarting experiment')
                paused = False
                socketIO.connect()

            if not paused:
                    socketIO.wait(seconds=0.1)
                    if time.time() - reset_connection_timer > 3600 and not paused:
                        # reset connection to avoid buildup of broadcast
                        # messages (unlikely but could happen for very long
                        # experiments with slow dpu code/computer)
                        logger.info('resetting connection to eVOLVER to avoid '
                                    'potential buildup of broadcast messages')
                        socketIO.disconnect()
                        socketIO.connect()
                        reset_connection_timer = time.time()
        except KeyboardInterrupt:
            try:
                print('Ctrl-C detected, pausing experiment')
                logger.warning('interrupt received, pausing experiment')
                EVOLVER_NS.stop_exp()
                # stop receiving broadcasts
                socketIO.disconnect()
                while True:
                    key = input('Experiment paused. Press enter key to restart '
                                ' or hit Ctrl-C again to terminate experiment')
                    logger.warning('resuming experiment')
                    # no need to have something like "restart_chemo" here
                    # with the new server logic
                    socketIO.connect()
                    break
            except KeyboardInterrupt:
                print('Second Ctrl-C detected, shutting down')
                logger.warning('second interrupt received, terminating '
                                'experiment')
                EVOLVER_NS.stop_exp()
                print('Experiment stopped, goodbye!')
                logger.warning('experiment stopped, goodbye!')
                break
        except Exception as e:
            logger.critical('exception %s stopped the experiment' % str(e))
            print('error "%s" stopped the experiment' % str(e))
            traceback.print_exc(file=sys.stdout)
            EVOLVER_NS.stop_exp()
            print('Experiment stopped, goodbye!')
            logger.warning('experiment stopped, goodbye!')
            break

    # stop experiment one last time
    # covers corner case where user presses Ctrl-C twice quickly
    socketIO.connect()
    EVOLVER_NS.stop_exp()
