import socketio
import requests
import json
import sys

http_session = requests.Session()
http_session.verify = False
sio = socketio.Client(logger=False, engineio_logger=False)



broker_name="orion-1"
username = ""
password = ""
device=""
variable="testValue"
try:
    username=sys.argv[1]
    password=sys.argv[2]
    device=sys.argv[3]
except Exception as E:
    print("Probably won't work (create a device called defaultDevice with a value called testValue), but proceeding with default parameters due to",E)
    username = "userareamanager"
    password = "$#areamanager-pwd#$"
    device="defaultDevice"


def getTokenViaUserCredentials(username,password):
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

    urlToken = "$#base-url#$/auth/realms/master/protocol/openid-connect/token"
    response = requests.request("POST", urlToken, data=payload, headers=header)
    token = response.json()
    return token

@sio.event
def connect():
    print('establishing connection')
    token = getTokenViaUserCredentials(username, password)
    sio.emit("authenticate",token['access_token'])

@sio.event
def authenticate(data):
    print('authenticate result: ', data)
    jd = json.loads(data)
    if jd['status']=='OK' :
        sio.emit('subscribe','http://www.disit.org/km4city/resource/iot/orion-1/Organization/{device} {variable}')

@sio.event
def subscribe(data):
    print('subscribe result:', data)
    r = json.loads(data)
    if r['status'] == 'OK' :
      sio.on('update http://www.disit.org/km4city/resource/iot/orion-1/Organization/{device} {variable}', handle_update)

def handle_update(data):
    print(data)

@sio.event
def disconnect():
    print('disconnected from server')
    sio.disconnect()


sio.connect(url='$#base-url#$/',socketio_path='synoptics/socket.io',transports='websocket')
sio.wait()