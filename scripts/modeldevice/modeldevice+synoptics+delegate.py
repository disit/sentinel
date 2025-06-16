from datetime import datetime
import time
import json
import sys
import socketio
import requests
import urllib.parse

http_session = requests.Session()
http_session.verify = False
sio = socketio.Client(logger=False, engineio_logger=False)
import requests

f = open("data/conf.json")
config = json.load(f)

latest_data = None
broker_name="orion-001"
username = ""
password = ""
synoptics = ""
try:
    username=sys.argv[1]
    password=sys.argv[2]
    synoptics=sys.argv[3]
except Exception as E:
    print("Proceeding with default parameters due to",E)
    username = "userareamanager"
    password = "$#areamanager-pwd#$"
    synoptics = True

def get_latest_device():
    """Returns the name of the latest device created, which is saved to a file

    Returns:
        str: String containing the name of the device
    """    
    with open('latest-device.txt', 'r') as f:
        return f.read()
        
def get_latest_model():
    """Returns the name of the latest model created, which is saved to a file

    Returns:
        str: String containing the name of the model
    """  
    with open('latest-model.txt', 'r') as f:
        return f.read()

def getTokenViaUserCredentials():
    """Get the authentication token from keycloak. Uses global variables to ease programming

    Returns:
        dict: The response from the keycloak service
    """ 
    payload = {
        'f': 'json',
        'client_id': 'js-kpi-client',
        'grant_type': 'password',
        'username': username,
        'password': password,
        'scope': 'openid'
    }

    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    urlToken = config['base-url']+"/auth/realms/master/protocol/openid-connect/token"
    response = requests.request("POST", urlToken, data=payload, headers=header)
    token = response.json()
    return token

@sio.event
def connect():
    """Connect to synoptics with the auth token
    """
    token = getTokenViaUserCredentials()
    sio.emit("authenticate",token['access_token'])

@sio.event
def authenticate(data):
    """Attempts to authenticate to the synoptics

    Args:
        data (str): The auth token
    """  
    jd = json.loads(data)
    if jd['status']=='OK':
        sio.emit('subscribe','http://www.disit.org/km4city/resource/iot/orion-1/Organization/'+get_latest_device()+' value44')
    else:
        print("Synoptics: [ERROR] in authenticate: ",str(jd))

@sio.event
def subscribe(data):
    """Subscribes to a given resource, receiving the latest data. Performs a minimal amount of error checking

    Args:
        data (str): the identifier of the resource
    """   
    print("data received in subscribing", data)
    r = json.loads(data)
    if r['status'] == 'OK':
        sio.on('update http://www.disit.org/km4city/resource/iot/orion-1/Organization/'+get_latest_device()+' value44', handle_update)
    else:
        print("Synoptics: [ERROR] in subscribe: ",str(r))
        
        
def handle_update(data):
    """Saves the received data in global variable for later use

    Args:
        data (str): string representation of the received data
    """  
    print("Data updated with",data)
    globals()['latest_data']=json.loads(data)['lastValue']
    sio.disconnect()

@sio.event
def disconnect():
    """Disconnects upon completing the task of receiving data
    """ 
    print('Disconnected from server')

def main():
    """Creates a model, then creates a device based on the model, then delegates the device to another user, then sends data to the model, and finally checks if the data can be accessed with both the servicemap and the synoptics
    """    
    access_token = accessToken(config)
    model_name = datetime.now().strftime("%Y%m%dT%H%M%S")
    device_name = datetime.now().strftime("%Y%m%dT%H%M%S")
    
    with open('latest-model.txt', 'w') as f:
        f.write(model_name+'model')
    with open('latest-device.txt', 'w') as f:
        f.write(device_name+'device')
    createModel(config, access_token)
    
    createDevice(config, access_token, get_latest_device())

    uriDelegateDevice = delegateDevice(device_name+'device', config, access_token)
    if synoptics == "True":
        nData = 7
        sleep = 1
        previous_data = latest_data
        for i in range(2, nData):
            print('\n')
            string_value = str(i)
            sendData(config, accessToken(config), get_latest_device(), string_value)
            
            print("Waiting", str(sleep), "seconds")
            time.sleep(sleep)
            access_token_delegated = accessTokenDelegated(config)
            readDelegateDevice(uriDelegateDevice, config, access_token_delegated, string_value)
            
            #print("Waiting another", str(sleep), "seconds")
            #time.sleep(sleep)
            sio.connect(url=config['base-url'],socketio_path='synoptics/socket.io',transports='websocket')
            sio.wait()
            sio.disconnect()
            if str(latest_data)==string_value:
                print("Data was received from synoptics")
            else:
                print(latest_data, string_value)
                print("Error: data was not received")
            if (previous_data==None):
                pass # first time setting a value
            elif (previous_data!=latest_data):
                print("Success: update was read as intended")
            else:
                print("Failure: the newest value wasn't read")
    deletedevice(get_latest_device(), broker_name, access_token,config["model"]["model_url"])

def readDelegateDevice(serviceuri, conf, token, value_read):
    """Reads data from a delegated device, then checks if the data read is the data expected

    Args:
        serviceuri (str): Url of the delegated device
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
        value_read (str): Value to check against the value received
    """    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+token
    }

    url = conf["base-url"] + '/superservicemap/api/v1/?serviceUri='+ serviceuri +'&realtime=true&appID=iotapp'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            if value_read==response.json()["realtime"]["results"]["bindings"][0]["value44"]["value"]:
                print("Servicemap: read expected value", value_read)
            else:
                print("Servicemap: [ERROR] didn't read correct value; got", response.json()["realtime"]["results"]["bindings"][0]["value44"]["value"], ", expected", value_read)
            #print("Request was successful.")
            #print("Response:")
            #print(response.json())
        except KeyError:
            print("Servicemap: There was no value to read: json is",response.json())
    else:
        print("Servicemap: [ERROR] request failed with status code:",response.status_code)
        print("Response:")
        print(response.text)

def createModel(conf, token):
    """Creates a new model, with the data required to create it found in a configuration dictionary

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
    """    
    header = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+token
    }
    attributes = [{"value_name":"dateObserved","data_type":"string","value_type":"timestamp","editable":"0","value_unit":"timestamp","healthiness_criteria":"refresh_rate","healthiness_value":"300"},{"value_name":"value44","data_type":"string","value_type":"message","editable":"0","value_unit":"-","healthiness_criteria":"refresh_rate","healthiness_value":"300","real_time_flag":"true"}]

    url = conf["model"]["model_url"] + "action=insert&attributes=" + urllib.parse.quote(json.dumps(attributes,separators=(",", ":"))) + "&name="+get_latest_model()+"&description=&type="+conf['model']['model_type']+"&kind="+conf['model']['model_kind']+"&producer=&frequency="+conf['model']['model_frequency']+"&kgenerator="+conf['model']['model_kgenerator']+"&edgegateway_type=&contextbroker="+conf['model']['model_contextbroker']+"&protocol="+conf['model']['model_protocol']+"&format="+conf['model']['model_format']+"&hc="+conf['model']['model_hc']+"&hv="+conf['model']['model_hv']+"&subnature="+conf['model']['model_subnature']+"&static_attributes=%5B%5D&service=&servicePath=&token="+token+"&nodered=true"
    response = requests.request("PATCH", url, headers=header)
    r = (response.text)
    r = json.loads(r)
    print("\nStatus for model,",get_latest_model(), "with", r['status'])
    time.sleep(2)

def createDevice(conf, token, device_name):
    """Creates a new device using the model created earlier

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
        device_name (str): Name of the device
    """    
    long = "11.24657"
    lat = "43.77709"

    header = {
        "Content-Type": "application/json",
        "Accept": "application/x-www-form-urlencoded",
        "Authorization": "Bearer "+token,
    }
    attributes = [{"value_name":"dateObserved","data_type":"string","value_type":"timestamp","editable":"0","value_unit":"timestamp","healthiness_criteria":"refresh_rate","healthiness_value":"300"},{"value_name":"value44","data_type":"string","value_type":"message","editable":"0","value_unit":"-","healthiness_criteria":"refresh_rate","healthiness_value":"300","real_time_flag":"true"}]
    
    url = conf["device"]["device_url"] + "action=insert&attributes=" + urllib.parse.quote(json.dumps(attributes,separators=(",", ":"))) + "&id="+device_name+"&type="+conf['model']['model_type']+"&kind="+conf['model']['model_kind']+"&contextbroker="+conf['model']['model_contextbroker']+"&format="+conf['model']['model_format']+"&mac=&model="+get_latest_model()+"&producer=&latitude="+lat+"&longitude="+long+"&visibility=&frequency="+conf['model']['model_frequency']+"&token="+token+"&k1=ae402872-8207-4451-83cb-d047a2f68340&k2=ecb6a002-8452-4f90-88d7-e0c4c4dcf370&edgegateway_type=&edgegateway_uri=&subnature="+conf['model']['model_subnature']+"&static_attributes=%5B%5D&service=&servicePath=&nodered=true"
    #mobile_device_url
    #url = conf["device"]["device_url"] + f"action=insert&attributes=%5B%7B%22value_name%22%3A%22dateObserved%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22timestamp%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22timestamp%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%2C%7B%22value_name%22%3A%22value44%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22message%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22-%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%5D&id="+device_name+"&type="+conf['model']['model_type']+"&kind="+conf['model']['model_kind']+"&contextbroker="+conf['model']['model_contextbroker']+"&format="+conf['model']['model_format']+"&mac=&model="+get_latest_model()+"&producer=&latitude="+lat+"&longitude="+long+"&visibility=&frequency="+conf['model']['model_frequency']+"&token="+token+"&k1=ae402872-8207-4451-83cb-d047a2f68340&k2=ecb6a002-8452-4f90-88d7-e0c4c4dcf370&edgegateway_type=&edgegateway_uri=&subnature="+conf['model']['model_subnature']+"&static_attributes=%5B%5B%22http%3A%2F%2Fwww.disit.org%2Fkm4city%2Fschema%23isMobile%22%2C%22true%22%5D%5D&service=&servicePath=&nodered=true"    
    response = requests.request("PATCH", url, headers=header)
    r = (response.text)
    r = json.loads(r)
    print("\nStatus for device:",get_latest_device(), "with", r['status'])
    time.sleep(2)
    
def getDevice(conf, device_name, token):
    """Get a device given its name

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json
        device_name (str): Name of the device
        token (str): Authentication token for keycloak

    Returns:
        dict: The device found, or None if it wasn't found
    """    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+token
    }
    url = conf["base-url"] + '/ownership-api/v1/list/?type=IOTID&accessToken='+token

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("Request was successful: received the devices")
        data=response.json()

    else:
        print("Request failed with status code:",response.status_code)
        print("Response:")
        print(response.text)
        
    desired_element = None
    for element in data:
        if element['elementName'] == device_name:
            desired_element = element
            print("Device was found")
            break
    return desired_element    

def accessTokenDelegated(conf):
    """Get the authentication token from keycloak. Uses global variables to ease programming. Uses the delegated credentials

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json

    Returns:
        dict: The response from the keycloak service
    """    
    access_token = ''
    payload = {
        'f': 'json',
        'client_id': conf.get('token').get('clientID'),
        'grant_type': 'password',
        'username': conf["usernamedelegated"],
        'password': conf["usernamedelegatedpassword"],
        'scope': 'openid'
    }

    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    urlToken = conf.get('token').get('token_url')
    currentTime = datetime.now()
    try:
        response = requests.request("POST", urlToken, data=payload, headers=header)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print(currentTime, "Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print(currentTime, "Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print(currentTime, "Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print(currentTime, "Ops: Something Else", err)
    else:
        token = response.json()
        access_token = token['access_token']

    return access_token

    
def delegateDevice(device_name, conf, token):
    """Given a device, delegates it to a different user

    Args:
        device_name (str): Name of the device to be delegated
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak

    Returns:
        str: elementUrl of the request
    """    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+token
    }
    
    device=getDevice(conf, device_name, token)  

    # Estrai i valori
    contextbroker = device['elementDetails']['contextbroker']
    k1 = device['elementDetails']['k1']
    k2 = device['elementDetails']['k2']

    url = conf["base-url"] + '/iot-directory/api/device.php?action=add_delegation&id='+device_name+'&delegated_user='+conf["usernamedelegated"]+'&contextbroker='+contextbroker+'&k1=' + k1 +'&k2=' + k2 +'&token=' + token +"&nodered=yes"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Request was successful: device was delegated")
        #print("------------------------------------------------------------------------------------------------")
        #print("Response:")
        #print(response.json())
    else:
        print("Request failed with status code:",response.status_code)
        print("Response:")
        print(response.text)
        
    return device['elementUrl']
    
def deletedevice(device_name, context_broker, access_token, base_uri):
    """Given a device name, deletes it

    Args:
        device_name (str): Name of the device
        context_broker (str): Context broker of the to-be-deleted device
        access_token (str): Authentication token for keycloak
        base_uri (str): Protocol and domain name of the url where to perform the action
    """    
    header = {
        "Content-Type": "application/json",
        "Accept": "application/x-www-form-urlencoded",
        "Authorization": "Bearer "+ access_token,
    }
    url = base_uri + "?action=delete&id=" + device_name + "&contextbroker=" + context_broker + "&token=" + access_token + "&nodered=yes"
    response = requests.request("POST", url, headers=header)
    if (response.status_code == 200):
        print("\nDevice," +device_name+ "deleted successfully")
    elif (response.status_code == 401):
        print("\nUnauthorized, accessToken: " + access_token)
    else:
        print("\nSomething else went wrong: " + response.content)
    

def sendData(conf, token, device_name, string_value):
    """Given a device and some data, sends said data to the given device, then prints the result of the operation

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
        device_name (str): Name of the device
        string_value (str): Value to sent to the device
    """    
    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer "+token,
    }
    timestamp = datetime.now().isoformat()
    timestamp = timestamp[0:20] + "000Z"
    payload = {"value44":{"type":"string","value": int(string_value)},"dateObserved":{"type":"string","value":timestamp}}
    #mobile_device_url
    #payload = {"value44":{"type":"string","value": string_value},"dateObserved":{"type":"string","value":timestamp},"latitude":{"value":"49.67971430832918","type":"float"},"longitude":{"value":"9.760345207618004","type":"float"}}
    url = conf["base-url"]+'/orion-filter/orion-1/v2/entities/' + device_name + '/attrs?elementid=' + device_name + '&type=' + conf['model']['model_type']
    print(url)
    response = requests.request("PATCH", url, data=json.dumps(payload), headers=header)
    if (response.status_code == 204):
        print("Insert Succeded value", string_value)
    else:
        print("Insert Failed response:", response)

def accessToken(conf):
    """Get the authentication token from keycloak. Uses global variables to ease programming

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json

    Returns:
        dict: The response from the keycloak service
    """       
    access_token = ''
    payload = {
        'f': 'json',
        'client_id': 'js-kpi-client',
        'grant_type': 'password',
        'username': username,
        'password': password,
        'scope': 'openid'
    }

    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    urlToken = conf.get('token').get('token_url')
    currentTime = datetime.now()
    try:
        response = requests.request("POST", urlToken, data=payload, headers=header)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print(currentTime, "Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print(currentTime, "Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print(currentTime, "Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print(currentTime, "Ops: Something Else", err)
    else:
        token = response.json()
        access_token = token['access_token']
    return access_token



if __name__ == "__main__":
    main()
