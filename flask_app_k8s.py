
'''Copyright (C) 2023 DISIT Lab http://www.disit.org - University of Florence

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.'''
import subprocess
from threading import Lock
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory, redirect
import requests
import mysql.connector
import json
import os
import copy
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import base64
import random
import string
import traceback
from urllib.parse import urlparse
from datetime import datetime, timedelta
import concurrent.futures
import re
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from datetime import timedelta
import html


os.environ["PYTHONUNBUFFERED"]="1"
os.environ["admin-log-length"]="200"
os.environ["default-log-length"]="1000"
os.environ["requests-timeout"]="15000"
os.environ["is-master"]="true"
os.environ["telegram-api-token"]="replaceme"
os.environ["telegram-channel"]="123456789"
os.environ["db-user"]="root"
os.environ["db-passwd"]="cPehkP5bbNJMt6Ao"
os.environ["db-host"]="sentineldb"
os.environ["db-port"]="3306"
os.environ["smtp-server"]="change.me.com"
os.environ["smtp-port"]="587"
os.environ["sender-email"]="change@at.me"
os.environ["sender-email-password"]="replacethispassword"
os.environ["email-recipients"]="['first_address@to.besent', 'second_address@to.besent', 'more_addresses@to.besent']"
os.environ["platform-url"]="http://example.org"
os.environ["platform-explanation"]="Some information"
os.environ["load-threshold"]="30"
os.environ["memory-threshold"]="1"
os.environ["running_as_kubernetes"]="True"

def string_of_list_to_list(string):
    try:
        a = string[1:-1]
        a = a.replace('"',"")
        a = a.replace("'","")
        ret = a.split(",")
        return [b.strip() for b in ret]
    except:
        raise Exception("Couldn't do it")

USERS_FILE = '/data/users.txt'

users = {}
with open(USERS_FILE, 'r') as f:
    for line in f:
        if ' ' in line:
            username, hashed = line.strip().split(': ', 1)
            users[username] = hashed


class Snap4SentinelTelegramBot:
    def __init__(self, bot_token, chat_id=None, actually_send=True):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._actually_send = actually_send

    def set_chat_id(self, chat_id, force=False):
        if not isinstance(chat_id, str):
            return False
        if self._chat_id == None or force is True:
            self._chat_id = chat_id
            return True

    def send_message(self, message, chat_id=None):
        if not self._actually_send:
            return True, "Did not send but was told not to"
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = {}
        if chat_id is None:
            if self._chat_id is None:
                return False, "Chat id was not set"
            else:
                payload["chat_id"] = self._chat_id
        else:
            payload["chat_id"] = chat_id
        if not isinstance(message, str):
            return False, "Message wasn't text"
        payload["text"] = message
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, "Message was sent"
        else:
            return False, f"Failed to send message: {response.text}"
        

f = open("conf.json")
config = json.load(f)


API_TOKEN = os.getenv("telegram-api-token")
bot_2 = Snap4SentinelTelegramBot(API_TOKEN, int(os.getenv("telegram-channel")))
greendot = """&#128994"""
reddot = """&#128308"""

# edit this block according to your mysql server's configuration
db_conn_info = {
    "user": os.getenv("db-user"),
    "passwd": os.getenv("db-passwd"),
    "host": os.getenv("db-host"),
    "port": int(os.getenv("db-port")),
    "database": "checker",
    "auth_plugin": 'mysql_native_password'
}

def format_error_to_send(instance_of_problem, containers, because = None, explain_reason=None):
    using_these = ', '.join('"{0}"'.format(w).strip() for w in containers.split(", "))
    if because:
        becauses=because.split(",")
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        query2 = 'SELECT category, component, position FROM checker.component_to_category where component in ({}) order by category;'.format(using_these)
        cursor.execute(query2)
        now_it_is = cursor.fetchall()
    newstr=""
    for a in now_it_is:
        curstr="In category " + a[0] + ", located in " + a[2] + " the kubernetes container named " + a[1] + " " + instance_of_problem
        if because:
            newstr += curstr + explain_reason + becauses.pop(0)+"\n"
        else:
            newstr += curstr+"\n"
    return newstr

def send_telegram(chat_id, message):
    if isinstance(message, list):
        message[2]=filter_out_muted_containers_for_telegram(message[2])
    bot_2.send_message(message, chat_id)
    return

def send_email(sender_email, sender_password, receiver_emails, subject, message):
    composite_message = os.getenv("platform-explanation") + "\n" + message
    smtp_server = os.getenv("smtp-server")
    smtp_port = int(os.getenv("smtp-port"))
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender_email, sender_password)
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ','.join(receiver_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(str(composite_message), 'html'))
    server.send_message(msg)
    server.quit()
    return
    

def filter_out_muted_containers_for_telegram(containers):
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''WITH RankedEntries AS ( 
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY component ORDER BY until DESC) AS row_num FROM telegram_alert_pauses
                    ) 
                    SELECT component, until FROM RankedEntries WHERE row_num = 1;'''
            cursor.execute(query)
            results = cursor.fetchall()
        new_elements=[]
        for element in containers:
            if any(element in string for string in [a[0] for a in results]) and element[1].strftime("%Y-%m-%d %H:%M:%S")>datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                pass
            else:
                new_elements.append(element)
    except Exception:
        print("Something went wrong during container filtering because of:",traceback.format_exc())
    return ", ".join(new_elements)

def filter_out_muted_failed_are_alive_for_telegram(tests):
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''WITH RankedEntries AS ( 
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY component ORDER BY until DESC) AS row_num FROM telegram_alert_pauses
                    ) 
                    SELECT component, until FROM RankedEntries WHERE row_num = 1;'''
            cursor.execute(query)
            results = cursor.fetchall()
            if len(results) == 0:
                return ", ".join([a["container"] for a in tests])
        new_elements=[]
        for element in results:
            for element_2 in tests:
                if element[0] == element_2["container"]:
                    if element[1].strftime("%Y-%m-%d %H:%M:%S")>datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                        pass
                    else:
                        if element_2 in new_elements:
                            pass
                        else:
                            new_elements.append(element_2)
                else:
                    if element_2 in new_elements:
                        pass
                    else:
                        new_elements.append(element_2)
    except Exception:
        print("Something went wrong during container filtering because of:",traceback.format_exc())
    return ", ".join([a["container"] for a in new_elements])

def filter_out_wrong_status_containers_for_telegram(containers):
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''WITH RankedEntries AS ( 
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY component ORDER BY until DESC) AS row_num FROM telegram_alert_pauses
                    ) 
                    SELECT component, until FROM RankedEntries WHERE row_num = 1;'''
            cursor.execute(query)
            results = cursor.fetchall()
        new_elements=[]
        restruct={}
        for a in results:
            restruct[a[0]]=a[1]
        for element in containers:
            if element["Name"] in [a[0] for a in results]:
                if restruct[element[element]].strftime("%Y-%m-%d %H:%M:%S")>datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                    pass
                else:
                    new_elements.append(element)
            else:
                new_elements.append(element)
    except Exception:
        print("Something went wrong during container filtering because of:",traceback.format_exc())
    return ", ".join([a["Name"] for a in new_elements])

def isalive():
    send_email(os.getenv("sender-email"), os.getenv("sender-email-password"), string_of_list_to_list(os.getenv("email-recipients")), os.getenv("platform-url")+" is alive", os.getenv("platform-url")+" is alive")
    send_telegram(int(os.getenv("telegram-channel")), os.getenv("platform-url")+" is alive")
    return

def auto_run_tests():
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''select command, container_name, command_explained from tests_table;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            total_result = ""
            badstuff = []
            for r in list(results):
                command_ran = subprocess.run(r[0], shell=True, capture_output=True, text=True, encoding="cp437", timeout=10).stdout
                total_result += command_ran
                if "Failure" in command_ran:
                    badstuff.append({"container":r[1], "result":command_ran, "command":r[2]})
            return badstuff
    except Exception:
        print("Something went wrong during tests running because of:",traceback.format_exc())
        return badstuff

def auto_alert_status():
    if not os.getenv("running_as_kubernetes"):
        containers_ps = [a for a in (subprocess.run('docker ps --format json -a', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
        containers_stats = [b for b in (subprocess.run('docker stats --format json -a --no-stream', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
        containers_merged = []
        for container_stats in containers_stats:
            for container_ps in containers_ps:
                for key1, value1 in json.loads(container_stats).items():
                    for key2, value2 in json.loads(container_ps).items():
                        if key1 == "Name" and key2 == "Names":
                            if value1 == value2:
                                containers_merged.append({**json.loads(container_ps), **json.loads(container_stats)})
    else:
        raw_json = json.loads(subprocess.run('kubectl get pods -o json',shell=True, capture_output=True, text=True, encoding="utf_8").stdout)
        conversions=[]
        for item in raw_json["items"]:
            conversion = {}
            try:
                command = item.get("command", [])
                args = item.get("args", [])
                full_command = command + args
                if full_command:
                    conversion["Command"] = full_command
            except Exception as E: # no command set, read from image
                #conversion["Command"] = subprocess.run(f"kubectl exec {item['metadata']['name']} -n {namespace} -- cat /proc/1/cmdline | tr '\0' ' '", shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                conversion["Command"] = "Command not found"
            conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
            conversion["ID"] = item["metadata"]["uid"]
            conversion["Image"] = item["spec"]["containers"][0]["image"]
            conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
            #conversion["LocalVolumes"] = "Whatever"
            conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
            conversion["Names"] = item["metadata"]["name"]
            #conversion["Networks"] = "Whatever"
            conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])

            fmt = "%Y-%m-%dT%H:%M:%SZ"
            dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
            dt2 = datetime.now()
            try:
                conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minutes(s) and {(dt2-dt1).seconds % 60} second(s)"
            except Exception as E:
                print(E)
                conversion["RunningFor"] = "Not running"
            #conversion["Size"] = "Whatever"
            conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0]
            conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
            #conversion["BlockIO"] = "Whatever"
            #conversion["CPUPerc"] = "Whatever"
            conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
            #conversion["MemPerc"] = "Whatever"
            #conversion["MemUsage"] = "Whatever"
            conversion["Name"] = item["metadata"]["name"]
            #conversion["NetIO"] = "Whatever"
            #conversion["PIDs"] = "Whatever"

            # new things
            conversion["Node"] = item["spec"]["nodeName"]
            temp_vols=copy.deepcopy(item["spec"]["volumes"])
            temp_str = ""
            for vol_num in range(len(item["spec"]["volumes"])):
                temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                del temp_vols[vol_num]["name"]
                temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                
            conversion["Volumes"] = temp_str
            conversion["Namespace"] = item["metadata"]["namespace"]
            
            
            conversions.append(conversion)
        containers_merged = conversions
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''SELECT * FROM checker.component_to_category;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
    except Exception:
        send_alerts("Can't reach db, auto alert 1:"+ traceback.format_exc())
        return
    is_alive_with_ports = auto_run_tests()
    components = [a[0].replace("*","") for a in results]
    components_original = [a[0] for a in results]
    containers_which_should_be_running_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and (c["State"] != "running")]
    containers_which_should_be_exited_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in ["certbot"]) and c["State"] != "exited"]
    containers_which_are_running_but_are_not_healthy = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and "unhealthy" in c["Status"]]
    problematic_containers = containers_which_should_be_exited_and_are_not + containers_which_should_be_running_and_are_not + containers_which_are_running_but_are_not_healthy
    #containers_which_are_fine = list(set([n["Names"] for n in containers_merged]) - set([n["Names"] for n in problematic_containers]))
    names_of_problematic_containers = [n["Names"] for n in problematic_containers]
    containers_which_are_not_expected = list(set(components_original)-set([a["Names"] for a in [b for b in containers_which_are_not_expected if not b.endswith("*")]]))
    '''
    top = get_top()
    load_averages = re.findall(r"(\d+\.\d+)", top["system_info"]["load_average"])[-3:]
    load_issues=""
    for average, timing in zip(load_averages, [1, 5, 15]):
        if float(average) > int(os.getenv("load-threshold")):
            load_issues += "Load threshold above "+str(int(os.getenv("load-threshold"))) + " with " + str(average) + "during the last " + str(timing) + " minute(s).\n"
    memory_issues = ""
    if float(top["memory_usage"]["used"])/float(top["memory_usage"]["total"]) > int(os.getenv("memory-threshold")):
        memory_issues = "Memory usage above " + str(int(os.getenv("memory-threshold"))) + " with " + str(top["memory_usage"]["used"]) + " " + top["memory_measuring_unit"] + " out of " + top["memory_usage"]["total"] + " " + top["memory_measuring_unit"] + " currently in use\n"
    '''
    if len(names_of_problematic_containers) > 0 or len(is_alive_with_ports) > 0 or len(containers_which_are_not_expected):
        try:
            # todo
            # UPDATE `checker`.`summary_status` SET `status` = "&#128308" where `category` in ("System","Broker") # join, set of a list
            issues = ["","","","",""]
            if len(names_of_problematic_containers) > 0:
                issues[0]=problematic_containers
            if len(is_alive_with_ports) > 0:
                issues[1]=is_alive_with_ports
            if len(containers_which_are_not_expected) > 0:
                issues[2]=containers_which_are_not_expected
            '''
            if len(load_issues)>0:
                issues[3]=load_issues
            if len(memory_issues)>0:
                issues[4]=memory_issues
            '''
            send_advanced_alerts(issues)
        except Exception:
            print(traceback.format_exc())
            send_alerts("Couldn't properly send error messages: "+traceback.format_exc())
            return
    else:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                update_healthy_categories_query=f"UPDATE `checker`.`summary_status` SET `status` = %s;"
                cursor.execute(update_healthy_categories_query, [greendot])
                conn.commit()
                return
        except Exception:
            print(traceback.format_exc())
            send_alerts("Couldn't reach database while not needing to send error messages: "+traceback.format_exc())
            return

def get_top():
    if os.environ["running_as_kubernetes"] == "True":
        nodes_output = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True,
            text=True
        )
        nodes_data = json.loads(nodes_output.stdout)

        # Get pods JSON (across all namespaces)
        pods_output = subprocess.run(
            ["kubectl", "get", "pods", "-A", "-o", "json"],
            capture_output=True,
            text=True
        )
        pods_data = json.loads(pods_output.stdout)

        # Count running pods per node
        pod_counts = {}
        for pod in pods_data["items"]:
            node_name = pod.get("spec", {}).get("nodeName")
            pod_phase = pod.get("status", {}).get("phase")
            if node_name and pod_phase == "Running":
                pod_counts[node_name] = pod_counts.get(node_name, 0) + 1

        # Construct final node info with pod counts
        node_info = []
        for item in nodes_data["items"]:
            name = item["metadata"]["name"]
            capacity = item["status"]["capacity"]

            node_data = {
                "name": name,
                "capacity": {
                    "cpu": capacity.get("cpu"),
                    "memory": capacity.get("memory")
                },
                "running_pods": f"{str(pod_counts.get(name, 0))}/{capacity.get('pods')}",
                "status": ", ".join(["Ready" if a["message"] == "kubelet is posting ready status" else a["message"] for a in item["status"]["conditions"] if a["status"]=="True"])
            }

            node_info.append(node_data)
        return render_template("k8s-top.html", json_data=json.dumps(node_info)), 200
    else:
        process = subprocess.Popen(['top', '-b', '-n', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = process.communicate()

        # Initialize dictionaries to hold parsed data
        parsed_data = {
            'system_info': {},
            'cpu_usage': {},
            'memory_usage': {},
            'processes': [],
            'memory_measuring_unit': "B"
        }
        
        # Split output into lines
        lines = stdout.splitlines()
        
        # Parse system information (first line typically)
        system_info_line = lines[0]
        parsed_data['system_info'] = {
            'time': re.search(r'\d{2}:\d{2}:\d{2}', system_info_line).group(),
            'up_time': re.search(r'up\s+([^,]+)', system_info_line).group(1),
            'users': re.search(r'(\d+)\s+user', system_info_line).group(1),
            'load_average': re.search(r'load average:\s+(.+)', system_info_line).group(1)
        }

        # Parse CPU usage (usually line 3)
        cpu_usage_line = lines[2]
        cpu_values = re.findall(r'(\d+\.\d+)', cpu_usage_line)
        parsed_data['cpu_usage'] = {
            'us': cpu_values[0],  # User CPU usage
            'sy': cpu_values[1],  # System CPU usage
            'ni': cpu_values[2],  # Nice CPU usage
            'id': cpu_values[3],  # Idle CPU percentage
            'wa': cpu_values[4],  # IO wait
            'hi': cpu_values[5],  # Hardware interrupt
            'si': cpu_values[6],  # Software interrupt
            'st': cpu_values[7]   # Steal time
        }

        # Parse memory usage (usually line 4)
        memory_usage_line = lines[3]
        mem_values = re.findall(r'(\d+)', memory_usage_line)
        parsed_data["memory_measuring_unit"]=re.findall(r'^(\w+)', memory_usage_line)[0]
        parsed_data['memory_usage'] = {
            'total': mem_values[0],
            'free': mem_values[1],
            'used': mem_values[2],
            'buff_cache': mem_values[3]
        }

        # Parse process list (starts from line 7 onwards)
        for line in lines[7:]:
            columns = line.split()
            if len(columns) >= 12:  # Ensure we have enough columns for parsing
                process_info = {
                    'pid': columns[0],
                    'user': columns[1],
                    'pr': columns[2],
                    'ni': columns[3],
                    'virt': columns[4],
                    'res': columns[5],
                    'shr': columns[6],
                    's': columns[7],
                    'cpu': columns[8],
                    'mem': columns[9],
                    'time': columns[10],
                    'command': ' '.join(columns[11:])
                }
                parsed_data['processes'].append(process_info)
    return parsed_data

def send_alerts(message):
    try:
        send_email(os.getenv("sender-email"), os.getenv("sender-email-password"), string_of_list_to_list(os.getenv("email-recipients")), os.getenv("platform-url")+" is in trouble!", message)
        send_telegram(int(os.getenv("telegram-channel")), message)
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
def update_container_state_db():
    if not os.getenv("running_as_kubernetes"):
        containers_ps = [a for a in (subprocess.run('docker ps --format json -a', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
        containers_stats = [b for b in (subprocess.run('docker stats --format json -a --no-stream', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
        containers_merged = []
        for container_stats in containers_stats:
            for container_ps in containers_ps:
                for key1, value1 in json.loads(container_stats).items():
                    for key2, value2 in json.loads(container_ps).items():
                        if key1 == "Name" and key2 == "Names":
                            if value1 == value2:
                                containers_merged.append({**json.loads(container_ps), **json.loads(container_stats)})
        
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''INSERT INTO `checker`.`container_data` (`containers`) VALUES (%s);'''
            cursor.execute(query,(json.dumps(containers_merged),))
            conn.commit()
    else:
        raw_json = json.loads(subprocess.run('kubectl get pods -o json',shell=True, capture_output=True, text=True, encoding="utf_8").stdout)
        conversions=[]
        for item in raw_json["items"]:
            conversion = {}
            try:
                command = item.get("command", [])
                args = item.get("args", [])
                full_command = command + args
                if full_command:
                    conversion["Command"] = full_command
            except Exception as E: # no command set, read from image
                #conversion["Command"] = subprocess.run(f"kubectl exec {item['metadata']['name']} -n {namespace} -- cat /proc/1/cmdline | tr '\0' ' '", shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                conversion["Command"] = "Command not found"
            conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
            conversion["ID"] = item["metadata"]["uid"]
            conversion["Image"] = item["spec"]["containers"][0]["image"]
            conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
            #conversion["LocalVolumes"] = "Whatever"
            conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
            conversion["Names"] = item["metadata"]["name"]
            #conversion["Networks"] = "Whatever"
            conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])

            fmt = "%Y-%m-%dT%H:%M:%SZ"
            dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
            dt2 = datetime.now()
            try:
                conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minutes(s) and {(dt2-dt1).seconds % 60} second(s)"
            except Exception as E:
                print(E)
                conversion["RunningFor"] = "Not running"
            #conversion["Size"] = "Whatever"
            conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0]
            conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
            #conversion["BlockIO"] = "Whatever"
            #conversion["CPUPerc"] = "Whatever"
            conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
            #conversion["MemPerc"] = "Whatever"
            #conversion["MemUsage"] = "Whatever"
            conversion["Name"] = item["metadata"]["name"]
            #conversion["NetIO"] = "Whatever"
            #conversion["PIDs"] = "Whatever"

            # new things
            conversion["Node"] = item["spec"]["nodeName"]
            temp_vols=copy.deepcopy(item["spec"]["volumes"])
            temp_str = ""
            for vol_num in range(len(item["spec"]["volumes"])):
                temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                del temp_vols[vol_num]["name"]
                temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                
            conversion["Volumes"] = temp_str
            conversion["Namespace"] = item["metadata"]["namespace"]
            
            conversions.append(conversion)
            
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''INSERT INTO `checker`.`container_data` (`containers`) VALUES (%s);'''
            cursor.execute(query,(json.dumps(conversions),))
            conn.commit()
        
mutex = Lock()
def queued_running(command):
    answer = None
    print("Locking executor due to running", command)
    with mutex:
        answer = subprocess.run(command, shell=True, capture_output=True, text=True, encoding="utf_8")
    print ("Unlocked executor")
    return answer
    


def send_advanced_alerts(message):
    try:
        text_for_email, em1, em2, em3 = "", "", "", ""
        if len(message[0])>0:
            em1 = format_error_to_send("is not in the correct status ",", ".join([a["Name"] for a in message[0]]),", ".join([a["Status"] for a in message[0]]),"as its status currently is: ")
            text_for_email = "These containers are not in the correct status: " + ", ".join([a["Name"] for a in message[0]])+"\n"
        if len(message[1])>0:
            em2 = format_error_to_send("is not answering correctly to its 'is alive' test ",", ".join([a["container"] for a in message[1]]),", ".join([a["command"] for a in message[1]]),"given the failure of: ")
            text_for_email+= 'These containers are not answering correctly to their "is alive" test: '+ ", ".join([a["container"] for a in message[1]])+"\n"
        if len(message[2])>0:
            em3 = format_error_to_send("wasn't found running in kubernetes ",", ".join(message[2]))
            text_for_email+= "These containers weren't found in kubernetes: "+ ", ".join(message[2])+"\n"
        if len(message[3])>0:
            text_for_email+= message[3]
        if len(message[4])>0:
            text_for_email+= message[4]
        try:
            if len(text_for_email) > 5:
                send_email(os.getenv("sender-email"), os.getenv("sender-email-password"), string_of_list_to_list(os.getenv("email-recipients")), os.getenv("platform-url")+" is in trouble!", em1+"\n"+em2+"\n"+em3+"\n"+message[3]+"\n"+message[4])
        except:
            print("[ERROR] while sending email:",text_for_email)
        text_for_telegram, t1, t2, t3 = "", "", "", ""
        if len(message[0])>0:
            t1=format_error_to_send("is not in the correct status ",filter_out_wrong_status_containers_for_telegram(message[0]))
            text_for_telegram = "These containers are not in the correct status: " + str(filter_out_wrong_status_containers_for_telegram(message[0])) +"\n"
        if len(message[1])>0:
            t2=format_error_to_send("is not answering correctly to its 'is alive' test ",filter_out_muted_failed_are_alive_for_telegram(message[1]))
            text_for_telegram+= 'These containers are not answering correctly to their "is alive" test: '+ str(filter_out_muted_failed_are_alive_for_telegram(message[1]))+"\n"
        if len(filter_out_muted_containers_for_telegram(message[2]))>0:
            t3=format_error_to_send("wasn't found running in kubernetes ",filter_out_muted_containers_for_telegram(message[2]))
            text_for_telegram+= "These containers weren't found in kubernetes: "+ str(filter_out_muted_containers_for_telegram(message[2]))+"\n"
        if len(message[3])>0:
            text_for_telegram+= message[3]
        if len(message[4])>0:
            text_for_telegram+= message[4]
        if len(text_for_telegram)>5:  #todo check me better
            try:
                send_telegram(int(os.getenv("telegram-channel")), t1+"\n"+t2+"\n"+t3+"\n"+message[3]+"\n"+message[4])
            except:
                print("[ERROR] while sending telegram:",t1+"\n"+t2+"\n"+t3+"\n"+message[3]+"\n"+message[4],"\nDue to",traceback.format_exc())
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
    
scheduler = BackgroundScheduler()
scheduler.add_job(auto_alert_status, trigger='interval', minutes=5)
scheduler.add_job(update_container_state_db, trigger='interval', minutes=5)
scheduler.add_job(isalive, 'cron', hour=8, minute=0)
scheduler.add_job(isalive, 'cron', hour=20, minute=0)
scheduler.start()
auto_alert_status()

def create_app():
    app = Flask(__name__)
    app.secret_key = b'\x8a\x17\x93kT\xc0\x0b6;\x93\xfdp\x8bLl\xe6u\xa9\xf5x'
    app.permanent_session_lifetime = timedelta(minutes=15)  # session expires after 15 mins of inactivity

    @app.route("/")
    def main_page():
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if 'username' in session:
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''SELECT complex_tests.*, GetHighContrastColor(button_color), COALESCE(categories.category, "System") as category FROM checker.complex_tests left join category_test on id = category_test.test left join categories on categories.idcategories = category_test.category;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    if session['username'] != "admin":
                        return render_template("checker-k8.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),timeout=int(os.getenv("requests-timeout")),user=session['username'])
                    else:
                        query_2 = '''select * from all_logs limit %s;'''
                        cursor.execute(query_2, (int(os.getenv("admin-log-length")),))
                        conn.commit()
                        results_log = cursor.fetchall()
                        return render_template("checker-admin.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),admin_log=results_log,timeout=int(os.getenv("requests-timeout")),user=session['username'],platform=os.getenv("platform-url"))
                return redirect(url_for('login'))
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    
    @app.route("/get_local_top", methods=["GET"])
    def get_local_top():
        if 'username' in session:
            if os.environ["running_as_kubernetes"] == "True":
                nodes_output = subprocess.run(
                    ["kubectl", "get", "nodes", "-o", "json"],
                    capture_output=True,
                    text=True
                )
                nodes_data = json.loads(nodes_output.stdout)

                # Get pods JSON (across all namespaces)
                pods_output = subprocess.run(
                    ["kubectl", "get", "pods", "-A", "-o", "json"],
                    capture_output=True,
                    text=True
                )
                pods_data = json.loads(pods_output.stdout)

                # Count running pods per node
                pod_counts = {}
                for pod in pods_data["items"]:
                    node_name = pod.get("spec", {}).get("nodeName")
                    pod_phase = pod.get("status", {}).get("phase")
                    if node_name and pod_phase == "Running":
                        pod_counts[node_name] = pod_counts.get(node_name, 0) + 1

                # Construct final node info with pod counts
                node_info = []
                for item in nodes_data["items"]:
                    name = item["metadata"]["name"]
                    capacity = item["status"]["capacity"]

                    node_data = {
                        "name": name,
                        "capacity": {
                            "cpu": capacity.get("cpu"),
                            "memory": capacity.get("memory")
                        },
                        "running_pods": f"{str(pod_counts.get(name, 0))}/{capacity.get('pods')}",
                        "status": ", ".join(["Ready" if a["message"] == "kubelet is posting ready status" else a["message"] for a in item["status"]["conditions"] if a["status"]=="True"])
                    }

                    node_info.append(node_data)
                return render_template("k8s-top.html", json_data=json.dumps(node_info)), 200
            else:
                json_data=get_top()
                json_data["source"] = os.getenv("platform-url")
                with mysql.connector.connect(**db_conn_info) as conn:
                    try:
                        cursor = conn.cursor(buffered=True)
                        query = '''SELECT ip FROM checker.ip_table where hostname = %s'''
                        cursor.execute(query,(os.getenv("platform-url"),))
                        conn.commit()
                        result = cursor.fetchone()
                        print(result)
                        if len(result) > 0:
                            json_data["source"].append(" - " + result[0])
                    except Exception as E:
                        pass
                        # no conversion for ip, not a big deal
                try:
                    form_dict = request.form.to_dict()
                    amount_of_lines = form_dict.pop('top_lines')
                    json_data['processes']=json_data['processes'][:int(amount_of_lines)]
                except Exception as E:
                    json_data['processes']=json_data['processes'][:40]
                if os.getenv("is-master"):
                    jsontobereturned = {"result":json_data, "error":[]}
                    return render_template("top-viewer.html", data=jsontobereturned), 200
                else:
                    return json_data
        return render_template("error_showing.html", r = "You are not authenticated"), 403
    

    @app.route("/get_top", methods=["GET"])
    def get_top_single():
        if 'username' in session:
            return get_local_top()
        return render_template("error_showing.html", r = "You are not authenticated"), 403
        

    @app.route("/organize_containers", methods=["GET"])
    def organize_containers():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''SELECT * FROM checker.component_to_category;'''
                    query2 = '''SELECT category from categories;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    cursor.execute(query2)
                    conn.commit()
                    results_2 = cursor.fetchall()
                    return render_template("organize_containers.html",containers=results, categories=results_2,timeout=int(os.getenv("requests-timeout")))
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_container", methods=["POST"])
    def add_container():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''INSERT INTO `checker`.`component_to_category` (`component`, `category`, `references`) VALUES (%s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],request.form.to_dict()['category'],request.form.to_dict()['contacts'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new container because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_container", methods=["POST"])
    def delete_container():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''DELETE FROM `checker`.`component_to_category` WHERE (`component` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    @app.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            print(username)
            print(check_password_hash(users[username], password))
            if username in users and check_password_hash(users[username], password):
                session.permanent = True
                session['username'] = username
                return redirect(url_for('main_page'))
            return "Invalid credentials", 401
        return render_template('login.html')

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route("/get_data_from_source", methods=["GET"])
    def get_additional_data():
        if 'username' in session:
            try:
                response = requests.get(request.args.to_dict()['url_of_resource'])
                response.raise_for_status()
                return response.text
            except Exception:
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/get_complex_test_buttons")
    def get_complex_test_buttons():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''SELECT complex_tests.*, GetHighContrastColor(button_color), COALESCE(categories.category, "System") as category FROM checker.complex_tests left join category_test on id = category_test.test left join categories on categories.idcategories = category_test.category;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    return results
            except Exception:
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/container_is_okay", methods=['POST'])
    def make_category_green():
        if 'username' in session:
            if request.method == "POST":
                try:
                    with mysql.connector.connect(**db_conn_info) as conn:
                        cursor = conn.cursor(buffered=True)
                        update_categories_query=f"""UPDATE `checker`.`summary_status` SET `status` = %s WHERE (`category` = %s);"""
                        cursor.execute(update_categories_query, (greendot, request.form.to_dict()['container'],))
                        conn.commit()
                        return "👌"
                except Exception:
                    send_alerts("Can't reach db due to",traceback.format_exc())
                    return render_template("error_showing.html", r =  "There was a problem: "+traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/read_containers", methods=['POST'])
    def check():
        if 'username' in session:
            return get_container_data()
        return redirect(url_for('login'))
            
    def send_request(url, headers):
        return requests.post(url, headers=headers)
    
    @app.route("/read_containers_db", methods=['GET'])
    def check_container_db():
        if 'username' in session:
            if not os.getenv("is-master"):
                return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster"), 403
            with mysql.connector.connect(**db_conn_info) as conn:
                try:
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT containers, sampled_at FROM checker.container_data order by sampled_at desc limit 1;'''
                    cursor.execute(query)
                    conn.commit()
                    result = cursor.fetchone()
                    tobereturned_answer = {"result":json.loads(result[0]), "error":[]}
                except Exception as E:
                    tobereturned_answer = {"result": {}, "error":["Couldn't load container data because of "+str(E)]}
                return tobereturned_answer
        return redirect(url_for('login'))

    def get_container_categories():
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT * FROM checker.component_to_category;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    
    def get_extra_data():
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT category, resource_address, resource_description, resource_information FROM checker.extra_resources join categories on categories.idcategories = extra_resources.id_category;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return "Error in get extra data!"
        
    @app.route("/run_test", methods=['POST'])
    def run_test():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''select command, command_explained, id from tests_table where container_name =%s;'''
                    cursor.execute(query, (request.form.to_dict()['container'],))
                    conn.commit()
                    results = cursor.fetchall()
                    total_result = ""
                    command_ran_explained = ""
                    for r in list(results):
                        command_ran = subprocess.run(r[0], shell=True, capture_output=True, text=True, encoding="cp437").stdout
                        command_ran_explained = subprocess.run(r[1], shell=True, capture_output=True, text=True, encoding="cp437").stdout + '\n'
                        total_result += "Running " + r[0] + " with result " + command_ran
                        query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                        cursor.execute(query_1,(command_ran, request.form.to_dict()['container'],r[0],))
                        conn.commit()
                        log_to_db('test_ran', "Executing the is alive test on "+request.form.to_dict()['container']+" resulted in: "+command_ran, request, which_test="is alive " + str(r[2]))
                    return jsonify(total_result, command_ran_explained)
            except Exception:
                print("Something went wrong during tests running because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
        
    @app.route("/run_test_complex", methods=['POST'])
    def run_test_complex():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''select command, id from complex_tests where name_of_test =%s;'''
                    form_dict = request.form.to_dict()
                    test_name = form_dict.pop('test_name')
                    cursor.execute(query, (test_name,))
                    conn.commit()
                    results = cursor.fetchall()
                    total_result = ""
                    for r in list(results):
                        arguments_test = " "
                        for key, value in form_dict.items():
                            arguments_test+='-'+key+' "'+value+'" '
                        command_ran = subprocess.run(r[0]+arguments_test, shell=True, capture_output=True, text=True, encoding="cp437")
                        if len(command_ran.stderr) > 0:
                            string_used = '<p style="color:#FF0000";>'+command_ran.stderr+'</p> '+command_ran.stdout
                        else:
                            string_used = command_ran.stdout
                        total_result += string_used
                        query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                        cursor.execute(query_1,(string_used, test_name,r[0],))
                        conn.commit()
                        log_to_db('test_ran', "Executing the complex test " + test_name + " resulted in: " +string_used, request, which_test="advanced test - "+str(r[1]))
                    return jsonify(total_result)
            except Exception:
                print("Something went wrong during tests running because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/reboot/<container_id>", methods=['POST', 'GET'])
    def reboot(container_id):
        if 'username' in session:
            try:
                return render_template("reboot.html", container=container_id)
            except Exception:
                print("Something went wrong during rebooting because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
        
    @app.route("/test_all_ports", methods=['GET'])
    def test_all_ports():
        if 'username' in session:
            result = {}
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''select container_name, command from tests_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                for r in list(results):
                    command_ran = subprocess.run(r[1], shell=True, capture_output=True, text=True, encoding="cp437").stdout
                    result[r[0]]=command_ran
            return result
        return redirect(url_for('login'))
            
    @app.route("/deauthenticate", methods=['POST','GET'])
    def deauthenticate():
        session.clear()
        return "You have been deauthenticated", 401
        
    @app.route("/reboot_container", methods=['POST'])
    def reboot_container():
        if 'username' in session:
            if request.method == "POST":
                something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
                psw = something[something.find(":")+1:]
                if psw == request.form.to_dict()['psw']:
                    result = queued_running('kubectl rollout restart deployments/'+request.form.to_dict()['id']).stdout
                    log_to_db('rebooting_containers', 'kubernetes restart '+request.form.to_dict()['id']+' resulted in: '+result, request)
                    return result
                else:
                    log_to_db('rebooting_containers', 'wrong authentication while restarting '+request.form.to_dict()['id'], request)
                    return "Container not rebooted", 401
            else: 
                log_to_db('rebooting_containers', "POST wasn't used in the request", request)
                return "False"
        return redirect(url_for('login'))
            
    @app.route("/get_muted_components", methods=['GET'])
    def get_muted_components():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''select * from telegram_alert_pauses where until > now();'''
                    cursor.execute(query,)
                    conn.commit()
                    results = cursor.fetchall()
                    if len(results) > 1:
                        return results, 200
                    else:
                        return [results], 200
            except Exception:
                print("Something went wrong during getting the muted components because:",traceback.format_exc())
                return traceback.format_exc(), 500
        return redirect(url_for('login'))
            
    @app.route("/mute_component_by_hours", methods=['POST'])
    def mute_component_by_hours():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''INSERT INTO telegram_alert_pauses (`component`, `until`) VALUES (%s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],(datetime.now() + timedelta(hours=int(request.form.to_dict()['hours']))).strftime("%Y-%m-%d %H:%M:%S"),))
                    conn.commit()
                    return "ok", 200
            except Exception:
                print("Something went wrong during muting a component because of:",traceback.format_exc())
                return traceback.format_exc(), 500
        return redirect(url_for('login'))
        
    @app.route("/tests_results", methods=['POST'])
    def get_tests():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''WITH RankedEntries AS ( 
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY container ORDER BY datetime DESC) AS row_num FROM tests_results
                        ) 
                        SELECT * FROM RankedEntries WHERE row_num = 1;'''
                    cursor.execute(query)
                    conn.commit()
                    log_to_db('getting_tests', 'Tests results were read', request)
                    results = cursor.fetchall()
                    return jsonify(results)
            except Exception:
                print("Something went wrong because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    # this is only called serverside
    def log_to_db(table, log, _=None, which_test=""): #FIXME, remove 3rd param from other calls
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                if table != "test_ran":
                    cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator) VALUES (NOW(),'{}','{}')'''.format(table, log.replace("'","''"), session['username']))
                else:
                    cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator, test) VALUES (NOW(),'{}','{}','{}')'''.format(table, log.replace("'","''"), session['username'], which_test))
                conn.commit()
        except Exception:
            print("Something went wrong during db logging because of:",traceback.format_exc(), "- in:",table)
            
    @app.route("/load_db",methods=['POST'])
    def load_db():
        if 'username' in session:
            trying_to_load_db_resulted_in = subprocess.run(f'mysql -u {os.getenv("db-user")} --password={os.getenv("db-passwd")} -D checker < just_complex.sql', shell=True, capture_output=True, text=True, encoding="utf_8")
            out = trying_to_load_db_resulted_in.stdout
            err = trying_to_load_db_resulted_in.stderr
            if "mysql: [Warning] Using a password on the command line interface can be insecure" in err:
                err = ""
            else:
                err = '<p style="color:#FF0000";>'+err+'</p>'
            if len(err)==0 and len(out)==0:
                out = '<input type="button" name="db-success" id="db-success" value="Success! Click to reload" class="form-control" onclick="location.reload()"/>'
            return err+out
        return redirect(url_for('login'))
    
    
    @app.route("/get_complex_tests", methods=["GET"])
    def get_complex_tests():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''WITH RankedEntries AS ( 
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY container ORDER BY datetime DESC) AS row_num FROM tests_results
                        ) 
                        SELECT * FROM RankedEntries WHERE row_num = 1;'''
                    cursor.execute(query)
                    conn.commit()
                    log_to_db('getting_tests', 'Tests results were read', request)
                    results = cursor.fetchall()
                    return jsonify(results)
            except Exception:
                print("Something went wrong because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/container/<podname>")
    def get_container_logs(podname):
        if 'username' in session:
            process = subprocess.Popen(
                'kubectl logs '+podname+" --tail "+str(int(os.getenv("default-log-length"))),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                text=True
            )
            out=[]
            for line in iter(process.stdout.readline, ''):
                out.append(line[:-1])
            process.stdout.close()
            r = '<br>'.join(out)
            return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
        return redirect(url_for('login'))
            
    @app.route("/get_summary_status")
    def get_summary_status():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    cursor.execute('''SELECT * FROM summary_status;''')
                    results = cursor.fetchall()
                    return jsonify(results)
            except Exception:
                print("Something went wrong during db logging because of:",traceback.format_exc())
        return redirect(url_for('login'))
    
    def get_container_data(do_not_jsonify=False):
        if not os.getenv("running_as_kubernetes"):
            containers_ps = [a for a in (subprocess.run('docker ps --format json -a', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
            containers_stats = [b for b in (subprocess.run('docker stats --format json -a --no-stream', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
            containers_merged = []
            for container_stats in containers_stats:
                for container_ps in containers_ps:
                    for key1, value1 in json.loads(container_stats).items():
                        for key2, value2 in json.loads(container_ps).items():
                            if key1 == "Name" and key2 == "Names":
                                if value1 == value2:
                                    containers_merged.append({**json.loads(container_ps), **json.loads(container_stats)})
            if do_not_jsonify:
                return containers_merged
            return jsonify(containers_merged)
        else:
            raw_json = json.loads(subprocess.run('kubectl get pods -o json',shell=True, capture_output=True, text=True, encoding="utf_8").stdout)
            conversions=[]
        for item in raw_json["items"]:
            conversion = {}
            try:
                command = item.get("command", [])
                args = item.get("args", [])
                full_command = command + args
                if full_command:
                    conversion["Command"] = full_command
            except Exception as E: # no command set, read from image
                #conversion["Command"] = subprocess.run(f"kubectl exec {item['metadata']['name']} -n {namespace} -- cat /proc/1/cmdline | tr '\0' ' '", shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                conversion["Command"] = "Command not found"
            conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
            conversion["ID"] = item["metadata"]["uid"]
            conversion["Image"] = item["spec"]["containers"][0]["image"]
            conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
            #conversion["LocalVolumes"] = "Whatever"
            conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
            conversion["Names"] = item["metadata"]["name"]
            #conversion["Networks"] = "Whatever"
            conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])

            fmt = "%Y-%m-%dT%H:%M:%SZ"
            dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
            dt2 = datetime.now()
            try:
                conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minutes(s) and {(dt2-dt1).seconds % 60} second(s)"
            except Exception as E:
                print(E)
                conversion["RunningFor"] = "Not running"
            #conversion["Size"] = "Whatever"
            conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0]
            conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
            #conversion["BlockIO"] = "Whatever"
            #conversion["CPUPerc"] = "Whatever"
            conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
            #conversion["MemPerc"] = "Whatever"
            #conversion["MemUsage"] = "Whatever"
            conversion["Name"] = item["metadata"]["name"]
            #conversion["NetIO"] = "Whatever"
            #conversion["PIDs"] = "Whatever"

            # new things
            conversion["Node"] = item["spec"]["nodeName"]
            temp_vols=copy.deepcopy(item["spec"]["volumes"])
            temp_str = ""
            for vol_num in range(len(item["spec"]["volumes"])):
                temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                del temp_vols[vol_num]["name"]
                temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                
            conversion["Volumes"] = temp_str
            conversion["Namespace"] = item["metadata"]["namespace"]
            
            
            conversions.append(conversion)
        return jsonify(conversions)
    
    @app.route("/generate_pdf", methods=['GET'])
    def generate_pdf():
        if 'username' in session:
            data_stored = []
            for container_data in get_container_data(True):
                process = subprocess.Popen(
                    'kubectl logs '+container_data['ID']+" --tail "+str(os.getenv("default-log-length")),
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                    text=True
                )
                out=[]
                for line in iter(process.stdout.readline, ''):
                    out.append(line[:-1])
                process.stdout.close()
                r = '<br>'.join(out)
                #r = '<br>'.join(subprocess.run('docker logs '+container_data['ID'] + ' --tail '+os.getenv("default-log-length"), shell=True, capture_output=True, text=True, encoding="utf_8").stdout.split('\n'))
                data_stored.append({"header": container_data['Name'], "string": r})
            
            # Create a PDF document
            subfolder = "pdf"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            pdf_output_path = subfolder+"/logs.pdf"
            os.makedirs(subfolder)
            doc = SimpleDocTemplate(pdf_output_path, pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            # Initialize list to store content
            content = []
            extra_logs = []
            tests_out = None
            extra_tests = []
            
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''WITH RankedEntries AS ( 
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY container ORDER BY datetime DESC) AS row_num FROM tests_results
                        ) 
                        SELECT * FROM RankedEntries WHERE row_num = 1;'''
                    cursor.execute(query)
                    conn.commit()
                    log_to_db('getting_tests', 'Tests results were read', request)
                    results = cursor.fetchall()
                    tests_out = results
            except Exception:
                print("Something went wrong because of:",traceback.format_exc())
            # index
            content.append(Paragraph("The following are hyperlinks to logs of each container.", styles["Heading1"]))
            for pair in data_stored:
                if pair["header"] in ['dashboard-backend','myldap']:
                    continue
                content.append(Paragraph(f'<a href="#c-{pair["header"]}" color="blue">Container {pair["header"]}</a>', styles["Normal"]))
            current_dir = os.path.dirname(os.path.abspath(__file__))
            for root, dirs, files in os.walk(os.path.join(current_dir, os.pardir)): #maybe doesn't find the files while clustered but continues gracefully
                if 'log.txt' in files:
                    #logs_file_path = os.path.join(root, 'log.txt')
                    log_output = subprocess.run(f'cd {root}; tail -n {os.getenv("default-log-length")} log.txt', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                    content.append(Paragraph('<a href="#iot-directory-log" color="blue">iot-directory-log</a>', styles["Normal"]))
                    extra_logs.append(Paragraph(f'<b><a name="iot-directory-log"></a>iot-directory-log</b>', styles["Heading1"]))
                    extra_logs.append(Paragraph(log_output.replace("\n","<br></br>"), styles["Normal"]))
                    break  # Stop searching after finding the first occurrence
            for test in tests_out:
                if not test:
                    break
                content.append(Paragraph(f'<a href="#t-{test[3]}" color="blue">Test of {test[3]}</a>', styles["Normal"]))
                extra_tests.append(test)
            content.append(PageBreak())
            
            
            # Iterate over pairs
            for pair in data_stored:
                if pair["header"] in ['dashboard-backend','myldap']:
                    continue
                header = pair["header"]
                string = pair["string"]
                strings = string.split("<br>")
                # Add header to content
                content.append(Paragraph(f'<b><a name="c-{header}"></a>{header}</b>', styles["Heading1"]))
                # Add normal string if it exists
                for substring in strings:
                    try:
                        content.append(Paragraph(substring, styles["Normal"]))
                    except ValueError:
                        content.append(Paragraph(html(substring), styles["Normal"]))
                content.append(PageBreak())
            for extra in extra_logs:
                content.append(extra)
            content.append(PageBreak())
            for test in extra_tests:
                content.append(Paragraph(f'<b><a name="t-{test[3]}"></a>{test[3]}</b>', styles["Heading1"]))
                content.append(Paragraph(test[2].replace("\n","<br>").replace("<br>","<br></br>"), styles["Normal"]))
                content.append(PageBreak())
            # Add content to the PDF document
            doc.build(content)
            # Send the PDF file as a response
            response = send_file(pdf_output_path)
            return response
        return redirect(url_for('login'))
        
    def find_target_folder(parent_folder):  #TODO won't work as intended in k8s
        for root, dirs, files in os.walk(parent_folder):
            if "docker-compose.yml" in files and "setup.sh" in files:
                return root
        return None
        
    @app.route("/download")
    def redirect_to_download():
        if 'username' in session:
            return redirect('/sentinel/downloads/')
        return redirect(url_for('login'))
    
    @app.route("/downloads/")
    @app.route("/downloads/<path:subpath>")
    def list_files(subpath=''):
        if 'username' in session:
            # Determine the full path relative to the base directory
            full_path = os.path.join(os.path.join(os.getcwd(), "certifications/"), subpath)
            if ".." in subpath:
                return render_template("error_showing.html", r = "Issues during the retrieving of the resource: illegal path"), 500
            # If it's a directory, list contents
            if os.path.isdir(full_path):
                try:
                    files = os.listdir(full_path)
                    files_list = [{"name": f, "data": [os.path.join(subpath, f)]} for f in files]
                    for a in files_list:
                        if a['name'] in next(os.walk(full_path))[1]:
                            a['data'].append('dir')
                        else:
                            a['data'].append('file')
                    return render_template("download_files.html", files=files_list, subpath=subpath)
                except FileNotFoundError:
                    return render_template("error_showing.html", r = "Issues during the retrieving of the folder: "+ traceback.format_exc()), 500
            # If it's a file, serve the file
            elif os.path.isfile(full_path):
                directory = os.path.dirname(full_path)
                filename = os.path.basename(full_path)
                return send_from_directory(directory, filename, as_attachment=True)
            else:
                return render_template("error_showing.html", r = "Issues during the retrieving of the file: "+ traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/clear_certifications", methods=['GET'])
    def clear_certifications():
        return "Suppressed", 500
        user = ""
        try:
            user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
            user = user[:user.find(":")]
        except Exception:
            return render_template("error_showing.html", r = "Issues during the establishing of the user: "+ traceback.format_exc()), 500
        if user != "admin":
            return render_template("error_showing.html", r = "User is not authorized to perform the operation."), 401
        script_folder = os.path.dirname(os.path.abspath(__file__))
        parent_folder = os.path.dirname(script_folder)
        target_folder = find_target_folder(parent_folder)
        if target_folder:
            clear_rars = subprocess.run(f'cd {target_folder}; rm -f *snap4city*-certification-*.rar', shell=True, capture_output=True, text=True, encoding="utf_8")
            return "Done"
        
    
    @app.route("/certification", methods=['GET'])
    def certification():
        if 'username' in session:
            if session['username'] != "admin":
                return render_template("error_showing.html", r = "User is not authorized to perform the operation."), 401
            try:
                subfolder = "cert"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
                script_to_run = "/app/scripts/make_dumps_of_database.sh"
                if os.getenv("running_as_kubernetes"):
                    script_to_run = "/app/scripts/make_dumps_of_database_k8.sh"
                make_certification = subprocess.run(f'cd {os.getenv("conf_path")}; mkdir {subfolder}; bash {script_to_run}; rar a -k -p{password} snap4city-certification-{password}.rar iotapp-00*/flows.json d*conf iot-directory-conf m*conf n*conf ownership-conf/config.php nifi/conf servicemap-conf/servicemap.properties ../placeholder_used.txt *dump.* servicemap-iot-conf/iotdeviceapi.dtd servicemap-superservicemap-conf/settings.xml synoptics-conf/ mongo_dump virtuoso_dump php ../checker/*; cp snap4city-certification-{password}.rar {subfolder}/snap4city-certification-{password}.rar', shell=True, capture_output=True, text=True, encoding="utf_8")
                if len(make_certification.stderr) > 0:
                    print(make_certification.stderr)
                    return send_file(f'/confs/{subfolder}/snap4city-certification-{password}.rar')
                else:
                    return send_file(f'/confs/snap4city-certification-{password}.rar')
            except Exception:
                return render_template("error_showing.html", r = f"Fatal error while generating configuration: {traceback.format_exc()}"), 401
        return redirect(url_for('login'))
            
    @app.route("/clustered_certification", methods=['GET'])
    def clustered_certification(): # probably unneeded
        return "Suppressed", 500
        if 'username' in session:
            if session['username'] != "admin":
                return render_template("error_showing.html", r = "User is not authorized to perform the operation"), 401
            try:
                results = None
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT distinct position FROM checker.component_to_category;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    error = False
                    errorText = ""
                    subfolder = "certifications/certcluster"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    subprocess.run(f'rm -f *snap4city*-certification-*.rar', shell=True)
                    for r in results:
                        file_name, content_disposition = "", ""
                        obtained = requests.get(r[0]+"/sentinel/certification", headers=request.headers)
                        if 'Content-Disposition' in obtained.headers:
                            content_disposition = obtained.headers['Content-Disposition']
                        if 'filename=' in content_disposition:
                            file_name = content_disposition.split('filename=')[1].strip('"')
                        if len(file_name) < 1:
                            errorText += "Unable to recover password from sentinel located at " + r[0] + "\n"
                            error = True
                        if obtained.status_code == 200 and len(file_name) > 1:
                            with open(urlparse(r[0]).hostname + ' - ' +file_name, "wb+") as file:
                                if not error:
                                    file.write(obtained.content)
                        else:
                            error = True
                            errorText += "Couldn't read file from sentinel located at " + r[0] + " because of error in request: "+ str(obtained.status_code) + '\n'
                    if error:
                        return render_template("error_showing.html", r = errorText.replace("\n","<br>")), 500
                    else:
                        password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
                        subprocess.run(f'rar a -k -p{password} snap4city-clustered-certification-{password}.rar *snap4city-certification-*.rar; mkdir -p {subfolder}; cp snap4city-clustered-certification-{password}.rar {subfolder}/snap4city-clustered-certification-{password}.rar', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                        return send_file(f'snap4city-clustered-certification-{password}.rar')
            except Exception:
                return render_template("error_showing.html", r = traceback.format_exc()), 500
    return app
    
if __name__ == "__main__":
    create_app().run(host='localhost', port=4080)
