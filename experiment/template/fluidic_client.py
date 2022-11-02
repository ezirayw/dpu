import requests, time, sys, os, json, yaml, asyncio

# Load config and calibration files
client_path = os.path.dirname(os.path.realpath(__file__))
print(client_path)
config_path = os.path.join(client_path, 'config', 'client_conf.yml')
calibration_path = os.path.join(client_path, 'config', 'calibrations.json')

f1 = open(calibration_path)
calibration = json.load(f1)
f1.close()

with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

IP = config["rpi_ip"]
PORT = config["server_port"]
URL = "http://" + IP + ":" + str(PORT)
print(URL)

def flask_request(url,payload):
    try:
        headers = config["headers"]
        response = requests.request("POST", url, json=payload, headers=headers)
        print(response.text)
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
        sys.exit()
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        sys.exit()
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
        sys.exit()
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        print(response.text)
        sys.exit()

def arm_test():
    url = URL + "/arm_test"
    payload = {}
    flask_request(url, payload)

def move_to_quad(quad):
    url = URL + "/move_to_quad"
    payload = {"quad": quad}
    flask_request(url, payload)

def set_arm():
    url = URL + "/set_arm"
    payload = {}
    flask_request(url, payload)

def reset_arm():
    url = URL + "/reset_arm"
    payload = {}
    flask_request(url, payload)

def fill_tubing():
    url = URL + "/fill_tubing"
    payload = {}
    flask_request(url, payload)

def prime_pumps():
    url = URL + "/prime_pump"
    payload = {}
    flask_request(url, payload)

def influx(fluid_command, quads, test):
    url = URL + "/influx"
    payload = {"fluid_command": fluid_command, "quads": quads, "test": test}
    flask_request(url, payload)

if __name__ == '__main__':
    check_fill_tubing = input("Is the tubing filled with desired fluid? Enter y/n: ")
    if check_fill_tubing == 'y':
        check_pump_calibration = input("Is the pump calibrated? Enter y/n: ")
        if check_pump_calibration == 'y':
            print("Robotic arm ready to handle eVOLVER fluidic functions")

    if check_fill_tubing == 'n':
        not_filled = True
        while not_filled:
            fill_cycles = input("Enter number of fill cycles to run: ")
            fill_cycles = int(fill_cycles)
            print("Running {0} number of fill tubing cycles".format(fill_cycles))
            for cycle in range(fill_cycles):
                fill_tubing()
            while True:
                re_check = input("Is tubing filled with fluid? Enter y/n: ")
                if re_check == 'y' or re_check == 'n':
                    break
                else:
                    print("Must enter either y or n.")
                    pass
            if re_check == 'y':
                not_filled = False
            if re_check == 'n':
                not_filled = True
        print("Tubing is filled and ready to prime")
        print("Priming pump. Important to prevent flyover events across vials")
        prime_pumps()


    ###### Call functions to make requests to robotic pipette server ########
    volumes = [[], [], [], []]
    for x in range(4):
        volumes[x] = [0] * 18

    test_command = {'base_media': volumes, 'selection_media': volumes, 'antibiotic': volumes}
    quads = [1]
    test = False

    set_arm()
    #move_to_quad(0)
    influx(test_command, quads, test)
    reset_arm()
