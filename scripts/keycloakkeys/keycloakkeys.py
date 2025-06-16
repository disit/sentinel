import requests
import json

url = '$#base-url#$/auth/realms/master/protocol/openid-connect/certs'
try:
    response = requests.get(url)
    if response.status_code == 200:
        content = json.loads(response.text) 
        if len(content.keys())==1: #we want only one key to be here
            print("Works!")
        else:
            print(f"Error! {len(content.keys())} keys were found, only one was expected")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
except requests.RequestException as e:
    print(f"Error fetching the page: {e}")
