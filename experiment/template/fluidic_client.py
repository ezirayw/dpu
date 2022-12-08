import requests, time, sys, os, json, yaml, asyncio

# Port for the robotic fluidics server connection. Do not change
XARM_PORT = 8080

# Headers for api requests to robotic fluidics server
HEADERS = {'Authorization': 'Basic azI6cENoM0hoTGhIeU1xdzJaRVk2VXJYcW9NOWVVKg==',
             'Content-Type': 'application/json',
             'Postman-Token': 'b1dd33bd-212f-4042-9877-e959e3f90a59',
             'cache-control': 'no-cache'}

def flask_request(url,payload):
    try:
        response = requests.request("POST", url, json=payload, headers=HEADERS)
        print(response.text)
        result = response.json()
        return result
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

def get_pump_settings(base_url):
    url = base_url + "/get_pump_settings"
    payload = {}
    pump_settings = flask_request(url, payload)
    return pump_settings

def arm_test(base_url):
    url = base_url + "/arm_test"
    payload = {}
    flask_request(url, payload)

def move_to_quad(base_url, quad):
    url = base_url + "/move_to_quad"
    payload = {"quad": quad}
    flask_request(url, payload)

def set_arm(base_url):
    url = base_url + "/set_arm"
    payload = {}
    flask_request(url, payload)

def reset_arm(base_url):
    url = base_url + "/reset_arm"
    payload = {}
    flask_request(url, payload)

def fill_tubing(base_url):
    url = base_url + "/fill_tubing"
    payload = {}
    flask_request(url, payload)

def prime_pumps(base_url):
    url = base_url + "/prime_pump"
    payload = {}
    flask_request(url, payload)

def influx(base_url, pump_commands):
    url = base_url + "/influx"
    payload = pump_commands
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
