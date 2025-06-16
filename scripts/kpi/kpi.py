from datetime import datetime
import time
import json
import os
import requests
import time
import requests
import sys
import socketio

http_session = requests.Session()
http_session.verify = False
sio = socketio.Client(logger=False, engineio_logger=False)

broker_name="orion-1"
username = ""
password = ""
variable="value44"
kpi_id=""
access_token=""
try:
    username=sys.argv[1]
    password=sys.argv[2]
except Exception as E:
    print("Proceeding with default parameters due to",E)
    username = "userareamanager"
    password = "$#areamanager-pwd#$"

root_path = os.getcwd()
params_path = root_path + "/data/conf.json"
f = open(params_path)
conf= json.load(f)

####
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

    urlToken = conf['url']+"/auth/realms/master/protocol/openid-connect/token"
    response = requests.request("POST", urlToken, data=payload, headers=header)
    token = response.json()
    return token

@sio.event
def connect():
    """Connect to synoptics with the auth token
    """    
    token = getTokenViaUserCredentials()
    #print(str(token))
    sio.emit("authenticate",token['access_token'])

@sio.event
def authenticate(data):
    """Attempts to authenticate to the synoptics

    Args:
        data (str): The auth token
    """    
    jd = json.loads(data)
    if jd['status']=='OK':
        sio.emit('subscribe',str(kpi_id))
    else:
        print("Synoptics: [ERROR] in authenticate: ",str(jd))
        exit(-1)

@sio.event
def subscribe(data):
    """Subscribes to a given resource, receiving the latest data. Performs a minimal amount of error checking

    Args:
        data (str): the identifier of the resource
    """    
    print("data received in subscribing", data)
    r = json.loads(data)
    if r['status'] == 'OK':
        sio.on("update "+str(kpi_id), handle_update)
    else:
        print("Synoptics: [ERROR] in subscribe: ",str(r))
        exit(-1)
        
        
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
####


def main():
    """Creates a kpi, sends data, then reads it from both the servicemap and the synoptics to ensure that all of the involved components are properly functioning
    """    
    print("Configuration file opened")
    access_token = accessToken(conf)
    globals()['kpi_id']=createKpi(conf,access_token)
    for i in range(5):
        sendDataKpi(kpi_id,conf,access_token,str(i))
        getKpi(kpi_id,conf,access_token,str(i))
        sio.connect(url=conf['url'],socketio_path='synoptics/socket.io',transports='websocket')
        sio.wait()
        sio.disconnect()
        if globals()['latest_data'] == i:
            print("Data sent matched data received from synoptics")
        else:
            print("[Error] Data did not match data received from synoptics")
        
            
def getKpi(idKpi, conf, token, base_to_check):
    """Receives the data from a kpi. Then attempts to check if it is properly functioning

    Args:
        idKpi (str): Identifier of the kpi
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
        base_to_check (int): The previous value received
    """    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = conf["url"] + '/datamanager/api/v1/kpidata/'+str(idKpi)+'/values/?sourceRequest=iotapp&highLevelType=MyKPI"&last=1'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Request was successful: the kpi was received")
        
        # value is sent as a string of a float, thus the control value is being cast to a float by adding a 0 decimal
        if response.json()[0]["value"]==str(base_to_check)+'.0':
            print("Data sent matched data received from KPI:", response.json()[0]["value"])
        else:
            print("[Error] Data sent did not match data received from KPI")
            print("Response:")
            print(response.json())
            print("Url used:",url)
    else:
        print("[Error] Request getKPI failed with status code:",response.status_code)
        print("Response:")
        print(response.text)
        print("Url used:",url)

def sendDataKpi(idKpi, conf, token, value):
    """Send data to a given kpi

    Args:
        idKpi (str): Identifier of the kpi
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak
        value (str): Value to be sent to the kpi
    """    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    url = conf["url"] + '/datamanager/api/v1/kpidata/'+str(idKpi)+'/values/?sourceRequest=iotapp'
    data = {
        "kpiId": idKpi,
        "value": value,
        "dataTime": int(time.time() * 1000)
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Request was successful: some data was sent to the kpi")
    else:
        print(f"[Error] Request sendDataKPI failed with status code: {response.status_code}")
        print("Response:")
        print(response.text)
        print("Url used:",conf["url"] + '/datamanager/api/v1/kpidata/'+str(idKpi)+'/values/?sourceRequest=iotapp')


def createKpi(conf, token):
    """Creates a kpi with a configuration saved inside the function as a dict

    Args:
        conf (dict): Dictionary holding the data, see data/conf.json
        token (str): Authentication token for keycloak

    Returns:
        str: id of the created kpi
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = conf["url"] + '/datamanager/api/v1/kpidata/?sourceRequest=kpieditor'
    print(url)
    data = {
        "highLevelType": "MyKPI",
        "valueName": "countingWifiLast",
        "description": "tryKPI",
        "info": "newKPI",
        "metadata": [
            {"key": "note"},
            {"key": "address"},
            {"key": "civic"},
            {"key": "city"},
            {"key": "province"},
            {"key": "phone"},
            {"key": "fax"},
            {"key": "website"},
            {"key": "email"}
        ],
        "nature": "TourismService",
        "subNature": "Wifi",
        "valueUnit": "#",
        "valueType": "people_count",
        "dataType": "integer",
        "latitude": "43.785905",
        "longitude": "11.228027"
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Request was successful: a new kpi was created")
        #print("Response:")
        #print(response.json())
    else:
        print(f"[Error] Request failed with status code: {response.status_code}")
        print("Response:")
        print(response.text)
    print("id of kpi:", response.json()['id'])
    return response.json()['id']



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
        'client_id': conf.get('token').get('clientID'),
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
        print(currentTime, "[Error] Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print(currentTime, "[Error] Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print(currentTime, "[Error] Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print(currentTime, "[Error] Ops: Something Else", err)
    else:
        token = response.json()
        print("The access token was correctly collected")
        access_token = token['access_token']

    return access_token


if __name__ == "__main__":
    main()
