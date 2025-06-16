from datetime import datetime

import json
import requests
import sys

def accessToken(data_json):
    access_token = ''
    payload = {
        'client_id': "js-kpi-client",
        'client_secret': "a347fb2d-87f0-4d41-89a9-b746b5273ccd",
        'grant_type': 'password',
        'username': data_json['username'],
        'password': data_json['password'],
        'scope': 'openid'
    }

    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    urlToken = f"{data_json['url']}/auth/realms/master/protocol/openid-connect/token"
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


def main():
    data_json=json.loads(open('data/data.json').read())
    url = f"{data_json['url']}/iot-directory/api/contextbroker.php"
    url = url + "?token=" + accessToken(data_json)
    url = url + "&action=update&name=orion-1&kind=internal&path=&version=v2&visibility=&ip=orion-001&port=1026&protocol=ngsi&login=login&password=login"
    url = url + f"&latitude={data_json['latitude']}&longitude={data_json['longitude']}&createdDate=2024-01-11+09%3A21%3A42&accesslink=orionbrokerfilter-001&accessport=8443&apikey=null&sha=&urlnificallback=http%3A%2F%2Fnifi%3A1030%2Fingestngsi&services=%5B%5D&log_orion=0&nodered="
    header={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}
    print(url)
    response=requests.request("POST", url,headers=header)
    print("status:",str(response.status_code), "with message:",json.loads(response.text)['msg'][2:])
    if "Cannot retrieve use information" in json.loads(response.text)['msg'][2:]:
        print(f"Is the host able to resolve {data_json['url']} as itself?", file=sys.stderr)
    return 0
    
if __name__ == "__main__":
    main()
