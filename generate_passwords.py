from werkzeug.security import generate_password_hash
import os
from getpass import getpass
import re
print("Snap4Sentinel account generator")
if os.path.isfile("users.txt"):
    print("Users file already exists, overwrite? (yes/no)")
    x = input()
    if x.lower() in ["yes", "y"]:
        pass
    elif x.lower() in ["no", "n"]:
        print("Not gonna overwrite, exiting...")
        exit(0)
    else:
        print("Unrecognized answer, exiting...")
        exit(-1)
users = {}
while True:
    print("Insert new user? (yes/no)")
    x = input()
    if x.lower() in ["yes", "y"]:
        print("Insert username (numbers and letters), max 20 chars: ")
        x = input()
        if re.fullmatch(r'^[A-Za-z0-9]{1,20}$', x):
            print("Insert password: ")
            y = getpass()
            print("Confirm password: ")
            z = getpass()
            if y != z:
                print("Passwords did not match!")
            else:
                users[x]=y
        else:
            print("Invalid username!")
    elif x.lower() in ["no", "n"]:
        if len(users.items()) == 0:
            print("You didn't create any user, do you want to quit without adding any user? (yes/no)")
            x = input()
            if x.lower() in ["yes", "y"]:
                print("Quitting without overwriting...")
                exit(0)
            elif x.lower() in ["no", "n"]:
                pass
            else:
                print("Unrecognized answer, exiting...")
                exit(-1)
        break
    else:
        print("Unrecognized answer")
if "admin" not in users.keys():
    while True:
        print("It is not recommended not generate an admin account, create one now? (yes/no)")
        x = input()
        if x.lower() in ["yes", "y"]:
            print("Insert password: ")
            y = getpass()
            print("Confirm password: ")
            z = getpass()
            if y != z:
                print("Passwords did not match!")
            else:
                users["admin"]=y
                break
        elif x.lower() in ["no", "n"]:
            print("No admin will be created")
            break

with open("users.txt","w") as f:
    for a,b in users.items():
        f.write(f"{a}: {generate_password_hash(b)}\n")
print("Saved accounts data to users.txt")