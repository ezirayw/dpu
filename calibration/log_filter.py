import json
import ast
if __name__ == '__main__':

    f1 = open('/Users/ezirayimerwolle/Desktop/ht_evolver.log')
    od_left_file = '/Users/ezirayimerwolle/Desktop/od_data_left.txt'
    od_right_file = '/Users/ezirayimerwolle/Desktop/od_data_right.txt'
    temp_file = '/Users/ezirayimerwolle/Desktop/temp.txt'
    substring_0 = '60, 60'
    substring_1 = '2023-12-16'
    while True:
        line = f1.readline()
        if not line:
            print('End of file')
            break

        if substring_0 in line and substring_1 in line and "'temp': [" in line:
            # get broadcast data as json object using bracket indexes to get data substring
            bracket_index = line.find("{")
            broadcast_string = line[bracket_index:len(line)]
            broadcast_string.replace("'", '"')

            # convert broadcast substring to python dictionary and extract relevant data
            broadcast_data = ast.literal_eval(broadcast_string)
            print(type(broadcast_data))
            with open(od_left_file, 'a') as f_od_left:
                f_od_left.write(str(broadcast_data['data']['od_90_left']) + '\n')
            with open(od_right_file, 'a') as f_od_right:
                f_od_right.write(str(broadcast_data['data']['od_90_right'])+ '\n')
            with open(temp_file, 'a') as f_temp:
                f_temp.write(str(broadcast_data['data']['temp'])+ '\n')
        
            f_od_left.close()
            f_od_right.close()
            f_temp.close()

    print("copied successfully")
    f1.close()