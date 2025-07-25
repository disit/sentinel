from werkzeug.security import generate_password_hash
import os
from getpass import getpass
import re
operation = 0 # 0 means start from new, 1 is add users, 2 is delete users, -1 is exit
print("Snap4Sentinel account generator")
if os.path.isfile("users.txt"):
    print("Users file already exists, overwrite? (yes/no)")
    x = input()
    if x.lower() in ["yes", "y"]:
        pass
    elif x.lower() in ["no", "n"]:
        print("Not gonna overwrite")
        print("Do you want to add some users? (yes/no)")
        x = input()
        if x.lower() in ["yes", "y"]:
            operation = 1
        elif x.lower() in ["no", "n"]:
            print("Do you want to delete some users? (yes/no)")
            x = input()
            if x.lower() in ["yes", "y"]:
                operation = 2
            elif x.lower() in ["no", "n"]:
                print("Exiting...")
                operation = -1
            else:
                print("Unrecognized answer, exiting...")
                operation = -1
        else:
            print("Unrecognized answer, exiting...")
            operation = -1
    else:
        print("Unrecognized answer, exiting...")
        operation = -1
if operation < 0:
    exit(-1)
users = {}
if operation == 0:
    while True:
        print("Insert new user? (yes/no)")
        x = input()
        if x.lower() in ["yes", "y"]:
            print("Insert username (numbers and letters), max 20 chars: ")
            x = input()
            if x in users:
                print("Username already exists")
            elif re.fullmatch(r'^[A-Za-z0-9]{1,20}$', x):
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
elif operation == 1:
    oldusers = {}
    print(" == Current list of users ==")
    with open("users.txt", "r") as file:
        for line in file:
            part = line.split(":", 1)[0].strip()
            print(part)
            oldusers[part] = ""
    
    print(" == End of list of users ==")
    while True:
        print("Insert new user? (yes/no)")
        x = input()
        if x.lower() in ["yes", "y"]:
            print("Insert username (numbers and letters), max 20 chars: ")
            x = input()
            
            if x in users or x in oldusers:
                print("Username already exists")
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

    with open("users.txt","a") as f:
        for a,b in users.items():
            f.write(f"{a}: {generate_password_hash(b)}\n")

elif operation == 2:
    oldusers = []
    print(" == Current list of users ==")
    with open("users.txt", "r") as file:
        here = 0
        for line in file:
            part = line.split(":", 1)[0].strip()
            print(f"{here}) {part}")
            oldusers.append(part)
            here = here + 1
    print(" == End of list of users ==")
    delete_these = []
    print("Write users to be deleted by name, if left blank will apply then close")
    while True:
        print("Insert username: ")
        x = input()
        if x == "":
            break
        elif x in delete_these:
            print(x,"will be deleted")
            delete_these.append(x)
        else:
            print("Invalid username!")
    with open("file.txt", "r+") as file:
        lines = file.readlines()
        file.seek(0)  # Go to the beginning of the file
        for line in lines:
            if not any(line.startswith(prefix+":") for prefix in delete_these):
                file.write(line)
        file.truncate()  # Remove leftover content after new end
print("Saved accounts data to users.txt")