#!/usr/bin/env python3

import numpy as np
import logging
import os.path


# logger setup
logger = logging.getLogger(__name__)

##### USER DEFINED GENERAL SETTINGS #####

# If using the GUI for data visualization, do not change EXP_NAME!
# only change if you wish to have multiple data folders within a single
# directory for a set of scripts
EXP_NAME = 'test_expt'

# Port for the eVOLVER connection. You should not need to change this unless you have multiple applications on a single RPi.
EVOLVER_PORT = 8081

##### Identify pump calibration files, define initial values for temperature, stirring, volume, power settings

TEMP_INITIAL = [30] * 16 #degrees C, makes 16-value list
TEMP_INITIAL_HT = [30] * 4 #degrees C, makes 4-value list
#Alternatively enter 16-value list to set different values
#TEMP_INITIAL = [30,30,30,30,32,32,32,32,34,34,34,34,36,36,36,36]
#TEMP_INITIAL_HT = [30,20,30,10]

STIR_INITIAL = [8] * 16 #try 8,10,12 etc; makes 16-value list
STIR_INITIAL_HT = [0] * 4 #try 20-75 etc; makes 4-value list
#Alternatively enter 16-value list to set different values
#STIR_INITIAL = [7,7,7,7,8,8,8,8,9,9,9,9,10,10,10,10]
#STIR_INITIAL_HT = [30,50,40,50]

VOLUME =  25 #mL, determined by vial cap straw length
VOLUME_HT = 5 #mL, determined by efflux needle length

OPERATION_MODE = 'turbidostat_HT' #use to choose between 'turbidostat', 'chemostat', 'ht_turbidostat', or 'ht_chemostat'
# if using a different mode, name your function as the OPERATION_MODE variable

def media_transform(volumes, pump_settings, step_rates, test):
    """ Convert influx volumes to pump motor steps for vial dilutions. Information will be stored in an read accessible JSON file """
    dilutions = {}

    # scan through fluid command and convert dilution volumes to stepper motor steps based on volume --> steps calibration
    for pump in volumes:
        pump_json = {}
        pump_id = pump_settings['pumps'][pump]['id']
        smoothie_id = pump_settings['pumps'][pump]['smoothie']

        for quad in range(len(volumes[pump])):
            quad_name = 'quad_{0}'.format(quad)
            pump_json[quad_name] = {}

            for vial in range(18):
                vial_name = 'vial_{0}'.format(vial)
                if test:
                    pump_json[quad_name][vial_name] = 0 # used for debugging fluidics
                else:
                    pump_json[quad_name][vial_name] = volumes[pump][quad][vial] * step_rates[smoothie_id][pump_id] # convert volume command to syringe pump motor steps
        dilutions[pump] = pump_json

    # save dilutiion steps to JSON
    #dilutions_path = os.path.join(DILUTIONS_PATH, 'dilutions.json')
    #with open(dilutions_path, 'w') as f:
    #    json.dump(dilutions, f)
    #return dilutions

def hz_to_rate(hz, c, b):
    return c * math.pow(hz, b)

def rate_to_hz(rate, c, b):
    """ rate should be in ml/h """
    return math.pow(((rate) / c), 1.0/b)

def ipp_calculations(elapsed_time, eVOLVER):

    # arabinose stock concentration is at 250 mM
    # Solenoid addresses for each ipp.
    # Each pump requires 3 addresses. These vars capture the 1st of the three (sequential)
    v2v_addr = 32
    ipp_min_waiting_time = 4

    # Sets the minimum amount of time that the experiment must run
    # before the IPP selection scheme will start
    bolus_amount = .4 # ml
    bolus_rate = 10
    bolus_time = bolus_amount / hz_to_rate(10, c[0], b[0])

    turnover_time = 1 # hours
    init_rate = .08
    start_rate = 0.04 # V/h

    # Start ipp protocol
    if (elapsed_time > ipp_min_waiting_time):
        if (elapsed_time < ipp_min_waiting_time + bolus_time):
            # Start bolus
            print("ipp bolus")
            rate = bolus_rate
            vial = 'all'
        else:
            rate = rate_to_hz(start_rate * LAGOON_VOLUME, c[0], b[0])
            vial = 'all'

        print("running ipp cmd. addr: {0}, vial: {1}, rate: {2}".format(v2v_addr, vial, round(rate,3)))
        eVOLVER.ipp_command(v2v_addr, vial, round(rate,3))

##### END OF USER DEFINED GENERAL SETTINGS #####

def growth_curve(eVOLVER, input_data, vials, elapsed_time):
    return

def turbidostat(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####

    turbidostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    stop_after_n_curves = np.inf #set to np.inf to never stop, or integer value to stop diluting after certain number of growth curves
    OD_values_to_average = 6  # Number of values to calculate the OD average

    lower_thresh = [0.2] * len(vials) #to set all vials to the same value, creates 16-value list
    upper_thresh = [0.4] * len(vials) #to set all vials to the same value, creates 16-value list

    if eVOLVER.experiment_params is not None:
        lower_thresh = list(map(lambda x: x['lower'], eVOLVER.experiment_params['vial_configuration']))
        upper_thresh = list(map(lambda x: x['upper'], eVOLVER.experiment_params['vial_configuration']))

    #Alternatively, use 16 value list to set different thresholds, use 9999 for vials not being used
    #lower_thresh = [0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]
    #upper_thresh = [0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]


    ##### END OF USER DEFINED VARIABLES #####


    ##### Turbidostat Settings #####
    #Tunable settings for overflow protection, pump scheduling etc. Unlikely to change between expts

    time_out = 5 #(sec) additional amount of time to run efflux pump
    pump_wait = 3 # (min) minimum amount of time to wait between pump events

    ##### End of Turbidostat Settings #####

    flow_rate = eVOLVER.get_flow_rate() #read from calibration file

    ##### Turbidostat Control Code Below #####

    # fluidic message: initialized so that no change is sent
    MESSAGE = ['--'] * 48
    for x in turbidostat_vials: #main loop through each vial

        # Update turbidostat configuration files for each vial
        # initialize OD and find OD path

        file_name =  "vial{0}_ODset.txt".format(x)
        ODset_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'ODset', file_name)
        data = np.genfromtxt(ODset_path, delimiter=',')
        ODset = data[len(data)-1][1]
        ODsettime = data[len(data)-1][0]
        num_curves=len(data)/2;

        file_name =  "vial{0}_OD.txt".format(x)
        OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD', file_name)
        data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)
        average_OD = 0

        # Determine whether turbidostat dilutions are needed
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window
        collecting_more_curves = (num_curves <= (stop_after_n_curves + 2)) #logical, checks to see if enough growth curves have happened

        if data.size != 0:
            # Take median to avoid outlier
            od_values_from_file = data[:,1]
            average_OD = float(np.median(od_values_from_file))

            #if recently exceeded upper threshold, note end of growth curve in ODset, allow dilutions to occur and growthrate to be measured
            if (average_OD > upper_thresh[x]) and (ODset != lower_thresh[x]):
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time,
                                                   lower_thresh[x]))
                text_file.close()
                ODset = lower_thresh[x]
                # calculate growth rate
                eVOLVER.calc_growth_rate(x, ODsettime, elapsed_time)

            #if have approx. reached lower threshold, note start of growth curve in ODset
            if (average_OD < (lower_thresh[x] + (upper_thresh[x] - lower_thresh[x]) / 3)) and (ODset != upper_thresh[x]):
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time, upper_thresh[x]))
                text_file.close()
                ODset = upper_thresh[x]

            #if need to dilute to lower threshold, then calculate amount of time to pump
            if average_OD > ODset and collecting_more_curves:

                time_in = - (np.log(lower_thresh[x]/average_OD)*VOLUME)/flow_rate[x]

                if time_in > 20:
                    time_in = 20

                time_in = round(time_in, 2)

                file_name =  "vial{0}_pump_log.txt".format(x)
                file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                         'pump_log', file_name)
                data = np.genfromtxt(file_path, delimiter=',')
                last_pump = data[len(data)-1][0]
                if ((elapsed_time - last_pump)*60) >= pump_wait: # if sufficient time since last pump, send command to Arduino
                    logger.info('turbidostat dilution for vial %d' % x)
                    # influx pump
                    MESSAGE[x] = str(time_in)
                    # efflux pump
                    MESSAGE[x + 16] = str(time_in + time_out)

                    file_name =  "vial{0}_pump_log.txt".format(x)
                    file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'pump_log', file_name)

                    text_file = open(file_path, "a+")
                    text_file.write("{0},{1}\n".format(elapsed_time, time_in))
                    text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

    # send fluidic command only if we are actually turning on any of the pumps
    #if MESSAGE != ['--'] * 48:
        #eVOLVER.fluid_command(MESSAGE)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    # end of turbidostat() fxn

def chemostat(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####
    start_OD = [0] * 16 # ~OD600, set to 0 to start chemostate dilutions at any positive OD
    start_time = [0] * 16 #hours, set 0 to start immediately
    # Note that script uses AND logic, so both start time and start OD must be surpassed

    OD_values_to_average = 6  # Number of values to calculate the OD average

    chemostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials

    rate_config = [0.5] * 16 #to set all vials to the same value, creates 16-value list
    stir = [8] * 16
    #UNITS of 1/hr, NOT mL/hr, rate = flowrate/volume, so dilution rate ~ growth rate, set to 0 for unused vials

    #Alternatively, use 16 value list to set different rates, use 0 for vials not being used
    #rate_config = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6]

    ##### END OF USER DEFINED VARIABLES #####

    if eVOLVER.experiment_params is not None:
        rate_config = list(map(lambda x: x['rate'], eVOLVER.experiment_params['vial_configuration']))
        stir = list(map(lambda x: x['stir'], eVOLVER.experiment_params['vial_configuration']))
        start_time= list(map(lambda x: x['startTime'], eVOLVER.experiment_params['vial_configuration']))
        start_OD= list(map(lambda x: x['startOD'], eVOLVER.experiment_params['vial_configuration']))

    ##### Chemostat Settings #####

    #Tunable settings for bolus, etc. Unlikely to change between expts
    bolus = 0.5 #mL, can be changed with great caution, 0.2 is absolute minimum

    ##### End of Chemostat Settings #####

    flow_rate = eVOLVER.get_flow_rate() #read from calibration file
    period_config = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array
    bolus_in_s = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array


    ##### Chemostat Control Code Below #####

    for x in chemostat_vials: #main loop through each vial

        # Update chemostat configuration files for each vial

        #initialize OD and find OD path
        file_name =  "vial{0}_OD.txt".format(x)
        OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD', file_name)
        data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)
        average_OD = 0
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window

        if data.size != 0: #waits for seven OD measurements (couple minutes) for sliding window

            #calculate median OD
            od_values_from_file = data[:,1]
            average_OD = float(np.median(od_values_from_file))

            # set chemostat config path and pull current state from file
            file_name =  "vial{0}_chemo_config.txt".format(x)
            chemoconfig_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                            'chemo_config', file_name)
            chemo_config = np.genfromtxt(chemoconfig_path, delimiter=',')
            last_chemoset = chemo_config[len(chemo_config)-1][0] #should t=0 initially, changes each time a new command is written to file
            last_chemophase = chemo_config[len(chemo_config)-1][1] #should be zero initially, changes each time a new command is written to file
            last_chemorate = chemo_config[len(chemo_config)-1][2] #should be 0 initially, then period in seconds after new commands are sent

            # once start time has passed and culture hits start OD, if no command has been written, write new chemostat command to file
            if ((elapsed_time > start_time[x]) and (average_OD > start_OD[x])):

                #calculate time needed to pump bolus for each pump
                bolus_in_s[x] = bolus/flow_rate[x]

                # calculate the period (i.e. frequency of dilution events) based on user specified growth rate and bolus size
                if rate_config[x] > 0:
                    period_config[x] = (3600*bolus)/((rate_config[x])*VOLUME) #scale dilution rate by bolus size and volume
                else: # if no dilutions needed, then just loops with no dilutions
                    period_config[x] = 0

                if  (last_chemorate != period_config[x]):
                    print('Chemostat updated in vial {0}'.format(x))
                    logger.info('chemostat initiated for vial %d, period %.2f'
                                % (x, period_config[x]))
                    # writes command to chemo_config file, for storage
                    text_file = open(chemoconfig_path, "a+")
                    text_file.write("{0},{1},{2}\n".format(elapsed_time,
                                                           (last_chemophase+1),
                                                           period_config[x])) #note that this changes chemophase
                    text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    eVOLVER.update_chemo(input_data, chemostat_vials, bolus_in_s, period_config) #compares computed chemostat config to the remote one
    # end of chemostat() fxn

# def your_function_here(): # good spot to define modular functions for dynamics or feedback
def turbidostat_HT(eVOLVER, input_data, quads, elapsed_time, test):
    OD_data = input_data['transformed']['od']
    ##### USER DEFINED VARIABLES #####

    turbidostat_vials = quads #vials is all 72, can set to different range (ex. [[0,1,2,3],[],[0,1,2,3],[0,1,2,3]]) to only trigger tstat on those vials
    turbidostat_pumps = ['base_media']
    stop_after_n_curves = np.inf #set to np.inf to never stop, or integer value to stop diluting after certain number of growth curves
    OD_values_to_average = 6  # Number of values to calculate the OD average

    active_quads = []
    for quad in quads:
        if quads[quad] != []:
            quad_count = quad.split('_')[1]
            active_quads.append(float(quad_count))

    lower_thresh = []
    upper_thresh = []
    for quad in quads:
        lower_thresh.append([0.2] * len(quad)) #to set all vials to the same value, creates 18-value list
        upper_thresh.append([0.4] * len(quad)) #to set all vials to the same value, creates 18-value list

    if eVOLVER.experiment_params is not None:
        for quad in eVOLVER.experiment_params['quad_configuration']:
            lower_thresh.append(list(map(lambda x: x['lower'], eVOLVER.experiment_params['quad_configuration'][quad])))
            upper_thresh.append(list(map(lambda x: x['upper'], eVOLVER.experiment_params['quad_configuration'][quad])))

    #Alternatively, use 4x18 array to set different thresholds, use 9999 for vials not being used
    #lower_thresh = [[0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]]
    #upper_thresh = [[0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999], [0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]]


    ##### END OF USER DEFINED VARIABLES #####


    ##### Turbidostat Settings #####
    #Tunable settings for overflow protection, pump scheduling etc. Unlikely to change between expts

    time_out = 5 #(sec) additional amount of time to run efflux pump
    pump_wait = 3 # (min) minimum amount of time to wait between pump events

    ##### End of Turbidostat Settings #####

    step_rates = eVOLVER.get_step_rate() #read from syringe pump calibration file
    pump_settings = eVOLVER.get_pump_settings()

    # Verify that user defined pumps match pump settings
    influx_volumes = {}
    for pump in turbidostat_pumps:
        influx_volumes[pump] = []
        if pump not in pump_settings['pumps']:
            logger.warning('desired pump not in pump settings')
            return
        else:
            continue

    ##### Turbidostat Control Code Below #####
    SYRINGE_PUMP_MESSAGE = []
    for quad in turbidostat_vials: #main loop through each vial
        for pump in influx_volumes:
            influx_volumes[pump].append([0] * 18)
        current_quad = quad.split('_')[1]
        for vial in turbidostat_vials[quad]:

            # Update turbidostat configuration files for each vial
            # initialize OD and find OD path

            file_name =  "quad-{0}_vial-{1}_ODset.txt".format(current_quad, vial)
            ODset_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, quad, 'ODset', file_name)
            data = np.genfromtxt(ODset_path, delimiter=',')
            ODset = data[len(data)-1][1]
            ODsettime = data[len(data)-1][0]
            num_curves=len(data)/2;

            file_name =  "quad-{0}_vial-{1}_OD.txt".format(current_quad, vial)
            OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, quad, 'OD', file_name)
            data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)
            average_OD = 0

            # Determine whether turbidostat dilutions are needed
            #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window
            collecting_more_curves = (num_curves <= (stop_after_n_curves + 2)) #logical, checks to see if enough growth curves have happened

            if data.size != 0:
                # Take median to avoid outlier
                od_values_from_file = data[:,1]
                average_OD = float(np.median(od_values_from_file))

                #if recently exceeded upper threshold, note end of growth curve in ODset, allow dilutions to occur and growthrate to be measured
                if (average_OD > upper_thresh[current_quad][vial]) and (ODset != lower_thresh[current_quad][vial]):
                    text_file = open(ODset_path, "a+")
                    text_file.write("{0},{1}\n".format(elapsed_time,lower_thresh[current_quad][vial]))
                    text_file.close()
                    ODset = lower_thresh[current_quad][vial]
                    # calculate growth rate
                    eVOLVER.calc_growth_rate(x, ODsettime, elapsed_time)

                #if have approx. reached lower threshold, note start of growth curve in ODset
                if (average_OD < (lower_thresh[current_quad][vial] + (upper_thresh[current_quad][vial] - lower_thresh[current_quad][vial]) / 3)) and (ODset != upper_thresh[current_quad][vial]):
                    text_file = open(ODset_path, "a+")
                    text_file.write("{0},{1}\n".format(elapsed_time, upper_thresh[current_quad][vial]))
                    text_file.close()
                    ODset = upper_thresh[current_quad][vial]

                #if need to dilute to lower threshold, then calculate amount of time to pump
                if average_OD > ODset and collecting_more_curves:

                    volume_in = - (np.log(lower_thresh[current_quad][vial]/average_OD)*VOLUME)

                    file_name =  "quad-{0}_vial-{0}_syringe-pump_log.txt".format(current_quad,vial)
                    file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, quad, 'syringe-pump_log', file_name)
                    data = np.genfromtxt(file_path, delimiter=',')
                    last_pump = data[len(data)-1][0]
                    if ((elapsed_time - last_pump)*60) >= pump_wait: # if sufficient time since last pump, send command to Arduino
                        logger.info('turbidostat dilution for quad {0} vial {1}'.format(current_quad, vial))
                        # influx pump
                        influx_volumes['base_media'][current_quad][vial] = volume_in
                        text_file = open(file_path, "a+")
                        text_file.write("{0},{1}\n".format(elapsed_time, volume_in))
                        text_file.close()
            else:
                logger.debug('not enough OD measurements for quad {0} vial{1}'.format(current_quad, vial))

    SYRINGE_PUMP_MESSAGE = media_transform(influx_volumes, pump_settings, step_rates, test)
    # send fluidic command only if we are actually turning on any of the pumps
    if SYRINGE_PUMP_MESSAGE != []:
        eVOLVER.arm_fluid_command(SYRINGE_PUMP_MESSAGE, active_quads)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    # end of turbidostat() fxn

if __name__ == '__main__':
    print('Please run eVOLVER.py instead')
    logger.info('Please run eVOLVER.py instead')
