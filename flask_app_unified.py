
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
import random
import string
import traceback
from urllib.parse import urlparse
from datetime import datetime, timedelta
import re
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from datetime import timedelta
import html
import jwt
import asyncio

ALGORITHM = 'HS256'
def string_of_list_to_list(string):
    try:
        a = string[1:-1]
        a = a.replace('"',"")
        a = a.replace("'","")
        ret = a.split(",")
        return [b.strip() for b in ret]
    except:
        raise Exception("Couldn't do it")

USERS_FILE = 'users.txt'

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

for key, value in config.items():
    if not os.getenv(key):
        os.environ[key] = value

bot_2 = Snap4SentinelTelegramBot(os.getenv("telegram-api-token"), int(os.getenv("telegram-channel")))
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
    if not os.getenv("running_as_kubernetes"):
        using_these = ', '.join('"{0}"'.format(w).strip() for w in containers.split(", "))
    else:
        using_these = '|'.join('^{0}'.format(w).strip() for w in containers.split(", "))
    if because:
        becauses=because.split(",")
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        if not os.getenv("running_as_kubernetes"):
            query2 = 'SELECT category, component, position FROM checker.component_to_category where component in ({}) order by category;'.format(using_these)
        else:
            query2 = '''SELECT category, component, position FROM checker.component_to_category WHERE component REGEXP '{}' ORDER BY category;'''.format(using_these)
        cursor.execute(query2)
        now_it_is = cursor.fetchall()
    newstr=""
    for a in now_it_is:
        if not os.getenv("running_as_kubernetes"):
            curstr="In category " + a[0] + ", located in " + a[2] + " the kubernetes container named " + a[1] + " " + instance_of_problem
        else:
            curstr="In category " + a[0] + ", in namespace " + a[2] + " the kubernetes container named " + a[1] + " " + instance_of_problem
        
        if because:
            try:
                newstr += curstr + explain_reason + becauses.pop(0)+"<br>"
            except IndexError: #somehow ran out of reasons, use the last one
                newstr += curstr + explain_reason + "couldn't find reason"+"<br>"
        else:
            newstr += curstr+"<br>"
    return newstr

def send_telegram(chat_id, message):
    if isinstance(message, list):
        message[2]=filter_out_muted_containers_for_telegram(message[2])
    bot_2.send_message(message, chat_id)
    return

def send_email(sender_email, sender_password, receiver_emails, subject, message):
    composite_message = os.getenv("platform-explanation") + "<br>" + message
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
    print("Email was sent to:",string_of_list_to_list(os.getenv("email-recipients")))
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

async def auto_run_tests():
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''select command, container_name, command_explained from tests_table;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            tasks = [run_shell_command(r[0], r[1]) for r in results]
            completed = await asyncio.gather(*tasks)

            return dict(completed)
    except Exception:
        print("Something went wrong during tests running because of:",traceback.format_exc())

async def run_shell_command(name, command):
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        output = stdout.decode("cp437") if stdout else ""
        error = stderr.decode("cp437") if stderr else ""

        if process.returncode != 0:
            return name, f"Command {command} exited with code {process.returncode}:\n{error}"
        
        return name, output

    except Exception:
        return name, f"Command {command} had an error:\n{traceback.format_exc()}"


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
        if os.getenv("is-multi"):
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT distinct position FROM checker.component_to_category;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                total_answer=[]
                for r in results:
                    obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                    try:
                        total_answer = total_answer + json.loads(obtained)
                    except:
                        try:
                            obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                            total_answer = total_answer + json.loads(obtained)
                        except:
                            pass
            containers_merged = containers_merged + total_answer
    else:
        
        raw_jsons = []
        for a in string_of_list_to_list(os.getenv("namespaces")):
            raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
        conversions=[]
        for raw_json in raw_jsons:
            for item in raw_json["items"]:
                conversion = {}
                try:
                    command = item.get("command", [])
                    args = item.get("args", [])
                    full_command = command + args
                    if full_command:
                        conversion["Command"] = full_command
                except Exception as E: # no command set, read from image
                    conversion["Command"] = "Command not found"
                conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
                conversion["ID"] = item["metadata"]["uid"]
                conversion["Image"] = item["spec"]["containers"][0]["image"]
                try:
                    conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
                except KeyError:
                    conversion["Labels"] = "No labels"
                try:
                    conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
                except KeyError:
                    conversion["Mounts"] = "No volumes"
                conversion["Names"] = item["metadata"]["name"]
                try:
                    conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])
                except KeyError as E:
                    conversion["Ports"] = "No ports"

                fmt = "%Y-%m-%dT%H:%M:%SZ"
                try:
                    dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
                    dt2 = datetime.now()
                    conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minute(s) and {(dt2-dt1).seconds % 60} second(s)"
                except Exception as E:
                    conversion["RunningFor"] = "Not running"
                conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0] + " - restarts: " + str(item["status"]["containerStatuses"][0]["restartCount"])
                conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
                conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
                conversion["Name"] = item["metadata"]["name"]

                # new things
                conversion["Node"] = item["spec"]["nodeName"]
                try:
                    temp_vols=copy.deepcopy(item["spec"]["volumes"])
                    temp_str = ""
                    for vol_num in range(len(item["spec"]["volumes"])):
                        temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                        del temp_vols[vol_num]["name"]
                        temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                        
                    conversion["Volumes"] = temp_str
                except KeyError:
                    conversion["Volumes"] = "No volumes"
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
    is_alive_with_ports = auto_run_tests() # check namespace here if k8s
    components = [a[0].replace("*","") for a in results]
    #components_original = [[a[0],a[2]] for a in results]
    components_original = [(a[0][:max(0,a[0].find("*")-1)],a[3]) for a in results]
    containers_which_should_be_running_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and not ("running" in c["State"])]
    
    containers_which_should_be_exited_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in ["certbot"]) and c["State"] != "exited"]
    if not os.getenv("running_as_kubernetes"): #todo troubleshoot here
        containers_which_are_running_but_are_not_healthy = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and "unhealthy" in c["Status"]]
    else:
        containers_which_are_running_but_are_not_healthy=[]
        for c_m in containers_merged:
            if any(c_m["Names"].startswith(value) for value in components):
                if "restarts" in c_m["State"]:
                    try:
                        if int(c_m["State"].strip().split("restarts:")[-1]) > 4:
                            since = sum([int(b[0])*b[1] for b in zip(re.findall("(\d+)", c_m["RunningFor"]),[86400,3600,60,1])])
                            if since>600 or since==0:
                                containers_which_are_running_but_are_not_healthy.append(c_m)
                    except Exception:
                        containers_which_are_running_but_are_not_healthy.append(c_m)
    problematic_containers = containers_which_should_be_exited_and_are_not + containers_which_should_be_running_and_are_not + containers_which_are_running_but_are_not_healthy
    #containers_which_are_fine = list(set([n["Names"] for n in containers_merged]) - set([n["Names"] for n in problematic_containers]))
    names_of_problematic_containers = [n["Names"] for n in problematic_containers]
    if not os.getenv("running_as_kubernetes"): #todo troubleshoot here
        containers_which_are_not_expected = list(set(tuple(item) for item in components_original)-set((('-'.join(b["Names"].split('-')[:-2]),b["Namespace"]) for b in containers_merged)))
        containers_which_are_not_expected = [a for a in containers_which_are_not_expected if not a[0].endswith("*")]
    else:
    
        containers_which_are_not_expected = dict(components_original)
        for c in containers_merged:
            #print("dealing with",c["Names"],"as",'-'.join(c["Names"].split('-')[:-2]))
            for value in list(containers_which_are_not_expected.keys()):
                if '-'.join(c["Names"].split('-')[:-2]).startswith(value):
                    del containers_which_are_not_expected[value]
    
    if not os.getenv("running_as_kubernetes"):
        top = get_top()
        load_averages = re.findall(r"(\d+\.\d+)", top["system_info"]["load_average"])[-3:]
        load_issues=""
        for average, timing in zip(load_averages, [1, 5, 15]):
            if float(average) > int(os.getenv("load-threshold")):
                load_issues += "Load threshold above "+str(int(os.getenv("load-threshold"))) + " with " + str(average) + "during the last " + str(timing) + " minute(s).\n"
        memory_issues = ""
        if float(top["memory_usage"]["used"])/float(top["memory_usage"]["total"]) > int(os.getenv("memory-threshold")):
            memory_issues = "Memory usage above " + str(int(os.getenv("memory-threshold"))) + " with " + str(top["memory_usage"]["used"]) + " " + top["memory_measuring_unit"] + " out of " + top["memory_usage"]["total"] + " " + top["memory_measuring_unit"] + " currently in use\n"
    else:
        load_issues = ""
        memory_issues = ""
    cron_results = []
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''WITH RankedEntries AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY id_cronjob ORDER BY datetime DESC) AS row_num FROM cronjob_history) 
SELECT datetime,result,errors,name,command,categories.category FROM RankedEntries join cronjobs on cronjobs.idcronjobs=RankedEntries.id_cronjob join categories on categories.idcategories=cronjobs.category WHERE row_num = 1 and errors is not NULL;'''
            cursor.execute(query)
            conn.commit()
            cron_results = cursor.fetchall()
    except Exception:
        pass
    if len(names_of_problematic_containers) > 0 or len(is_alive_with_ports) > 0 or len(containers_which_are_not_expected) or len(cron_results)>0:
        try:
            # todo
            # UPDATE `checker`.`summary_status` SET `status` = "&#128308" where `category` in ("System","Broker") # join, set of a list
            issues = ["","","","","",""]
            if len(names_of_problematic_containers) > 0:
                issues[0]=problematic_containers
            if len(is_alive_with_ports) > 0:
                issues[1]=is_alive_with_ports
            if len(containers_which_are_not_expected) > 0:
                issues[2]=[a[0] for a in containers_which_are_not_expected]
            if len(load_issues)>0:
                issues[3]=load_issues
            if len(memory_issues)>0:
                issues[4]=memory_issues
            if len(cron_results)>0:
                issues[5]=cron_results
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
        if os.getenv("is-multi"):
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT distinct position FROM checker.component_to_category;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                total_answer=[]
                for r in results:
                    obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                    try:
                        total_answer = total_answer + json.loads(obtained)
                    except:
                        try:
                            obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                            total_answer = total_answer + json.loads(obtained)
                        except:
                            pass
            containers_merged = containers_merged + total_answer
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''INSERT INTO `checker`.`container_data` (`containers`) VALUES (%s);'''
            cursor.execute(query,(json.dumps(containers_merged),))
            conn.commit()
        
    else:
        raw_jsons = []
        for a in string_of_list_to_list(os.getenv("namespaces")):
            raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
        conversions=[]
        for raw_json in raw_jsons:
            for item in raw_json["items"]:
                conversion = {}
                try:
                    command = item.get("command", [])
                    args = item.get("args", [])
                    full_command = command + args
                    if full_command:
                        conversion["Command"] = full_command
                except Exception as E: # no command set, read from image
                    conversion["Command"] = "Command not found"
                conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
                conversion["ID"] = item["metadata"]["uid"]
                conversion["Image"] = item["spec"]["containers"][0]["image"]
                try:
                    conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
                except KeyError:
                    conversion["Labels"] = "No labels"
                conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
                conversion["Names"] = item["metadata"]["name"]
                conversion["Name"] = item["metadata"]["name"]
                try:
                    conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])
                except KeyError as E:
                    conversion["Ports"] = "No ports"

                fmt = "%Y-%m-%dT%H:%M:%SZ"
                try:
                    dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
                    dt2 = datetime.now()
                    conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minute(s) and {(dt2-dt1).seconds % 60} second(s)"
                except Exception as E:
                    conversion["RunningFor"] = "Not running"
                conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0] + " - restarts: " + str(item["status"]["containerStatuses"][0]["restartCount"])
                conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
                conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
                conversion["Node"] = item["spec"]["nodeName"]
                try:
                    temp_vols=copy.deepcopy(item["spec"]["volumes"])
                    temp_str = ""
                    for vol_num in range(len(item["spec"]["volumes"])):
                        temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                        del temp_vols[vol_num]["name"]
                        temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                    conversion["Volumes"] = temp_str
                except KeyError:
                    conversion["Volumes"] = "No volumes"
                
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
    
def runcronjobs():
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''SELECT * FROM cronjobs;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            for r in list(results):
                print(f"Running {r[1]} cronjob")
                command_ran = subprocess.run(r[2], shell=True, capture_output=True, text=True, encoding="cp437", timeout=10)
                if len(command_ran.stderr) > 0:
                    query = '''INSERT INTO `cronjob_history` (`result`, `id_cronjob`, `errors`) VALUES (%s, %s, %s);'''
                    cursor.execute(query, (command_ran.stdout.strip(),r[0],command_ran.stderr.strip(),))
                else:
                    query = '''INSERT INTO `cronjob_history` (`result`, `id_cronjob`) VALUES (%s, %s);'''
                    cursor.execute(query, (command_ran.stdout.strip(),r[0],))
                conn.commit()
    except Exception:
        print("Something went wrong during cronjobs running because of:",traceback.format_exc())


def send_advanced_alerts(message):
    try:
        container_source = ""
        if not os.getenv("running_as_kubernetes"):
            container_source="docker"
        else:
            container_source="kubernetes"
        text_for_email = ""
        if len(message[0])>0:
            text_for_email = format_error_to_send("is not in the correct status ",containers=", ".join(['-'.join(a["Name"].split('-')[:-2]) for a in message[0]]),because=", ".join([a["State"] for a in message[0]]),explain_reason="as its status currently is: ")+"<br><br>"
        if len(message[1])>0:
            text_for_email+= format_error_to_send("is not answering correctly to its 'is alive' test ",", ".join([a["container"] for a in message[1]]),", ".join([a["command"] for a in message[1]]),"given the failure of: ")+"<br><br>"
        if len(message[2])>0:
            text_for_email+= format_error_to_send(f"wasn't found running in {container_source} ",", ".join(message[2]))+"<br><br>"
        if len(message[3])>0:
            text_for_email+= message[3] + '<br><br>'
        if len(message[4])>0:
            text_for_email+= message[4] + '<br><br>'
        if len(message[5])>0:
            prepare_text = "<br>These cronjobs failed:"
            for failed_cron in message[5]:
                prepare_text += f"<br>Cronjob named {failed_cron[3]} assigned to category {failed_cron[5]} gave {'no result and' if len(failed_cron[1])<1 else 'result of: ' + failed_cron[1] + ' but'} error: {failed_cron[2]} at {failed_cron[0].strftime('%Y-%m-%d %H:%M:%S')}"
            text_for_email += prepare_text + "<br><br>"
        try:
            if len(text_for_email) > 5:
                send_email(os.getenv("sender-email"), os.getenv("sender-email-password"), string_of_list_to_list(os.getenv("email-recipients")), os.getenv("platform-url")+" is in trouble!", text_for_email)
            else:
                print("No mail was sent because no problem was detected")
        except:
            print("[ERROR] while sending with reason:\n",traceback.format_exc(),"\nMessage would have been: ", text_for_email)
        text_for_telegram = ""
        if len(message[0])>0:
            text_for_telegram = "These containers are not in the correct status: " + str(filter_out_wrong_status_containers_for_telegram(message[0])) +"\n"
        if len(message[1])>0:
            text_for_telegram+= 'These containers are not answering correctly to their "is alive" test: '+ str(filter_out_muted_failed_are_alive_for_telegram(message[1]))+"\n"
        if len(filter_out_muted_containers_for_telegram(message[2]))>0:
            text_for_telegram+= f"These containers weren't found in {container_source}: "+ str(filter_out_muted_containers_for_telegram(message[2]))+"\n"
        if len(message[3])>0:
            text_for_telegram+= message[3] +"\n"
        if len(message[4])>0:
            text_for_telegram+= message[4] +"\n"
        if len(message[5])>0:
            text_for_telegram+= str(message[5])
        if len(text_for_telegram)>5:  
            try:
                send_telegram(int(os.getenv("telegram-channel")), text_for_telegram)
            except:
                print("[ERROR] while sending telegram:",text_for_telegram,"\nDue to",traceback.format_exc())
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
update_container_state_db() #on start, populate immediately
scheduler = BackgroundScheduler()
scheduler.add_job(auto_alert_status, trigger='interval', minutes=int(os.getenv("error_notification_frequency",5)))
scheduler.add_job(update_container_state_db, trigger='interval', minutes=int(os.getenv("database_update_frequency")))
scheduler.add_job(isalive, 'cron', hour=8, minute=0)
scheduler.add_job(isalive, 'cron', hour=20, minute=0)
scheduler.add_job(runcronjobs, trigger='interval', minutes=5)
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
                    query = '''SELECT complex_tests.*, GetHighContrastColor(button_color), COALESCE(categories.category, "System") as category FROM checker.complex_tests left join categories on categories.idcategories = complex_tests.category_id;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    if session['username'] != "admin":
                        if not os.getenv("running_as_kubernetes"):
                            return render_template("checker.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),timeout=int(os.getenv("requests-timeout")),user=session['username'])
                        else:
                            return render_template("checker-k8.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),timeout=int(os.getenv("requests-timeout")),user=session['username'])
                    else:
                        query_2 = '''select * from all_logs limit %s;'''
                        cursor.execute(query_2, (int(os.getenv("admin-log-length")),))
                        conn.commit()
                        results_log = cursor.fetchall()
                        if not os.getenv("running_as_kubernetes"):
                            return render_template("checker-admin.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),admin_log=results_log,timeout=int(os.getenv("requests-timeout")),user=session['username'],platform=os.getenv("platform-url"))
                        else:
                            return render_template("checker-admin-k8.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),admin_log=results_log,timeout=int(os.getenv("requests-timeout")),user=session['username'],platform=os.getenv("platform-url"))
                return redirect(url_for('login'))
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500

    @app.route("/get_local_top", methods=["GET"])
    def get_local_top():
        if 'username' in session:
            return get_top()
        return render_template("error_showing.html", r = "You are not authenticated"), 403
    

    @app.route("/get_top", methods=["GET"])
    def get_top_single():  #TODO doesn't do multi yet
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
                    if os.getenv("running_as_kubernetes"):
                        return render_template("organize_containers_k8s.html",containers=results, categories=results_2,timeout=int(os.getenv("requests-timeout")))
                    else:
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
                    query = '''INSERT INTO `checker`.`component_to_category` (`component`, `category`, `references`, `position`) VALUES (%s, %s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],request.form.to_dict()['category'],request.form.to_dict()['contacts'],request.form.to_dict()['namespace']))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new container because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_container", methods=["POST"])
    def edit_container(): #add position if only if docker
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    if not os.getenv("running_as_kubernetes"):
                        query = '''UPDATE `checker`.`component_to_category` SET `references` = %s, `category` = %s, `position` = %s where (`component` = %s)'''
                        cursor.execute(query, (request.form.to_dict()['contacts'],request.form.to_dict()['category'],request.form.to_dict()['position'],request.form.to_dict()['id'],))
                    else:
                        query = '''UPDATE `checker`.`component_to_category` SET `references` = %s, `category` = %s, `position` = `%s` where (`component` = %s)'''
                        cursor.execute(query, (request.form.to_dict()['contacts'],request.form.to_dict()['category'],request.form.to_dict()['namespace'],request.form.to_dict()['id'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
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
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''DELETE FROM `checker`.`component_to_category` WHERE (`component` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    ## start add cronjob
    
    @app.route("/organize_cronjobs", methods=["GET"])
    def organize_cronjobs():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT * FROM checker.cronjobs;'''
                    query2 = '''SELECT * from categories;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    cursor.execute(query2)
                    conn.commit()
                    results_2 = cursor.fetchall()
                    return render_template("organize_cronjobs.html",cronjobs=results, categories=results_2,timeout=int(os.getenv("requests-timeout")))
                    
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_cronjob", methods=["POST"])
    def add_cronjob():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''INSERT INTO `checker`.`cronjobs` (`name`, `command`, `category`) VALUES (%s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['category'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new cronjob because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_cronjob", methods=["POST"])
    def edit_cronjob(): 
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''UPDATE `checker`.`cronjobs` SET `name` = %s, `command` = %s, `category` = %s WHERE (`idcronjobs` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['category'],request.form.to_dict()['id'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
            except Exception:
                print("Something went wrong during the editing of a new cronjob because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_cronjob", methods=["POST"])
    def delete_cronjob():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                if os.getenv('UNSAFE_MODE') != "true":
                    return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                cursor = conn.cursor(buffered=True)
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                query = '''DELETE FROM `checker`.`cronjobs` WHERE (`idcronjobs` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    ## end add cronjob
    
    ## start add extra resource
    
    @app.route("/organize_extra_resources", methods=["GET"])
    def organize_extra_resources():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT * FROM checker.extra_resources;'''
                    query2 = '''SELECT * from categories;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    cursor.execute(query2)
                    conn.commit()
                    results_2 = cursor.fetchall()
                    return render_template("organize_extra_resources.html",extra_resources=results, categories=results_2,timeout=int(os.getenv("requests-timeout")))
                    
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_extra_resource", methods=["POST"])
    def add_extra_resource():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''INSERT INTO `checker`.`extra_resources` ( `resource_address`, `resource_information`, `resource_description`) VALUES (%s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['address'],request.form.to_dict()['information'],request.form.to_dict()['description'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new extra resource because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_extra_resource", methods=["POST"])
    def edit_extra_resource(): 
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''UPDATE `checker`.`extra_resources` SET `resource_address` = %s, `resource_information` = %s, `resource_description` = %s WHERE (`id_category` = %s) and (`resource_address` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['address'],request.form.to_dict()['information'],request.form.to_dict()['description'],request.form.to_dict()['id'],request.form.to_dict()['address'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
            except Exception:
                print("Something went wrong during the editing of a new extra resource because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_extra_resource", methods=["POST"])
    def delete_extra_resource():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                if os.getenv('UNSAFE_MODE') != "true":
                    return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                cursor = conn.cursor(buffered=True)
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                query = '''DELETE FROM `checker`.`extra_resources` WHERE (`id_category` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    ## end add extra resource
    
    ## start add test
    
    @app.route("/organize_tests", methods=["GET"])
    def organize_tests():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT * FROM checker.tests_table;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    return render_template("organize_tests.html",tests=results, timeout=int(os.getenv("requests-timeout")))
                    
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_test", methods=["POST"])
    def add_test():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''INSERT INTO `checker`.`tests_table` (`container_name`, `command`, `command_explained`) VALUES (%s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['container_name'],request.form.to_dict()['command'],request.form.to_dict()['command_explained'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new test because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_test", methods=["POST"])
    def edit_test(): 
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''UPDATE `checker`.`tests_table` SET `container_name` = %s, `command` = %s, `command_explained` = %s WHERE (`id` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['container_name'],request.form.to_dict()['command'],request.form.to_dict()['command_explained'],request.form.to_dict()['id'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
            except Exception:
                print("Something went wrong during the editing of a new test because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_test", methods=["POST"])
    def delete_test():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                if os.getenv('UNSAFE_MODE') != "true":
                    return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                cursor = conn.cursor(buffered=True)
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                query = '''DELETE FROM `checker`.`tests_table` WHERE (`id` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    ## end add test
    
    ## start add complex test
    
    @app.route("/organize_complex_tests", methods=["GET"])
    def organize_complex_tests():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT * FROM checker.complex_tests;'''
                    query2 = '''SELECT * from categories;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    cursor.execute(query2)
                    conn.commit()
                    results_2 = cursor.fetchall()
                    return render_template("organize_complex_tests.html",complex_tests=results, categories=results_2,timeout=int(os.getenv("requests-timeout")))
                    
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_complex_test", methods=["POST"])
    def add_complex_test():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''INSERT INTO `checker`.`complex_tests` (`name_of_test`, `command`, `extraparameters`, `button_color`, `explanation`, `category_id`) VALUES (%s, %s, %s, %s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['extra_parameters'],request.form.to_dict()['button_color'],request.form.to_dict()['explanation'],request.form.to_dict()['category'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new complex test because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_complex_test", methods=["POST"])
    def edit_complex_test(): 
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                    cursor = conn.cursor(buffered=True)
                    query = '''UPDATE `checker`.`complex_tests` SET `name_of_test` = %s, `command` = %s, `extraparameters` = %s, `button_color` = %s, `explanation` = %s, `category_id` = %s WHERE (`id` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['extra_parameters'],request.form.to_dict()['button_color'],request.form.to_dict()['explanation'],request.form.to_dict()['category'],request.form.to_dict()['id'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
            except Exception:
                print("Something went wrong during the editing of a new complex_test because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_complex_test", methods=["POST"])
    def delete_complex_test():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                if os.getenv('UNSAFE_MODE') != "true":
                    return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                
                cursor = conn.cursor(buffered=True)
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                query = '''DELETE FROM `checker`.`complex_tests` WHERE (`id` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        return redirect(url_for('login'))
    
    ## end add complex test
    
    ## start add category
    
    @app.route("/organize_categories", methods=["GET"])
    def organize_categories():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query2 = '''SELECT * from categories;'''
                    cursor.execute(query2)
                    conn.commit()
                    results_2 = cursor.fetchall()
                    return render_template("organize_categories.html",categories=results_2,timeout=int(os.getenv("requests-timeout")))
                    
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/add_category", methods=["POST"])
    def add_category():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''INSERT INTO `checker`.`categories` (`category`) VALUES (%s);'''
                    cursor.execute(query, (request.form.to_dict()['category'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new category because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
    
    @app.route("/edit_category", methods=["POST"])
    def edit_category(): 
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    query = '''UPDATE `checker`.`categories` SET `category` = %s (`idcategories` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['category'],request.form.to_dict()['id'],)) 
                    conn.commit()
                    if cursor.rowcount > 0:
                        return "ok", 201
                    else:
                        return "Somehow request did not result in database changes", 400
            except Exception:
                print("Something went wrong during the editing of a new category because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return redirect(url_for('login'))
        
    @app.route("/delete_category", methods=["POST"])
    def delete_category():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    if session['username']!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    if os.getenv('UNSAFE_MODE') != "true":
                        return render_template("error_showing.html", r = "Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"), 401
                    cursor = conn.cursor(buffered=True)
                    if not check_password_hash(users[username], request.form.to_dict()['psw']):
                        return "An incorrect password was provided", 400
                    query = '''DELETE FROM `checker`.`categories` WHERE (`idcategories` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the editing of a new category because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        
        return redirect(url_for('login'))
    
    ## end add cronjob
    
   
    
    
    
    @app.route("/login", methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
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
    def get_additional_data(): # this should call the db, not directly the webpage
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''SELECT * FROM extra_resources where resource_address = %s;'''
                    cursor.execute(query, (request.form.to_dict()['id'],))
                    conn.commit()
                    try:
                        result = cursor.fetchone()
                    except Exception:
                        return "An unauthorized url was attempted to use", 400
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
                    query = '''SELECT complex_tests.*, GetHighContrastColor(button_color), COALESCE(categories.category, "System") as category FROM checker.complex_tests left join categories on categories.idcategories = complex_tests.category_id;'''
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
        if os.getenv("is-multi"):
            try:
                jwt.decode(request.form.to_dict()['auth'], app.config['SECRET_KEY'], algorithms=[ALGORITHM])
                return get_container_data()
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
        elif 'username' in session:
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
                    
                    if not os.getenv("running_as_kubernetes"):
                        container = request.form.to_dict()['container']
                    else:
                        container = '-'.join(request.form.to_dict()['container'].split('-')[:-2])
                    cursor.execute(query, (container,))
                    conn.commit()
                    results = cursor.fetchall()
                    total_result = ""
                    for r in list(results):
                        try:
                            command_ran = subprocess.run(r[0], shell=True, capture_output=True, text=True, encoding="cp437")
                            total_result += "Running " + r[0] + " with result " + command_ran.stdout + "\nWith errors: " + command_ran.stderr
                            query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                            cursor.execute(query_1,(f"{command_ran.stdout}\n{command_ran.stderr}", request.form.to_dict()['container'],r[0],))
                            conn.commit()
                            log_to_db('test_ran', "Executing the is alive test on "+request.form.to_dict()['container']+" resulted in: "+command_ran.stdout, request, which_test="is alive " + str(r[2]))
                        except Exception:
                            return jsonify(f"Test of {request.form.to_dict()['container']} had a runtime error with the cause: {traceback.format_exc()}"), 500
                    return jsonify(total_result)
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
        
    @app.route("/test_all_ports", methods=['GET'])
    async def test_all_ports():
        if 'username' in session:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''select container_name, command from tests_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                
                tasks = [run_shell_command(r[0], r[1]) for r in results]
                completed = await asyncio.gather(*tasks)

                return dict(completed)
        return redirect(url_for('login'))
            
    @app.route("/deauthenticate", methods=['POST','GET'])
    def deauthenticate():
        session.clear()
        return "You have been deauthenticated", 401
        
    @app.route("/reboot_container", methods=['POST'])
    def reboot_container():
        
        if not os.getenv("running_as_kubernetes"):
            try:
                jwt.decode(request.form.to_dict()['auth'], app.config['SECRET_KEY'], algorithms=[ALGORITHM])
                result = queued_running('docker restart '+request.form.to_dict()['id']).stdout
                log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result, request)
                return result
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            except Exception: #not an intracluster call
                if 'username' in session:
                    result = queued_running('docker restart '+request.form.to_dict()['id']).stdout
                    log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result, request)
                    return result
        else:
            if 'username' in session:
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                try:
                    result = queued_running(f"kubectl rollout restart deployment {'-'.join(request.form.to_dict()['id'].split('-')[:-2])} -n $(kubectl get deployments --all-namespaces | awk '$2==\"{'-'.join(request.form.to_dict()['id'].split('-')[:-2])}\" {{print $1}}')")
                    #result = queued_running('kubectl rollout restart deployments/'+"-".join(request.form.to_dict()['id'].split("-")[:-2])).stdout
                    log_to_db('rebooting_containers', 'kubernetes restart '+request.form.to_dict()['id']+' resulted in: '+result.stdout, request)
                    return result.stdout
                except Exception:
                    return f"Issue while rebooting pod: {traceback.format_exc()}", 500
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
    
    @app.route("/reboot_container_advanced/<container_id>", methods=['POST','GET'])
    def reboot_container_advanced(container_id):
        if not os.getenv("is-multi"):
            return "Disabled for non-clustered environments", 500
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster"), 403
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''SELECT position FROM checker.component_to_category where component=%s;'''
                cursor.execute(query, (container_id,))
                conn.commit()
                results = cursor.fetchall()
                try:
                    r = requests.post(results[0][0]+"/sentinel/reboot_container",  data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)})
                    return r.text
                except:
                    r = requests.post(results[0][0]+"/reboot_container", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)})
                    return r.text
        except Exception:
            print("Something went wrong during advanced container rebooting because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500

            
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
    
    @app.route("/cronjobs", methods=['POST', 'GET'])
    def get_cron_jobs():
        if 'username' in session:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    cursor = conn.cursor(buffered=True)
                    query = '''WITH RankedEntries AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY id_cronjob ORDER BY datetime DESC) AS row_num FROM cronjob_history) 
SELECT datetime,result,errors,name,command,categories.category FROM RankedEntries join cronjobs on cronjobs.idcronjobs=RankedEntries.id_cronjob join categories on categories.idcategories=cronjobs.category WHERE row_num = 1;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    return jsonify(results)
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
            if not os.getenv("running_as_kubernetes"):

                process = subprocess.Popen(
                    'docker logs '+podname+" --tail "+str(config["default-log-length"]),
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
            else:
                prefetch = subprocess.Popen(
               f"kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                    text=True
                )
                namespace = ""
                try:
                    namespace = prefetch.stdout.readlines()[0].strip()
                except IndexError:
                    pass
                if namespace not in string_of_list_to_list(os.getenv("namespaces")):
                    return render_template("error_showing.html", r = f"{podname} wasn't found among the containers"), 500
                process = subprocess.Popen(
               f"""kubectl logs -n $(kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}') {podname} --tail {os.getenv('default-log-length')}""",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                    text=True
                )
                out=[]
                if os.getenv('log_previous_container_if_kubernetes'):
                    process_previous = subprocess.Popen(
               f"""kubectl logs -n $(kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}') {podname} --tail {os.getenv('default-log-length')} --previous""",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                    text=True
                    )
                    for line in iter(process_previous.stdout.readline, ''):
                        out.append(line[:-1])
                for line in iter(process.stdout.readline, ''):
                    out.append(line[:-1])
                
                process.stdout.close()
                r = '<br>'.join(out)
                return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
        
        return redirect(url_for('login'))
        
    @app.route("/advanced_read_containers", methods=['POST'])
    def check_adv():
        if not os.getenv("is-multi"):
            return "Disabled for non-clustered environments", 500
        if not os.getenv('is-master'):
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster"), 403
        try:
            results = None
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT distinct position FROM checker.component_to_category;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                total_answer=[]
                errors=[]
                for r in results:
                    obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                    try:
                        total_answer = total_answer + json.loads(obtained)
                    except:
                        try:
                            obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)}).text
                            total_answer = total_answer + json.loads(obtained)
                        except Exception as E:
                            errors.append("Reading containers from "+r[0]+" failed: the backed received this exception: "+str(E))
                tobereturned_answer = {"result":total_answer, "error":errors}
                return tobereturned_answer
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    
    @app.route("/advanced-container/<container_name>")
    def get_container_logs_advanced(container_name):
        if 'username' in session: # probably unneeded
            try:
                r = get_container_logs(container_name)
                return r.text
            except Exception:
                print("Something went wrong during reading because of:",traceback.format_exc())
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
            
            raw_jsons = []
            for a in string_of_list_to_list(os.getenv("namespaces")):
                raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
            conversions=[]
        for raw_json in raw_jsons:
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
                try:
                    conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
                except KeyError:
                    conversion["Labels"] = "No labels"
                try:
                    conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
                except KeyError:
                    conversion["Mounts"] = "No volumes"
                conversion["Names"] = item["metadata"]["name"]
                try:
                    conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])
                except KeyError as E:
                    conversion["Ports"] = "No ports"

                fmt = "%Y-%m-%dT%H:%M:%SZ"
                try:
                    dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
                    dt2 = datetime.now()
                    conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minute(s) and {(dt2-dt1).seconds % 60} second(s)"
                except Exception as E:
                    conversion["RunningFor"] = "Not running"
                conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0] + " - restarts: " + str(item["status"]["containerStatuses"][0]["restartCount"])
                conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
                conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
                conversion["Name"] = item["metadata"]["name"]

                # new things
                conversion["Node"] = item["spec"]["nodeName"]
                try:
                    temp_vols=copy.deepcopy(item["spec"]["volumes"])
                    temp_str = ""
                    for vol_num in range(len(item["spec"]["volumes"])):
                        temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
                        del temp_vols[vol_num]["name"]
                        temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "
                        
                    conversion["Volumes"] = temp_str
                except KeyError:
                    conversion["Volumes"] = "No volumes"
                conversion["Namespace"] = item["metadata"]["namespace"]
                
                conversions.append(conversion)
        if do_not_jsonify:
            return conversions
        return jsonify(conversions)
    
    @app.route("/generate_pdf", methods=['GET'])
    def generate_pdf(): # no multi
        if 'username' in session:
            data_stored = []
            print(type(get_container_data(True)),str(get_container_data(True)))
            for container_data in get_container_data(True):
                process = subprocess.Popen(
                    f'{"kubectl" if os.getenv("running_as_kubernetes") else "docker"} logs '+container_data['Name']+" --tail "+str(os.getenv("default-log-length") + {"--namespace "+container_data['Namespace'] if os.getenv("running_as_kubernetes") else ""}),
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
            return redirect('/downloads/')
        return redirect(url_for('login'))
    
    @app.route("/downloads/")
    @app.route("/downloads/<path:subpath>")
    def list_files(subpath=''):
        if 'username' in session:
            # Determine the full path relative to the base directory
            full_path = os.path.join(os.path.join(os.getcwd(), "data/"), subpath)
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
                return render_template("error_showing.html", r = "No certification was ever produced"), 500
        return redirect(url_for('login'))
          
    
    @app.route("/certification", methods=['GET'])
    def certification():
        if 'username' in session:
            if session['username'] != "admin":
                try:
                    if jwt.decode(request.form.to_dict()['auth'], app.config['SECRET_KEY'], algorithms=[ALGORITHM])['sub'] == "admin": #maybe authenticate with token
                        pass
                    else:
                        return render_template("error_showing.html", r = "User is not authorized to perform the operation."), 401
                except jwt.ExpiredSignatureError:
                    return jsonify({'error': 'Token expired'}), 401
                except jwt.InvalidTokenError:
                    return jsonify({'error': 'Invalid token'}), 401
                except Exception:
                    return render_template("error_showing.html", r = "Something bad happened: " + traceback.format_exc()), 401
                
            try:
                subfolder = "cert"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
                script_to_run = "/app/scripts/make_dumps_of_database.sh"
                if os.getenv("running_as_kubernetes"):
                    script_to_run = "/app/scripts/make_dumps_of_database_k8.sh"
                make_certification = subprocess.run(f'mkdir -p /app/data; mkdir -p {os.getenv("conf_path")}; cp -r {os.getenv("conf_path")} /app/data/{subfolder}; cd /app/data/{subfolder} && bash {script_to_run} && rar a -k -p{password} snap4city-certification-{password}.rar */ *.*', shell=True, capture_output=True, text=True, encoding="utf_8")
                if len(make_certification.stderr) > 0:
                    print(make_certification.stderr)
                    return send_file(f'/app/data/{subfolder}/snap4city-certification-{password}.rar')
                else:
                    return send_file(f'/app/data/{subfolder}/snap4city-certification-{password}.rar')
            except Exception:
                return render_template("error_showing.html", r = f"Fatal error while generating configuration: {traceback.format_exc()}"), 401
        return redirect(url_for('login'))
            
    @app.route("/clustered_certification", methods=['GET'])
    def clustered_certification():
        if 'username' in session:
            if not os.getenv("is-multi"):
                return "Disabled for non-clustered environments", 500
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
                        obtained = requests.get(r[0]+"/sentinel/certification", data={"auth":jwt.encode({'sub': username,'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, os.getenv("cluster-secret"), algorithm=ALGORITHM)})
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
