from datetime import datetime
import time
import json
import os
import sys
import socketio
import requests

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
    synoptics = "true"

def getTokenViaUserCredentials():
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

    urlToken = f"{config['base-url']}/auth/realms/master/protocol/openid-connect/token"
    response = requests.request("POST", urlToken, data=payload, headers=header)
    token = response.json()
    return token

@sio.event
def connect():
    token = getTokenViaUserCredentials()
    sio.emit("authenticate",token['access_token'])

@sio.event
def authenticate(data):
    jd = json.loads(data)
    if jd['status']=='OK':
        sio.emit('subscribe','http://www.disit.org/km4city/resource/iot/orion-1/Organization/'+get_latest_device()+' value44')
    else:
        print("Error in authenticate: ",str(jd))

@sio.event
def subscribe(data):
    print("data received in subscribing", data)
    r = json.loads(data)
    if r['status'] == 'OK':
        sio.on('update http://www.disit.org/km4city/resource/iot/orion-1/Organization/'+get_latest_device()+' value44', handle_update)
    else:
        print("Error in subscribe: ",str(r))
        
        
def handle_update(data):
    print("data updated with",data)
    globals()['latest_data']=json.loads(data)['lastValue']
    sio.disconnect()

@sio.event
def disconnect():
    print('disconnected from server')

def main():
    
    print("Configuration file opened")
    access_token = accessToken(config)
    model_name = datetime.now().strftime("%Y%m%dT%H%M%S")
    device_name = datetime.now().strftime("%Y%m%dT%H%M%S")
    
    with open('latest-model.txt', 'w') as f:
        f.write(model_name+'model')
    with open('latest-device.txt', 'w') as f:
        f.write(device_name+'device')
    createModel(config, access_token)
    
    createDevice(config, access_token, get_latest_device())

    if synoptics == "True":
        nData = 3
        sleep = 5
        previous_data = latest_data
        for i in range(0, nData):
            string_value = str(i)
            sendData(config, accessToken(config), get_latest_device(), string_value)
            print("Waiting", str(sleep), "seconds")
            time.sleep(sleep)
            sio.connect(url=config['base-url'],socketio_path='synoptics/socket.io',transports='websocket')
            sio.wait()
            sio.disconnect()
            if str(latest_data)==string_value:
                print("Data was received")
            else:
                print("Error: data was not received")
            if (previous_data==None):
                pass # first time setting a value
            elif (previous_data!=latest_data):
                print("Success: update was read as intended")
            else:
                print("Failure: the newest value wasn't read")
    deletedevice(get_latest_device(), broker_name, access_token,config["model"]["model_url"])


def createModel(conf, token):
    header = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    url = conf["model"]["model_url"] + f"action=insert&attributes=%5B%7B%22value_name%22%3A%22dateObserved%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22timestamp%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22timestamp%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%2C%7B%22value_name%22%3A%22value44%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22message%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22-%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%5D&name={get_latest_model()}&description=&type={conf['model']['model_type']}&kind={conf['model']['model_kind']}&producer=&frequency={conf['model']['model_frequency']}&kgenerator={conf['model']['model_kgenerator']}&edgegateway_type=&contextbroker={conf['model']['model_contextbroker']}&protocol={conf['model']['model_protocol']}&format={conf['model']['model_format']}&hc={conf['model']['model_hc']}&hv={conf['model']['model_hv']}&subnature={conf['model']['model_subnature']}&static_attributes=%5B%5D&service=&servicePath=&token={token}&nodered=true"
    response = requests.request("PATCH", url, headers=header)
    r = (response.text)
    r = json.loads(r)
    print(f"\nStatus for model {get_latest_model()}: " + r['status'])
    time.sleep(2)

def createDevice(conf, token, device_name):
    long = "11.24657"
    lat = "43.77709"

    header = {
        "Content-Type": "application/json",
        "Accept": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {token}",
    }
    
    url = conf["device"]["device_url"] + f"action=insert&attributes=%5B%7B%22value_name%22%3A%22dateObserved%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22timestamp%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22timestamp%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%2C%7B%22value_name%22%3A%22value44%22%2C%22data_type%22%3A%22string%22%2C%22value_type%22%3A%22message%22%2C%22editable%22%3A%220%22%2C%22value_unit%22%3A%22-%22%2C%22healthiness_criteria%22%3A%22refresh_rate%22%2C%22healthiness_value%22%3A%22300%22%7D%5D&id={device_name}&type={conf['model']['model_type']}&kind={conf['model']['model_kind']}&contextbroker={conf['model']['model_contextbroker']}&format={conf['model']['model_format']}&mac=&model={get_latest_model()}&producer=&latitude={lat}&longitude={long}&visibility=&frequency={conf['model']['model_frequency']}&token={token}&k1=ae402872-8207-4451-83cb-d047a2f68340&k2=ecb6a002-8452-4f90-88d7-e0c4c4dcf370&edgegateway_type=&edgegateway_uri=&subnature={conf['model']['model_subnature']}&static_attributes=%5B%5D&service=&servicePath=&nodered=true"
    response = requests.request("PATCH", url, headers=header)
    r = (response.text)
    r = json.loads(r)
    print(f"\nStatus for device {get_latest_device()}: " + r['status'])
    time.sleep(2)
    
def deletedevice(device_name, context_broker, access_token, base_uri):
    header = {
        "Content-Type": "application/json",
        "Accept": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {access_token}",
    }
    url = base_uri + "?action=delete&id=" + device_name + "&contextbroker=" + context_broker + "&token=" + access_token + "&nodered=yes"
    response = requests.request("POST", url, headers=header)
    if (response.status_code == 200):
        print("\nDeleted successfully")
    elif (response.status_code == 401):
        print("\nUnauthorized, accessToken: " + access_token)
    else:
        print("\nSomething else went wrong: " + response.content)
    

def sendData(conf, token, device_name, string_value):
    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    timestamp = datetime.now().isoformat()
    timestamp = timestamp[0:20] + "000Z"
    payload = {"value44":{"type":"string","value": string_value},"dateObserved":{"type":"string","value":timestamp}}
    # http://dashtest/orion-filter-orion-1/v2/entities/20231120T094406device/attrs?elementid=20231120T094406device&type=test
    url = f'{conf["base-url"]}/orion-filter/orion-1/v2/entities/' + device_name + '/attrs?elementid=' + device_name + '&type=' + conf['model']['model_type']
    print(url)
    response = requests.request("PATCH", url, data=json.dumps(payload), headers=header)
    if (response.status_code == 204):
        print("\nInsert Succeded")
    else:
        print("\nInsert Failed")



def accessToken(conf):
    access_token = ''
    payload = {
        'f': 'json',
        'client_id': 'js-kpi-client',
        'grant_type': 'password',
        'username': username,
        'password': password
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

def get_latest_device():
    with open('latest-device.txt', 'r') as f:
        return f.read()
        
def get_latest_model():
    with open('latest-model.txt', 'r') as f:
        return f.read()

if __name__ == "__main__":
    main()
