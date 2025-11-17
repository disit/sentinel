
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
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory, redirect, url_for, session
from pysnmp.hlapi.v3arch.asyncio import *
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response, FileResponse, JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from threading import Lock
from urllib.parse import urlparse
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash
import asyncio
import copy
import html
import json
import jwt
import mysql.connector
import os
import paramiko
import random
import re
import requests
import smtplib
import string
import subprocess
import time
import traceback
import uvicorn

def oid_tuple(oid_str):
    """Convert OID string to tuple of integers for proper comparison"""
    return tuple(int(x) for x in oid_str.split('.'))

def print_debug_log(log_str):
    if os.getenv("debug","False") == "True":
        print(f"{datetime.now()} DEBUG: {log_str}")

async def safe_snmp_walk(host_data):
    """
    Walk only the relevant OIDs for memory, disk, and CPU.
    Returns a dict {oid: value}.
    """
    print_debug_log("Performing walk for SNMP")
    if host_data['safe']:
        snmpEngine = SnmpEngine()
        transport = await UdpTransportTarget.create((host_data["host"], 161))
        
        user = host_data["user"]
        json_details=json.loads(host_data["details"])
        auth_pass = json_details["auth_pass"]
        priv_pass = json_details["priv_pass"]

        user_data = UsmUserData(
            userName=user,
            authKey=auth_pass,
            privKey=priv_pass,
            authProtocol=usmHMAC384SHA512AuthProtocol, #hardcoded
            privProtocol=usmAesCfb128Protocol #hardcoded
        )

        results = {}

        for base_oid in ["1.3.6.1.2.1.25.2.3.1", "1.3.6.1.2.1.25.3.3.1.2", "1.3.6.1.4.1.2021.10.1.3"]: # hrStorageTable (memory & disk), hrProcessorLoad (CPU), load values
            current_oid = ObjectIdentity(base_oid)
            last_oid = None
            
            

            while True:
                errorIndication, errorStatus, errorIndex, varBinds = await next_cmd(
                    snmpEngine,
                    user_data,
                    transport,
                    ContextData(),
                    ObjectType(current_oid),
                    lexicographicMode=True,
                )

                if errorIndication or errorStatus or not varBinds:
                    break

                stop_walk = False  # <--- flag to break the while loop

                for varBind in varBinds:
                    oid, value = str(varBind[0]), varBind[1].prettyPrint()

                    if not oid.startswith(base_oid):
                        stop_walk = True
                        break

                    if last_oid and oid_tuple(oid) <= oid_tuple(last_oid):
                        stop_walk = True
                        break

                    last_oid = oid
                    results[oid] = value
                    current_oid = ObjectIdentity(oid)

                if stop_walk:
                    break

        snmpEngine.close_dispatcher()
        return results
    else:
        snmpEngine = SnmpEngine()
        transport = await UdpTransportTarget.create((host_data["host"], 161))
        results = {}

        for base_oid in ["1.3.6.1.2.1.25.2.3.1", "1.3.6.1.2.1.25.3.3.1.2", "1.3.6.1.4.1.2021.10.1.3"]: # hrStorageTable (memory & disk), hrProcessorLoad (CPU), load values
            current_oid = ObjectIdentity(base_oid)
            last_oid = None

            while True:
                errorIndication, errorStatus, errorIndex, varBinds = await next_cmd(
                    snmpEngine,
                    CommunityData("public2", mpModel=1),  # SNMPv2c
                    transport,
                    ContextData(),
                    ObjectType(current_oid),
                    lexicographicMode=True
                )

                if errorIndication or errorStatus or not varBinds:
                    break
                
                stop_walk = False  # <--- flag to break the while loop

                for varBind in varBinds:
                    oid, value = str(varBind[0]), varBind[1].prettyPrint()
                    print(oid, value)

                    if not oid.startswith(base_oid):
                        stop_walk = True
                        break

                    if last_oid and oid_tuple(oid) <= oid_tuple(last_oid):
                        stop_walk = True
                        break

                    last_oid = oid
                    results[oid] = value
                    current_oid = ObjectIdentity(oid)
                if stop_walk:
                    break

        snmpEngine.close_dispatcher()
        return results


async def get_system_info_snmp(host):
    # Walk HOST-RESOURCES-MIB
    data = await safe_snmp_walk(host)

    memory = {}
    disk = {}
    cpu = {}

    for oid, value in data.items():
        parts = oid.split('.')
        # hrStorageTable: 1.3.6.1.2.1.25.2.3.1
        if oid.startswith("1.3.6.1.2.1.25.2.3.1"):
            column = int(parts[-2])
            row = parts[-1]
            if row not in memory and row not in disk:
                row_dict = {}
            else:
                row_dict = memory.get(row, disk.get(row, {}))

            if column == 3:
                row_dict['descr'] = value
            elif column == 4:
                row_dict['alloc_unit'] = int(value)
            elif column == 5:
                row_dict['size'] = int(value)
            elif column == 6:
                row_dict['used'] = int(value)

            # classify memory vs disk based on descr
            descr = row_dict.get('descr', '').lower()
            if 'memory' in descr or 'ram' in descr:
                memory[row] = row_dict
            else:
                disk[row] = row_dict

    # CPU: hrProcessorLoad
    cpu_load_oids = {oid: value for oid, value in data.items() if oid.startswith("1.3.6.1.2.1.25.3.3.1.2")}
    if cpu_load_oids:
        cpu_percentages = [int(v) for v in cpu_load_oids.values()]
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        cpu['per_core'] = cpu_percentages
        cpu['average'] = avg_cpu
    load_oids = {
        "1min": "1.3.6.1.4.1.2021.10.1.3.1",
        "5min": "1.3.6.1.4.1.2021.10.1.3.2",
        "15min": "1.3.6.1.4.1.2021.10.1.3.3",
    }
    loads = {k: data.get(oid) for k, oid in load_oids.items()}
    return memory, disk, cpu, loads

async def gather_snmp_info(host):
    memory, disk, cpu, loads = await get_system_info_snmp(host)

    result = {
        "memory": [],
        "disks": [],
        "cpu": {},
        "load_avg": loads
    }

    # Memory
    for row, info in memory.items():
        used_bytes = info.get('used', 0) * info.get('alloc_unit', 1)
        total_bytes = info.get('size', 0) * info.get('alloc_unit', 1)
        result["memory"].append({
            "description": info.get('descr', 'unknown'),
            "used_MB": round(used_bytes / 1024 / 1024, 1),
            "total_MB": round(total_bytes / 1024 / 1024, 1),
        })

    # Disks
    for row, info in disk.items():
        used_bytes = info.get('used', 0) * info.get('alloc_unit', 1)
        total_bytes = info.get('size', 0) * info.get('alloc_unit', 1)
        result["disks"].append({
            "description": info.get('descr', 'unknown'),
            "used_MB": round(used_bytes / 1024 / 1024, 1),
            "total_MB": round(total_bytes / 1024 / 1024, 1),
        })

    # CPU
    if cpu:
        result["cpu"] = {
            "per_core": cpu.get("per_core", []),
            "average": round(cpu.get("average", 0), 1),
        }
    else:
        result["cpu"] = {"error": "No CPU info available via hrProcessorLoad"}

    return result

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

bot_2 = Snap4SentinelTelegramBot(os.getenv("telegram-api-token","0"), int(os.getenv("telegram-channel","0")))
greendot = """&#128994"""
reddot = """&#128308"""

# edit this block according to your mysql server's configuration
db_conn_info = {
    "user": os.getenv("db-user","user"),
    "passwd": os.getenv("db-passwd","password"),
    "host": os.getenv("db-host","localhost"),
    "port": int(os.getenv("db-port","3306")),
    "database": "checker",
    "auth_plugin": 'mysql_native_password'
}

def mixed_format_error_to_send_tests_test_ran(instance_of_problem, containers, because = None, explain_reason=None): #TODO complete this
    # split containers for naming reasons
    
    container_names = [c["container"] for c in containers]
    container_names = '|'.join('^{0}'.format(w).strip() for w in container_names if len(w)>0)
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        matches = []
        if len(container_names)>0:
            query = '''SELECT category, component, position FROM checker.component_to_category WHERE component REGEXP '{}' ORDER BY category;'''.format(container_names)
            cursor.execute(query)
            matches = cursor.fetchall()
        
        if len(matches) ==0:
            return ""  #found nothing
        newstr=""
        for a in matches:
            curstr="In category " + a[0] + ", in namespace " + a[2] + " the container named " + a[1] + " " + instance_of_problem
            if because:
                reason=[c for _,c in enumerate([a for a in because.keys()]) if c.startswith(a[1][:a[1].find("*")])] # container-* matches container-abcdefgh-12345
                
                if len(reason) == 1:
                    use_this_reason=because[reason[0]]
                else:
                    if len(reason) == 0:
                        print_debug_log("fuzzy search failed, trying second one in mixed format error sending")
                        reason=[c for _,c in enumerate([a for a in because.keys()]) if c in a[1]] # container-* matches container
                        if len(reason) == 1:
                            print_debug_log("second fuzzy search succeeded in mixed format error sending")
                            use_this_reason=because[reason[0]]
                        else:
                            if len(reason) == 0:
                                use_this_reason = "couldn't find reason due to a failed container name match (this is a non-critical bug)."
                            else:
                                use_this_reason = "couldn't find reason due to multiple container name matches (this is a non-critical bug)."
                    else:
                        use_this_reason = "couldn't find reason due to multiple container name matches (this is a non-critical bug)."
                try:
                    newstr += curstr + explain_reason + use_this_reason+"<br>"
                except Exception as E:
                    newstr += curstr + explain_reason + "couldn't find reason (this is a non-critical bug): " + traceback.format_exc()+"<br>"
            else:
                newstr += curstr+"<br>"
        return newstr
        

def mixed_format_error_to_send(instance_of_problem, containers, because = None, explain_reason=None): #TODO complete this
    # split containers for naming reasons
    k8s_c = [container for container in containers if container["Namespace"].startswith("Docker")]
    doc_c = [container for container in containers if not container["Namespace"].startswith("Docker")]
    k8s_c_names = '|'.join('^{0}'.format(w).strip() for w in k8s_c["Name"].split(", ") if len(w)>0)
    doc_c_names = ', '.join('"{0}"'.format(w).strip() for w in doc_c["Name"].split(", "))
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        k8s_matches, doc_matches= [], []
        if len(k8s_c_names)>0:
            query_k8s = '''SELECT category, component, position FROM checker.component_to_category WHERE component REGEXP '{}' ORDER BY category;'''.format(k8s_c_names)
            cursor.execute(query_k8s)
            k8s_matches = cursor.fetchall()
        if len(doc_c_names)>0:
            query_doc = 'SELECT category, component, position FROM checker.component_to_category where component in ({}) order by category;'.format(doc_c_names)
            cursor.execute(query_doc)
            doc_matches = cursor.fetchall()
        if len(doc_matches) + len(k8s_matches) == 0:
            return ""  #found nothing
        newstr=""
        for a in k8s_matches:
            curstr="In category " + a[0] + ", in namespace " + a[2] + " the kubernetes container named " + a[1] + " " + instance_of_problem
            if because:
                reason=[c for _,c in enumerate([a for a in because.keys()]) if c.startswith(a[1][:a[1].find("*")])] # container-* matches container-abcdefgh-12345
                
                if len(reason) == 1:
                    use_this_reason=because[reason[0]]
                else:
                    if len(reason) == 0:
                        print_debug_log("fuzzy search failed, trying second one in mixed format error sending")
                        reason=[c for _,c in enumerate([a for a in because.keys()]) if c in a[1]] # container-* matches container
                        if len(reason) == 1:
                            print_debug_log("second fuzzy search succeeded in mixed format error sending")
                            use_this_reason=because[reason[0]]
                        else:
                            if len(reason) == 0:
                                use_this_reason = "couldn't find reason due to a failed container name match (this is a non-critical bug)."
                            else:
                                use_this_reason = "couldn't find reason due to multiple container name matches (this is a non-critical bug)."
                    else:
                        use_this_reason = "couldn't find reason due to multiple container name matches (this is a non-critical bug)."
                try:
                    newstr += curstr + explain_reason + use_this_reason+"<br>"
                except Exception as E:
                    newstr += curstr + explain_reason + "couldn't find reason (this is a non-critical bug): " + traceback.format_exc()+"<br>"
            else:
                newstr += curstr+"<br>"
        for a in doc_matches:
            curstr="In category " + a[0] + ", located in " + a[2] + " the docker container named " + a[1] + " " + instance_of_problem
            if because:
                reason=[c for _,c in enumerate([a for a in because.keys()]) if c==a[1]]
                
                if len(reason) == 1:
                    use_this_reason=because[reason[0]]
                else:
                    if len(reason) == 0:
                        use_this_reason = "couldn't find reason due to a failed container name match (this is a non-critical bug)."
                    else:
                        use_this_reason=because[reason[0]]
                try:
                    newstr += curstr + explain_reason + use_this_reason+"<br>"
                except Exception:
                    newstr += curstr + explain_reason + "couldn't find reason (this is a non-critical bug): " + traceback.format_exc()+"<br>"
            else:
                newstr += curstr+"<br>"
        return newstr

KEY_DIR = "/ssh_keys"
os.makedirs(KEY_DIR, exist_ok=True)



def parse_top(data):
    # Initialize dictionaries to hold parsed data
    print_debug_log("Parsing a top")
    parsed_data = {
        'system_info': {},
        'cpu_usage': {},
        'memory_usage': {},
        'processes': [],
        'memory_measuring_unit': "B"
    }
    
    # Split output into lines
    lines = data.splitlines()
    
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
    cpu_values = re.findall(r'(\d+\,\d+)', cpu_usage_line)
    if len(cpu_values) == 0:
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


def send_telegram(chat_id, message):
    if isinstance(message, list):
        message[2]=filter_out_muted_containers_for_telegram(message[2])
    bot_2.send_message(message, chat_id)
    return

def send_email(sender_email, sender_password, receiver_emails, subject, message):
    if string_of_list_to_list(os.getenv("email-recipients","[]")) == "[]":
        print("Email was not sent, no email address(es) set as recipients")
    composite_message = os.getenv("platform-explanation","No explanation set") + "<br>" + message
    smtp_server = os.getenv("smtp-server","no.server.set")
    if not smtp_server:
        print("MISSING smtp-server, email not sent.")
        return
    smtp_port = int(os.getenv("smtp-port","587"))
    if os.getenv("smtp-type", "starttls") == "ssl":
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
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
    print("Email was sent to:",string_of_list_to_list(os.getenv("email-recipients","[]")))
    return
    

def filter_out_muted_containers_for_telegram(containers):
    print_debug_log("Filtering out muted cotnainers")
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
    print_debug_log("Filtering out failed are alive containers")
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
    print_debug_log("Filtering out wrong status containers")
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
    print_debug_log("Sending 'is alive'")
    send_email(os.getenv("sender-email","unset@email.com"), os.getenv("sender-email-password","unsetpassword"), string_of_list_to_list(os.getenv("email-recipients","[]")), os.getenv("platform-url","unseturl")+" is alive", os.getenv("platform-url","unseturl")+" is alive")
    send_telegram(int(os.getenv("telegram-channel","0")), os.getenv("platform-url","unseturl")+" is alive")
    return

def clean_old_db_entries():
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''DELETE FROM checker.cronjob_history WHERE datetime < curdate() - INTERVAL DAYOFWEEK(curdate())+6 DAY;
DELETE FROM host_data WHERE sampled_at < curdate() - INTERVAL DAYOFWEEK(curdate())+6 DAY;
DELETE FROM snmp_data WHERE sampled_at < curdate() - INTERVAL DAYOFWEEK(curdate())+6 DAY;
DELETE FROM tests_results WHERE datetime < curdate() - INTERVAL DAYOFWEEK(curdate())+6 DAY;'''
            cursor.execute(query,)
            conn.commit()
            print("Weekly deletion of old logs was successful")
    except:
        print("Couldn't delete old logs because: "+traceback.format_exc())
        send_email(os.getenv("sender-email","unset@email.com"), os.getenv("sender-email-password","unsetpassword"), string_of_list_to_list(os.getenv("email-recipients","[]")), os.getenv("platform-url","unseturl")+" didn't delete old logs.", os.getenv("platform-url","unseturl")+" didn't delete old logs because of "+traceback.format_exc())
    
        
def populate_tops_entries():
    print_debug_log("Populating top entries")
    try:
        # Fetch user from DB
        conn = mysql.connector.connect(**db_conn_info)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user, host FROM host;")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        outs = []
        errors = []
        for row in rows:
            try:
                user = row['user']
                host = row['host']
                private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")

                # Connect with key
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(host, username=user, key_filename=private_key_path)

                _, stdout, _ = ssh.exec_command("top -b -n 1")
                output = stdout.read().decode()

                ssh.close()
                generated_json=parse_top(output)
                generated_json["source"] = host
                outs.append(generated_json)
            except:
                error_json = {}
                error_json['host'] = row['host']
                error_json['user'] = row['user']
                error_json['error'] = traceback.format_exc()
                errors.append(error_json)
        for result in outs:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            query = '''INSERT INTO `host_data` (`result`, `host`) VALUES (%s, %s);'''
            cursor.execute(query, (json.dumps(result), result['source']))
            cursor.close()
            conn.commit()
        for result in errors:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            query = '''INSERT INTO `host_data` (`errors`, `host`) VALUES (%s, %s);'''
            cursor.execute(query, (json.dumps(result), result['host']))
            conn.commit()
            cursor.close()
        conn.close()
    except Exception as E:
        print("DEBUG")
        print(outs)
        print(errors)
        raise E



async def auto_run_tests():
    print_debug_log("Automatically running tests")
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''select command, container_name from tests_table;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            print(f"Starting running test (backend): {datetime.now()}")
            tasks = [run_shell_command(r[1], r[0]) for r in results]
            completed = await asyncio.gather(*tasks)
            for test_ran in completed:
                try:
                    query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                    cursor.execute(query_1,(test_ran["result"], test_ran['container'],test_ran['command'],))
                    conn.commit()
                except Exception:
                    print(f"ERROR: failed to insert the result of a test for container {test_ran['container']}")
                            
            return completed
    except Exception:
        print("Something went wrong during tests running because of:",traceback.format_exc())

async def run_shell_command(name, command):
    print_debug_log(f"Running this command: {command}")
    try:
        #print("run_shell_command: start "+name+" cmd:"+command)
        start = time.time()
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except asyncio.TimeoutError:
            process.kill()
            #await process.communicate()  # Clean up
            end = time.time()
            process_return_code = process.returncode
            if not process_return_code:
                process_return_code = "Timed out"
            print("run_shell_command: end "+name+" exception elapsed "+str(end-start)+"s result: "+str(process_return_code))
            return {"container":name, "result": f"Command {command} timed out after 10 seconds.", "command": command} 
        end = time.time()
        #print("run_shell_command: end "+name+" elapsed "+str(end-start)+"s result:"+str(process.returncode))

        output = stdout.decode("cp437") if stdout else ""
        error = stderr.decode("cp437") if stderr else ""
        
        if process.returncode != 0:
            return {"container":name, "result": error, "command": command}
        
        return {"container":name, "result": output, "command": command}

    except Exception:
        return {"container":name, "result": f"Command {command} had an error:\n{traceback.format_exc()}", "command": command}


def auto_alert_status():
    print_debug_log("Starting auto alert status")
    if os.getenv("is-master","False") == "False": #slaves don't send status
        return 
    if "False" == os.getenv("running-as-kubernetes","False"):
        
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
        
        new_containers_merged = []
        source = os.getenv("platform-url","")
        for current in new_containers_merged:
            td = {}
            #td["Command"] = current["Command"]
            td["CreatedAt"] = current["CreatedAt"]
            try: #it is set if it comes from elsewhere
                td["Source"] = current["Source"]
            except:
                td["Source"] = source
            td["ID"] = current["ID"]
            td["Image"] = current["Image"]
            td["Labels"] = current["Labels"]
            td["Mounts"] = current["Mounts"]
            td["Names"] = current["Names"]
            td["Name"] = current["Names"]
            td["Ports"] = current["Ports"]
            td["RunningFor"] = current["RunningFor"]
            td["State"] = current["State"]
            td["Status"] = current["Status"]
            td["Container"] = current["Container"]
            # host origin = node, sorta
            td["Node"] = os.getenv("platform-url","") #current[""]
            td["Volumes"] = current["LocalVolumes"]
            td["Namespace"] = "Docker - " + source
            new_containers_merged.append(td)
    else:
        
        raw_jsons = []
        for a in string_of_list_to_list(os.getenv("namespaces","['default']")):
            raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
        conversions=[]
        source = os.getenv("platform-url","")
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
                conversion["Source"]=source
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
                try:
                    conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
                except KeyError as E:
                    conversion["Container"] = "Container parameter"
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
    if os.getenv("is-multi","True") == "True":
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = f'''SELECT hostname FROM checker.ip_table WHERE hostname != "{os.getenv("platform-url","")}";''' # ask everyone but yourself for extra containers
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            total_answer=[]
            try:
                for r in results:
                    print_debug_log(f"Asking data from {r[0]}")
                    obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                    try:
                        total_answer = total_answer + json.loads(obtained)
                    except:
                        try:
                            obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                            total_answer = total_answer + json.loads(obtained)
                            print(f"Received {obtained[:100]}... from {r[0]}")
                        except Exception as E:
                            print("Error on multi reading container data:", str(E))
            except requests.exceptions.ConnectionError as E: 
                print("Error on multi reading container data:", str(E))
        containers_merged = containers_merged + total_answer
        new_containers_merged = []
        source = os.getenv("platform-url","")
        for current in new_containers_merged:
            td = {}
            #td["Command"] = current["Command"]
            td["CreatedAt"] = current["CreatedAt"]
            try: #it is set if it comes from elsewhere
                td["Source"] = current["Source"]
            except:
                td["Source"] = source
            td["ID"] = current["ID"]
            td["Image"] = current["Image"]
            td["Labels"] = current["Labels"]
            td["Mounts"] = current["Mounts"]
            td["Names"] = current["Names"]
            td["Name"] = current["Names"]
            td["Ports"] = current["Ports"]
            td["RunningFor"] = current["RunningFor"]
            td["State"] = current["State"]
            td["Status"] = current["Status"]
            td["Container"] = current["Container"]
            # host origin = node, sorta
            try:
                td["Node"] = current["Node"]
            except KeyError: #happens when docker data comes also from another sentinel instance
                td["Node"] = os.getenv("platform-url","")
            td["Volumes"] = current["LocalVolumes"]
            td["Namespace"] = "Docker - " + source
            new_containers_merged.append(td)
        containers_merged = new_containers_merged
        
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
    is_alive_with_ports = asyncio.run(auto_run_tests()) # check namespace here if k8s
    is_alive_with_ports = [a for a in is_alive_with_ports if "Failure" in a["result"]] # only keep those who failed
    # begin mixed dealing with docker/kubernetes
    containers_merged_docker = [a for a in containers_merged if a["Namespace"].startswith("Docker - ")]
    containers_merged_kubernetes = [a for a in containers_merged if not a["Namespace"].startswith("Docker - ")]
    
    components_docker = [a[0] for a in results if a[4]=="docker"]
    components_kubernetes = [a[0].replace("*","") for a in results if a[4]=="kubernetes"]
    components_original_docker = [(a[0][:max(0,a[0].find("*")-1)],a[3]) for a in results if a[4]=="docker"]
    components_original_kubernetes = [(a[0][:max(0,a[0].find("*")-1)],a[3]) for a in results if a[4]=="kubernetes"]
    
    containers_which_should_be_running_and_are_not = [c for c in containers_merged_docker if any(c["Names"].startswith(value) for value in components_docker) and not ("running" in c["State"])]
    [containers_which_should_be_running_and_are_not.append(a) for a in [c for c in containers_merged_kubernetes if any(c["Names"].startswith(value) for value in components_kubernetes) and not ("running" in c["State"])]]
    
    containers_which_should_be_exited_and_are_not = [c for c in containers_merged_docker if any(c["Names"].startswith(value) for value in ["certbot"]) and c["State"] != "exited"]
    [containers_which_should_be_exited_and_are_not.append(a) for a in [c for c in containers_merged_kubernetes if any(c["Names"].startswith(value) for value in ["certbot"]) and c["State"] != "exited"]]
    
    containers_which_are_running_but_are_not_healthy = [c for c in containers_merged_docker if any(c["Names"].startswith(value) for value in components_docker) and "unhealthy" in c["Status"]]
    for c_m in containers_merged_kubernetes:
        if any(c_m["Names"].startswith(value) for value in components_kubernetes):
            if "restarts" in c_m["State"]:
                try:
                    if int(c_m["State"].strip().split("restarts:")[-1]) > 4:
                        since = sum([int(b[0])*b[1] for b in zip(re.findall("(\d+)", c_m["RunningFor"]),[86400,3600,60,1])])
                        if since>600 or since==0:
                            containers_which_are_running_but_are_not_healthy.append(c_m)
                except Exception:
                    containers_which_are_running_but_are_not_healthy.append(c_m)
    problematic_containers = containers_which_should_be_exited_and_are_not + containers_which_should_be_running_and_are_not + containers_which_are_running_but_are_not_healthy
    names_of_problematic_containers = [n["Names"] for n in problematic_containers]
    
    containers_which_are_not_expected = list(set(tuple(item) for item in components_original_docker)-set((('-'.join(b["Names"].split('-')[:-2]),b["Namespace"]) for b in containers_merged_docker)))
    containers_which_are_not_expected = [a for a in containers_which_are_not_expected if not a[0].endswith("*")]
    missing_containers_k = dict(components_original_kubernetes)
    containers_which_are_not_expected_k = [a for a in missing_containers_k if not a[0].endswith("*")]
    og_conts = copy.deepcopy(containers_which_are_not_expected_k)
    for c in containers_merged_kubernetes:
        for value,_ in list(missing_containers_k.items()):
            if '-'.join(c["Names"].split('-')[:-2]).startswith(value):
                try:
                    og_conts.remove(value)
                except ValueError:
                    pass
    [containers_which_are_not_expected.append(a) for a in og_conts]
    
    if "False" == os.getenv("running-as-kubernetes","False"):
        top = get_top()
        load_averages = re.findall(r"(\d+\.\d+)", top["system_info"]["load_average"])[-3:]
        load_issues=""
        for average, timing in zip(load_averages, [1, 5, 15]):
            if float(average) > int(os.getenv("load-threshold",1000)):
                load_issues += "Load threshold above "+str(int(os.getenv("load-threshold",1000))) + " with " + str(average) + "during the last " + str(timing) + " minute(s).\n"
        memory_issues = ""
        if float(top["memory_usage"]["used"])/float(top["memory_usage"]["total"]) > int(os.getenv("memory-threshold",1000)):
            memory_issues = "Memory usage above " + str(int(os.getenv("memory-threshold",1000))) + " with " + str(top["memory_usage"]["used"]) + " " + top["memory_measuring_unit"] + " out of " + top["memory_usage"]["total"] + " " + top["memory_measuring_unit"] + " currently in use\n"
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
    populate_tops_entries()
    top_results = []
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''WITH RankedEntries AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY host ORDER BY sampled_at DESC) AS row_num FROM host_data) SELECT host.host as host, sampled_at, data, errors, threshold_cpu, threshold_mem FROM RankedEntries join host on host.host=RankedEntries.host WHERE row_num = 1;'''
            cursor.execute(query)
            conn.commit()
            top_results = cursor.fetchall()
    except Exception:
        pass
    problematic_tops_cpu = []
    problematic_tops_ram = []
    
    top_errors = []
    for top_r in top_results:
        try:
            if len(top_r["error"]) > 0:
                top_errors.append(top_r["error"])
                continue
            regex = r"load average:\s+(\d*,\d*), (\d*,\d*), (\d*,\d*)"
            matches = re.finditer(regex, json.loads(top_r["result"])["system_info"]["load_average"], re.MULTILINE)
            for _, match in enumerate(matches, start=1):
                for groupNum in range(0, len(match.groups())):
                    if (float(match.group(groupNum + 1).replace(",","."))>top_r["threshold_cpu"]):
                        problematic_tops_cpu.append(top_r)
            if float(json.loads(top_r["result"])["memory_usage"]["used"])/float(json.loads(top_r["result"])["memory_usage"]["total"]) > float(top_r["threshold_mem"]):
                problematic_tops_ram.append(top_r)
        except:
            top_errors.append(top_r)
                    
    if len(names_of_problematic_containers) > 0 or len(is_alive_with_ports) > 0 or len(containers_which_are_not_expected) or len(cron_results)>0 or len(problematic_tops_cpu)>0 or len(problematic_tops_ram)>0 or len(top_errors)>0:
        try:
            issues = ["","","","","","","","",""]
            if len(names_of_problematic_containers) > 0:
                issues[0]=problematic_containers
            if len(is_alive_with_ports) > 0:
                issues[1]=is_alive_with_ports
            if len(containers_which_are_not_expected) > 0:
                issues[2]=containers_which_are_not_expected
            if len(load_issues)>0:
                issues[3]=load_issues
            if len(memory_issues)>0:
                issues[4]=memory_issues
            if len(cron_results)>0:
                issues[5]=cron_results
            if len(problematic_tops_cpu)>0:
                issues[6]=problematic_tops_cpu
            if len(problematic_tops_ram)>0:
                issues[7]=problematic_tops_ram
            if len(top_errors)>0:
                issues[8]=top_errors
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
    return
    # end mixed dealing with docker/kubernetes
    
        
def get_top():
    print_debug_log("Getting a top")
    if os.getenv("running-as-kubernetes", "True") == "True":
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
    print_debug_log("Sending alerts")
    try:
        send_email(os.getenv("sender-email","unset@email.com"), os.getenv("sender-email-password","unsetpassword"), string_of_list_to_list(os.getenv("email-recipients","[]")), os.getenv("platform-url","unseturl")+" is in trouble!", message)
        send_telegram(int(os.getenv("telegram-channel","0")), message)
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
def update_container_state_db():
    print_debug_log("Populating database with container data")
    if os.getenv("is-master","False") == "False": #slaves don't write to db
        return 
    if "False" == os.getenv("running-as-kubernetes","False"):
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
        if os.getenv("is-multi","False") == "True":
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT hostname FROM checker.ip_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                total_answer=[]
                try:
                    for r in results:
                        print_debug_log(f"Getting data from {r[0]}")
                        if os.getenv("platform-url","") == r[0]:
                            continue # don't take yourself
                        obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                        try:
                            total_answer = total_answer + json.loads(obtained)
                        except:
                            try:
                                obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                                total_answer = total_answer + json.loads(obtained)
                            except:
                                print(traceback.format_exc())
                except requests.exceptions.ConnectionError:
                    print(traceback.format_exc())
            containers_merged = containers_merged + total_answer
        else:
            print("NOT updating container data as multi...")
        new_containers_merged = []
        source = os.getenv("platform-url","")
        for current in containers_merged:
            td = {}
            td["CreatedAt"] = current["CreatedAt"]
            try: #it is set if it comes from elsewhere
                td["Source"] = current["Source"]
            except:
                td["Source"] = source
            td["ID"] = current["ID"]
            td["Image"] = current["Image"]
            td["Labels"] = current["Labels"]
            td["Mounts"] = current["Mounts"]
            td["Names"] = current["Names"]
            td["Name"] = current["Names"]
            td["Ports"] = current["Ports"]
            td["RunningFor"] = current["RunningFor"]
            td["State"] = current["State"]
            td["Status"] = current["Status"]
            td["Container"] = current["Container"]
            # host origin = node, sorta
            td["Node"] = os.getenv("platform-url","") #current[""]
            try:
                td["Node"] = current["Node"]
            except KeyError: #happens when docker data comes also from another sentinel instance
                td["Node"] = os.getenv("platform-url","")
            try:
                td["Volumes"] = current["LocalVolumes"]
            except KeyError: #happens when docker data comes also from another sentinel instance
                td["Volumes"] = current["Volumes"]
            try: #it is set if it comes from elsewhere
                td["Namespace"] = current["Namespace"]
            except: #happens when docker data comes also from another sentinel instance
                td["Namespace"] = "Docker - " + source
            new_containers_merged.append(td)
        containers_merged = new_containers_merged
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''INSERT INTO `checker`.`container_data` (`containers`) VALUES (%s);'''
            cursor.execute(query,(json.dumps(containers_merged),))
            conn.commit()
        
    else:
        raw_jsons = []
        for a in string_of_list_to_list(os.getenv("namespaces","['default']")):
            raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
        conversions=[]
        source = os.getenv("platform-url","")
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
                conversion["Source"]=source
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
                    conversion["Mounts"] = "No mounts"
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
                try:
                    conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
                except KeyError as E:
                    conversion["Container"] = "Container parameter"
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
        if os.getenv("is-multi","False") == "True":
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT hostname FROM checker.ip_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                total_answer=[]
                try:
                    for r in results:
                        print_debug_log(f"Getting data from {r[0]}")
                        if os.getenv("platform-url","") == r[0]:
                            continue # don't take yourself
                        obtained = requests.post(r[0]+"/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                        try:
                            total_answer = total_answer + json.loads(obtained)
                        except:
                            try:
                                obtained = requests.post(r[0]+"/sentinel/read_containers", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)}).text
                                total_answer = total_answer + json.loads(obtained)
                            except:
                                print(traceback.format_exc())
                except requests.exceptions.ConnectionError:
                    print(traceback.format_exc())
            conversions = conversions + total_answer
        else:
            print("NOT updating container data as multi...")
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
    print("Unlocked executor")
    return answer
    
def runcronjobs():
    print_debug_log("Running cronjobs")
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = f'SELECT * FROM cronjobs where `where_to_run`="{os.getenv("platform-url","")}"'
            if os.getenv("is-master","False") == "True": # the master will run the unassigned ones
                query+="or `where_to_run` is Null"
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            for r in list(results):
                print(f"Running {r[1]} cronjob")
                command_ran = subprocess.run(r[2], shell=True, capture_output=True, text=True, encoding="utf8", timeout=10)
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
    print_debug_log("Preparing the content of an alert")
    try:
        text_for_email = ""
        for a in range(len(message)):
            print(f"Element {a}: "+str(message[a])[:100])
        if len(message[0])>0:
            text_for_email = mixed_format_error_to_send("is not in the correct status ",containers=message[0],because=dict([(a["Name"],a["State"]) for a in message[0]]),explain_reason="as its status currently is: ")+"<br><br>"
        if len(message[1])>0:
            #containers = ", ".join([a["container"] for a in message[1]])
            becauses = dict([[a["container"],a["command"]] for a in message[1]])
            text_for_email+= mixed_format_error_to_send_tests_test_ran("is not answering correctly to its 'is alive' test ",containers=message[1],because=becauses,explain_reason="given the failure of: ")+"<br><br>"    
        if len(message[2])>0:
            text_for_email+= mixed_format_error_to_send(f"wasn't found running in the intended location: ",containers=message[2])+"<br><br>"
        if len(message[3])>0:
            text_for_email+= message[3] + '<br><br>'
        if len(message[4])>0:
            text_for_email+= message[4] + '<br><br>'
        if len(message[5])>0:
            prepare_text = "<br>These cronjobs failed:"
            for failed_cron in message[5]:
                prepare_text += f"<br>Cronjob named {failed_cron[3]} assigned to category {failed_cron[5]} gave {'no result and' if len(failed_cron[1])<1 else 'result of: ' + failed_cron[1] + ' but'} error: {failed_cron[2]} at {failed_cron[0].strftime('%Y-%m-%d %H:%M:%S')}"
            text_for_email += prepare_text + "<br><br>"
        if len(message[6])>0:
            prepare_text_top_cpu = "<br>These hosts are overloaded on cpu:"
            for overloaded_cpu_top in message[6]:
                try:
                    prepare_text_top_cpu += f"<br>Host named {overloaded_cpu_top['host']} ({overloaded_cpu_top['description']}) had load averages above {overloaded_cpu_top['threshold_cpu']}: {json.loads(overloaded_cpu_top['result'])['system_info']['load_average']}</br>"
                except:
                    prepare_text_top_cpu += f"<br>Issue while interpreting cpu top: ({traceback.format_exc()})</br><br> Original object: {str(overloaded_cpu_top)}</br>"
            text_for_email += prepare_text_top_cpu + "<br><br>"
        if len(message[7])>0:
            prepare_text_top_mem = "<br>These hosts are overloaded on memory:"
            for overloaded_mem_top in message[7]:
                try:
                    prepare_text_top_mem += f"<br>Host named {overloaded_mem_top['host']} ({overloaded_mem_top['description']}) had memory load above {overloaded_mem_top['threshold_mem']}%: {json.loads(overloaded_mem_top['result'])['memory_usage']}</br>"
                except:
                    prepare_text_top_mem += f"<br>Issue while interpreting mem top: ({traceback.format_exc()})</br><br> Original object: {str(overloaded_mem_top)}</br>"

            text_for_email += prepare_text_top_mem + "<br><br>"
        if len(message[8])>0:
            prepare_text_top_error = "<br>Couldn't load the tops for these hosts:"
            for error_top in message[8]:
                try:
                    prepare_text_top_error += f"<br>Host named {error_top[0]} couldn't have resources collected because: {json.loads(error_top[3])['error']}</br>"
                except:
                    prepare_text_top_error += f"<br>Issue while interpreting top with errors: ({traceback.format_exc()})</br><br> Original object: {str(error_top)}</br>"
            text_for_email += prepare_text_top_error + "<br><br>"
        try:
            if len(text_for_email) > 15:
                print("Will send email with text:")
                print(text_for_email)
                send_email(os.getenv("sender-email","unset@email.com"), os.getenv("sender-email-password","unsetpassword"), string_of_list_to_list(os.getenv("email-recipients","[]")), os.getenv("platform-url","unseturl")+" is in trouble!", text_for_email)
            else:
                print("No mail was sent because no problem was detected")
        except:
            print("[ERROR] while sending with reason:\n",traceback.format_exc(),"\nMessage would have been: ", text_for_email)
        text_for_telegram = "" #probably needs fixing
        if len(message[0])>0:
            text_for_telegram = "These containers are not in the correct status: " + str(filter_out_wrong_status_containers_for_telegram(message[0])) +"\n"
        if len(message[1])>0:
            text_for_telegram+= 'These containers are not answering correctly to their "is alive" test: '+ str(filter_out_muted_failed_are_alive_for_telegram(message[1]))+"\n"
        if len(filter_out_muted_containers_for_telegram(message[2]))>0:
            text_for_telegram+= f"These containers weren't found in: "+ str(filter_out_muted_containers_for_telegram(message[2]))+"\n"
        if len(message[3])>0:
            text_for_telegram+= message[3] +"\n"
        if len(message[4])>0:
            text_for_telegram+= message[4] +"\n"
        if len(message[5])>0:
            text_for_telegram+= str(message[5])
        if len(message[6])>0:
            prepare_text_top_cpu = "\nThese hosts are overloaded on cpu:"
            for overloaded_cpu_top in message[6]:
                try:
                    prepare_text_top_cpu += f"\nHost named {overloaded_cpu_top['host']} ({overloaded_cpu_top['description']}) had load averages above {overloaded_cpu_top['threshold_cpu']}: {json.loads(overloaded_cpu_top['result'])['system_info']['load_average']}"
                except:
                    prepare_text_top_cpu += f"\nIssue while interpreting cpu top: ({traceback.format_exc()})\n Original object: {str(overloaded_cpu_top)}</br>"
            text_for_telegram += prepare_text_top_cpu + "\n\n"
        if len(message[7])>0:
            prepare_text_top_mem = "\nThese hosts are overloaded on memory:"
            for overloaded_mem_top in message[7]:
                try:
                    prepare_text_top_mem += f"\nHost named {overloaded_mem_top['host']} ({overloaded_mem_top['description']}) had memory load above {overloaded_mem_top['threshold_mem']}%: {json.loads(overloaded_mem_top['result'])['memory_usage']}"
                except:
                    prepare_text_top_mem += f"\nIssue while interpreting mem top: ({traceback.format_exc()})\n Original object: {str(overloaded_mem_top)}</br>"
            text_for_telegram += prepare_text_top_mem + "\n\n"
        if len(message[8])>0:
            prepare_text_top_error = "\nCouldn't load the tops for these hosts:"
            for error_top in message[8]:
                try:
                    prepare_text_top_error += f"\nHost named {error_top[0]} couldn't have resources collected because: {json.loads(error_top[3])['error']}"
                except:
                    prepare_text_top_error += f"\nIssue while interpreting top with errors: ({traceback.format_exc()})\n Original object: {str(error_top)}</br>"

            text_for_telegram += prepare_text_top_error + "\n\n"
        if len(text_for_telegram)>5:  
            try:
                send_telegram(int(os.getenv("telegram-channel","0")), text_for_telegram)
            except:
                print("[ERROR] while sending telegram:",text_for_telegram,"\nDue to",traceback.format_exc())
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
update_container_state_db() #on start, populate immediately
scheduler = BackgroundScheduler()
scheduler.add_job(auto_alert_status, trigger='interval', minutes=int(os.getenv("error-notification-frequency","5")))
scheduler.add_job(update_container_state_db, trigger='interval', minutes=int(os.getenv("database-update-frequency", "2")))
scheduler.add_job(isalive, 'cron', hour=8, minute=0)
scheduler.add_job(isalive, 'cron', hour=20, minute=0)
scheduler.add_job(runcronjobs, trigger='interval', minutes=5)
scheduler.add_job(clean_old_db_entries, 'cron',week=1)
scheduler.start()
auto_alert_status()

templates = Jinja2Templates(directory="templates")
app = Starlette(
    # Flask: app.config["application-root"]
    # Starlette: ASGI root_path
    root_path=os.getenv("application-root", "/")
)

# Sessions: secret + expiration
app.add_middleware(
    SessionMiddleware,
    secret_key="\x8a\x17\x93kT\xc0\x0b6;\x93\xfdp\x8bLl\xe6u\xa9\xf5x",
    max_age=15 * 60  # 15 minutes
)


def main_page(request):
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
                    return templates.TemplateResponse(
                    "checker-k8.html",
                    {"request": request, "extra": results, "categories": get_container_categories(), "extra_data": get_extra_data(), "timeout": int(os.getenv("requests-timeout","15000")), "user": session['username'], "multi": os.getenv("is-multi","False")},
                    status_code=200
                )
                else:
                    query_2 = '''select * from all_logs limit %s;'''
                    cursor.execute(query_2, (int(os.getenv("admin-log-length","1000")),))
                    conn.commit()
                    results_log = cursor.fetchall()
                    return templates.TemplateResponse(
                    "checker-admin-k8.html",
                    {"request": request, "extra": results, "categories": get_container_categories(), "extra_data": get_extra_data(), "admin_log": results_log, "timeout": int(os.getenv("requests-timeout","15000")), "user": session['username'], "platform": os.getenv("platform-url","unseturl"), "multi": os.getenv("is-multi","False")},
                    status_code=200
                    )
            return RedirectResponse(url=request.url_for("login"), status_code=302)
    except Exception:
        print("Something went wrong because of",traceback.format_exc())
        return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)



def get_local_top(request):
    if 'username' in session:
        return get_top()
    return templates.TemplateResponse("error_showing.html",{"r":"You are not authenticated"},status_code=403)



def get_top_single(request):
  #TODO doesn't do multi yet
    if 'username' in session:
        return get_local_top()
    return templates.TemplateResponse("error_showing.html",{"r":"You are not authenticated"},status_code=403)
    


def organize_containers(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''SELECT component, category, `references`, position, cast(kind as char) as kind FROM checker.component_to_category;'''
                query2 = '''SELECT category from categories;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                cursor.execute(query2)
                conn.commit()
                results_2 = cursor.fetchall()
                return templates.TemplateResponse("organize_containers_unified.html",{"containers": results, "categories":results_2, "timeout": int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_container(request):
    print_debug_log("Adding container")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''INSERT INTO `checker`.`component_to_category` (`component`, `category`, `references`, `position`, `kind`) VALUES (%s, %s, %s, %s, %s);'''
                if request.form.to_dict()['kind'] == "Kubernetes":
                    cursor.execute(query, (request.form.to_dict()['id'],request.form.to_dict()['category'],request.form.to_dict()['contacts'],request.form.to_dict()['namespace'],request.form.to_dict()['kind'],))
                else:
                    cursor.execute(query, (request.form.to_dict()['id'],request.form.to_dict()['category'],request.form.to_dict()['contacts'],request.form.to_dict()['position'],request.form.to_dict()['kind'],))

                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new container because of",traceback.format_exc())
            return f"Something went wrong during the addition of a new container because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_container(request):
    print_debug_log("Editing container")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                if request.form.to_dict()['kind'] == "Kubernetes":
                    if request.form.to_dict()['position']=="": #if namespace left empty, just leave the old one
                        query = '''UPDATE `checker`.`component_to_category` SET `references` = %s, `category` = %s, `kind` = %s where (`component` = %s)'''
                        cursor.execute(query, (request.form.to_dict()['contacts'],request.form.to_dict()['category'],request.form.to_dict()['kind'],request.form.to_dict()['id'],))
                    else:
                        query = '''UPDATE `checker`.`component_to_category` SET `references` = %s, `category` = %s, `position` = %s, `kind` = %s where (`component` = %s)'''
                        cursor.execute(query, (request.form.to_dict()['contacts'],request.form.to_dict()['category'],request.form.to_dict()['position'],request.form.to_dict()['kind'],request.form.to_dict()['id'],))
                else:
                    query = '''UPDATE `checker`.`component_to_category` SET `references` = %s, `category` = %s, `position` = %s, `kind` = %s where (`component` = %s)'''
                    cursor.execute(query, (request.form.to_dict()['contacts'],request.form.to_dict()['category'],request.form.to_dict()['position'],request.form.to_dict()['kind'],request.form.to_dict()['id'],))
                
                conn.commit()
                if cursor.rowcount > 0:
                    return "ok", 201
                else:
                    return "Somehow request did not result in database changes", 400
        except Exception:
            print("Something went wrong during the editing of a container because of",traceback.format_exc())
            return f"Something went wrong during the editing of a container because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_container(request):
    print_debug_log("Deleting container")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            if session['username']!="admin":
                return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
            cursor = conn.cursor(buffered=True)
            if not check_password_hash(users[username], request.form.to_dict()['psw']):
                return "An incorrect password was provided", 400
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''DELETE FROM `checker`.`component_to_category` WHERE (`component` = %s);'''
            cursor.execute(query, (request.form.to_dict()['id'],))
            conn.commit()
            return "ok", 201
    return RedirectResponse(url=request.url_for("login"), status_code=302)

## start add cronjob


def organize_cronjobs(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query = '''SELECT idcronjobs, name, command, category, where_to_run FROM checker.cronjobs where where_to_run is not null union SELECT idcronjobs, name, command, category, 'master' FROM checker.cronjobs where where_to_run is null;'''
                query2 = '''SELECT * from categories;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                cursor.execute(query2)
                conn.commit()
                results_2 = cursor.fetchall()
                return templates.TemplateResponse("organize_cronjobs.html",{"cronjobs":results, "categories":results_2,"timeout":int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_cronjob(request):
    print_debug_log("Adding cronjob")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                if request.form.to_dict()['where_to_run'] != "":
                    query = '''INSERT INTO `checker`.`cronjobs` (`name`, `command`, `category`, `where_to_run`) VALUES (%s, %s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['category'],request.form.to_dict()['where_to_run'],))
                else:
                    query = '''INSERT INTO `checker`.`cronjobs` (`name`, `command`, `category`, `where_to_run`) VALUES (%s, %s, %s, NULL);'''
                    cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['category'],request.form.to_dict()['where_to_run'],))
                
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new cronjob because of",traceback.format_exc())
            return f"Something went wrong during the addition of a new cronjob because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_cronjob(request):
    print_debug_log("Editing cronjob")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query = '''UPDATE `checker`.`cronjobs` SET `name` = %s, `command` = %s, `category` = %s, `where_to_run` = %s WHERE (`idcronjobs` = %s);'''
                cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['category'],request.form.to_dict()['where_to_run'],request.form.to_dict()['id'],)) 
                conn.commit()
                if cursor.rowcount > 0:
                    return "ok", 201
                else:
                    return "Somehow request did not result in database changes", 400
        except Exception:
            print("Something went wrong during the editing of a cronjob because of",traceback.format_exc())
            return f"Something went wrong during the editing of a cronjob because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_cronjob(request):
    print_debug_log("Deleting cronjob")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            if session['username']!="admin":
                return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
            if os.getenv('unsafe-mode') != "True":
                return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            cursor = conn.cursor(buffered=True)
            if not check_password_hash(users[username], request.form.to_dict()['psw']):
                return "An incorrect password was provided", 400
            query = '''DELETE FROM `checker`.`cronjobs` WHERE (`idcronjobs` = %s);'''
            cursor.execute(query, (request.form.to_dict()['id'],))
            conn.commit()
            return "ok", 201
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def organize_extra_resources(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query = '''SELECT `categories`.category as name_category, `extra_resources`.id_category as id_category, `extra_resources`.resource_address as resource_address, `extra_resources`.resource_information as resource_information, `extra_resources`.resource_description as resource_description FROM checker.extra_resources join categories on id_category=id_category;'''
                query2 = '''SELECT * from categories;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                cursor.execute(query2)
                conn.commit()
                results_2 = cursor.fetchall()
                return templates.TemplateResponse("organize_extra_resources.html",{"extra_resources":results, "categories":results_2,"timeout":int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_extra_resource(request):
    print_debug_log("Adding extra resource")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''INSERT INTO `checker`.`extra_resources` ( `resource_address`, `resource_information`, `resource_description`) VALUES (%s, %s, %s);'''
                cursor.execute(query, (request.form.to_dict()['address'],request.form.to_dict()['information'],request.form.to_dict()['description'],))
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new extra resource because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_extra_resource(request):
    print_debug_log("Editing extra resource")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
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
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_extra_resource(request):
    print_debug_log("Deleting extra resource")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            if session['username']!="admin":
                return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
            if os.getenv('unsafe-mode') != "True":
                return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
            cursor = conn.cursor(buffered=True)
            if not check_password_hash(users[username], request.form.to_dict()['psw']):
                return "An incorrect password was provided", 400
            query = '''DELETE FROM `checker`.`extra_resources` WHERE (`id_category` = %s);'''
            cursor.execute(query, (request.form.to_dict()['id'],))
            conn.commit()
            return "ok", 201
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def organize_tests(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''SELECT * FROM checker.tests_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                return templates.TemplateResponse("organize_tests.html",{"tests":results, "timeout":int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_test(request):
    print_debug_log("Adding test")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''INSERT INTO `checker`.`tests_table` (`container_name`, `command`, `command_explained`) VALUES (%s, %s, %s);'''
                cursor.execute(query, (request.form.to_dict()['container_name'],request.form.to_dict()['command'],request.form.to_dict()['command_explained'],))
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new test because of",traceback.format_exc())
            return f"Something went wrong during the addition of a new test because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_test(request):
    print_debug_log("Editing test")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''UPDATE `checker`.`tests_table` SET `container_name` = %s, `command` = %s, `command_explained` = %s WHERE (`id` = %s);'''
                cursor.execute(query, (request.form.to_dict()['container_name'],request.form.to_dict()['command'],request.form.to_dict()['command_explained'],request.form.to_dict()['id'],)) 
                conn.commit()
                if cursor.rowcount > 0:
                    return "ok", 201
                else:
                    return "Somehow request did not result in database changes", 400
        except Exception:
            print("Something went wrong during the editing of a test because of",traceback.format_exc())
            return f"Something went wrong during the editing of a test because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_test(request):
    print_debug_log("Deleting test")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            if session['username']!="admin":
                return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
            if os.getenv('unsafe-mode') != "True":
                return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
            cursor = conn.cursor(buffered=True)
            if not check_password_hash(users[username], request.form.to_dict()['psw']):
                return "An incorrect password was provided", 400
            query = '''DELETE FROM `checker`.`tests_table` WHERE (`id` = %s);'''
            cursor.execute(query, (request.form.to_dict()['id'],))
            conn.commit()
            return "ok", 201
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def organize_complex_tests(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''SELECT * FROM checker.complex_tests;'''
                query2 = '''SELECT * from categories;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                cursor.execute(query2)
                conn.commit()
                results_2 = cursor.fetchall()
                return templates.TemplateResponse("organize_complex_tests.html",{"complex_tests":results, "categories":results_2,"timeout":int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_complex_test(request):
    print_debug_log("Adding compelx test")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''INSERT INTO `checker`.`complex_tests` (`name_of_test`, `command`, `extraparameters`, `button_color`, `explanation`, `category_id`) VALUES (%s, %s, %s, %s, %s, %s);'''
                cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['extra_parameters'],request.form.to_dict()['button_color'],request.form.to_dict()['explanation'],request.form.to_dict()['category'],))
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new complex test because of",traceback.format_exc())
            return f"Something went wrong during the addition of a new complex test because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_complex_test(request):
    print_debug_log("Editing complex test")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
                cursor = conn.cursor(buffered=True)
                query = '''UPDATE `checker`.`complex_tests` SET `name_of_test` = %s, `command` = %s, `extraparameters` = %s, `button_color` = %s, `explanation` = %s, `category_id` = %s WHERE (`id` = %s);'''
                cursor.execute(query, (request.form.to_dict()['name'],request.form.to_dict()['command'],request.form.to_dict()['extra_parameters'],request.form.to_dict()['button_color'],request.form.to_dict()['explanation'],request.form.to_dict()['category'],request.form.to_dict()['id'],)) 
                conn.commit()
                if cursor.rowcount > 0:
                    return "ok", 201
                else:
                    return "Somehow request did not result in database changes", 400
        except Exception:
            print("Something went wrong during the editing of a complex_test because of",traceback.format_exc())
            return f"Something went wrong during the editing of a complex test because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_complex_test(request):
    print_debug_log("Deleting complex test")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            if session['username']!="admin":
                return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
            if os.getenv('unsafe-mode') != "True":
                return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
            
            cursor = conn.cursor(buffered=True)
            if not check_password_hash(users[username], request.form.to_dict()['psw']):
                return "An incorrect password was provided", 400
            query = '''DELETE FROM `checker`.`complex_tests` WHERE (`id` = %s);'''
            cursor.execute(query, (request.form.to_dict()['id'],))
            conn.commit()
            return "ok", 201
    return RedirectResponse(url=request.url_for("login"), status_code=302)

def organize_categories(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query2 = '''SELECT * from categories;'''
                cursor.execute(query2)
                conn.commit()
                results_2 = cursor.fetchall()
                return templates.TemplateResponse("organize_categories.html",{"categories":results_2,"timeout":int(os.getenv("requests-timeout","15000"))})
                
        except Exception:
            print("Something went wrong because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def add_category(request):
    print_debug_log("Adding category")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query = '''INSERT INTO `checker`.`categories` (`category`) VALUES (%s);'''
                cursor.execute(query, (request.form.to_dict()['category'],))
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the addition of a new category because of",traceback.format_exc())
            return f"Something went wrong during the addition of a new category because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def edit_category(request):
    print_debug_log("Editing category")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                query = '''UPDATE `checker`.`categories` SET `category` = %s (`idcategories` = %s);'''
                cursor.execute(query, (request.form.to_dict()['category'],request.form.to_dict()['id'],)) 
                conn.commit()
                if cursor.rowcount > 0:
                    return "ok", 201
                else:
                    return "Somehow request did not result in database changes", 400
        except Exception:
            print("Something went wrong during the editing of a category because of",traceback.format_exc())
            return f"Something went wrong during the editing of a category because of {traceback.format_exc()}", 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def delete_category(request):
    print_debug_log("Deleting category")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                if session['username']!="admin":
                    return templates.TemplateResponse("error_showing.html",{"r":"You do not have the privileges to access this webpage."},status_code=401)
                if os.getenv('unsafe-mode') != "True":
                    return templates.TemplateResponse("error_showing.html",{"r":"Unsafe mode is not set, hence you cannot perform this action (edit conf.json or env variables)"},status_code=401)
                cursor = conn.cursor(buffered=True)
                if not check_password_hash(users[username], request.form.to_dict()['psw']):
                    return "An incorrect password was provided", 400
                query = '''DELETE FROM `checker`.`categories` WHERE (`idcategories` = %s);'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                return "ok", 201
        except Exception:
            print("Something went wrong during the deletion of an old category because of",traceback.format_exc())
            return f"Something went wrong during the deletion of an old category because of {traceback.format_exc()}", 500
    
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def login(request):
    if os.getenv("is-master","False") == "True":
        if request.method == "POST":
            username = request.form['username']
            password = request.form['password']
            if username in users and check_password_hash(users[username], password):
                print_debug_log(f"{username} logged in")
                session.permanent = True
                session['username'] = username
                return redirect(url_for('main_page'))
            print_debug_log(f"{username} tried to login and failed due to wrong credentials")
            return "Invalid credentials", 401
        return render_template('login.html')
    return "This instance is not a master and you can't log on to it", 400



def get_additional_data(request):
    print_debug_log("Making a call to an extra resource")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT * FROM extra_resources where resource_address = %s;'''
                cursor.execute(query, (request.form.to_dict()['id'],))
                conn.commit()
                try:
                    _ = cursor.fetchone()
                except Exception:
                    return "An unauthorized url was attempted to use", 400
                response = requests.get(request.args.to_dict()['url_of_resource'])
                response.raise_for_status()
                return response.text
        except Exception:
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def get_complex_test_buttons(request):
    print_debug_log("Getting complex tests")
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
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def make_category_green(request):
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
                return templates.TemplateResponse("error_showing.html",{"r": "There was a problem: "+traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def check(request):
    print_debug_log("Reading containers")
    if os.getenv("is-multi","False") == "True":
        try:
            jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])
            return get_container_data()
        except jwt.ExpiredSignatureError:
            print("Token expired")
            return {'error': 'Token expired'}, 401
        except jwt.InvalidTokenError:
            print("Token invalid:", request.form.to_dict()['auth'])
            return {'error': 'Invalid token'}, 401
        except Exception:
            print(f"Something failed:", traceback.format_exc())
    elif 'username' in session:
        return get_container_data()
    return RedirectResponse(url=request.url_for("login"), status_code=302)
        
def send_request(url, headers):
    return requests.post(url, headers=headers)


def check_container_db(request):
    print_debug_log("Reading container's database")
    if 'username' in session:
        if not os.getenv("is-master","False") == "True":
            return templates.TemplateResponse("error_showing.html",{"r":"This Snap4Sentinel instance is not the master of its cluster"},status_code=403)
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
    return RedirectResponse(url=request.url_for("login"), status_code=302)

def get_container_categories(request):
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
        return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)

def get_extra_data(request):
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
    

def run_test(request):
    print_debug_log("Running test")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''select command, command_explained, id from tests_table where container_name =%s;'''
                
                if "False" == os.getenv("running-as-kubernetes","False"):
                    container = request.form.to_dict()['container']
                else:
                    container = '-'.join(request.form.to_dict()['container'].split('-')[:-2])
                cursor.execute(query, (container,))
                conn.commit()
                results = cursor.fetchall()
                total_result = ""
                for r in list(results):
                    try:
                        command_ran = subprocess.run(r[0], shell=True, capture_output=True, text=True, encoding="utf8")
                        total_result += "Running " + r[0] + " with result " + command_ran.stdout + "\nWith errors: " + command_ran.stderr
                        #new stuff
                        new_output = {"container":request.form.to_dict()['container'],"command":r[0],"result":command_ran.stdout,"errors":command_ran.stderr}
                        query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                        cursor.execute(query_1,(f"{command_ran.stdout}\n{command_ran.stderr}", container,r[0],))
                        conn.commit()
                        log_to_db('test_ran', "Executing the is alive test on "+request.form.to_dict()['container']+" resulted in: "+command_ran.stdout, which_test="is alive " + str(r[2]),user_op=session['username'])
                    except Exception:
                        return f"Test of {request.form.to_dict()['container']} had a runtime error with the cause: {traceback.format_exc()}", 500
                if len(results) == 0:
                    return {"container":request.form.to_dict()['container'],"command":"Test was not found","result":"Test was not ran","errors":""}
                return new_output
        except Exception:
            print("Something went wrong during tests running because of:",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)

    

def run_test_complex(request):
    print_debug_log("Running complex test")
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
                    command_ran = subprocess.run(r[0]+arguments_test, shell=True, capture_output=True, text=True, encoding="utf8")
                    if len(command_ran.stderr) > 0:
                        string_used = '<p style="color:#FF0000";>'+command_ran.stderr+'</p> '+command_ran.stdout
                    else:
                        string_used = command_ran.stdout
                    total_result += string_used
                    query_1 = 'insert into tests_results (datetime, result, container, command) values (now(), %s, %s, %s);'
                    cursor.execute(query_1,(string_used, test_name,r[0],))
                    conn.commit()
                    log_to_db('test_ran', "Executing the complex test " + test_name + " resulted in: " +string_used, which_test="advanced test - "+str(r[1]),user_op=session['username'])
                return total_result
        except Exception:
            print("Something went wrong during tests running because of",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)        
    

async def test_all_ports(request):
    print_debug_log("Testing all ports")
    if 'username' in session:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            # to run malicious code, malicious code must be present in the db or the machine in the first place
            query = '''select container_name, command from tests_table;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            print(f"Starting running test (frontend): {datetime.now()}")
            tasks = [run_shell_command(r[0], r[1]) for r in results]
            completed = await asyncio.gather(*tasks)
            return completed
    return RedirectResponse(url=request.url_for("login"), status_code=302)
        

def deauthenticate(request):
    # FIXME there is this and logout??
    print_debug_log("Deautheticated")
    session.clear()
    return "You have been deauthenticated", 401
    

def reboot_container(request):
    print_debug_log("Rebooting container")
    if 'username' not in session and os.getenv("is-master","False") == "True": # if we aren't logged in and this is a master, it could be that we are talking to a master as a master, in which case we should have a token
        try:
            jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])
        except:
            return RedirectResponse(url=request.url_for("login"), status_code=302)
    try:
        if not check_password_hash(users[username], request.form.to_dict()['psw']):
            return "An incorrect password was provided", 400
    except KeyError: # no psw found
        if os.getenv("is-multi","False") == "True" and "auth" in request.form.to_dict(): # on multi not having the psw is allowed if it has a token, because it is a intracluster call
            pass
        else:
            return "An incorrect password was provided", 400
    
    if os.getenv("is-multi","False") == "False":
        if "False" == os.getenv("running-as-kubernetes","False"):
            og_result = queued_running('docker restart '+request.form.to_dict()['id'])
            result = og_result.stdout
            if len(og_result.stderr)>0:
                log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result+' with errors: '+og_result.stderr, user_op=session['username'])
                return result, 500
            else:
                log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result, user_op=session['username'])
                return result
        else:
            try:
                result = queued_running(f"kubectl rollout restart deployment {'-'.join(request.form.to_dict()['id'].split('-')[:-2])} -n $(kubectl get deployments --all-namespaces | awk '$2==\"{'-'.join(request.form.to_dict()['id'].split('-')[:-2])}\" {{print $1}}')")
                #result = queued_running('kubectl rollout restart deployments/'+"-".join(request.form.to_dict()['id'].split("-")[:-2])).stdout
                log_to_db('rebooting_containers', 'kubernetes restart '+request.form.to_dict()['id']+' resulted in: '+result.stdout, user_op=session['username'])
                return result.stdout
            except Exception:
                return f"Issue while rebooting container/pod: {traceback.format_exc()}", 500
    else: # we are on multi here
        if "auth" not in request.form.to_dict():
            source = request.form.to_dict()['source']
            if source == os.getenv("platform-url",""):
                if "False" == os.getenv("running-as-kubernetes","False"):
                    og_result = queued_running('docker restart '+request.form.to_dict()['id'])
                    result = og_result.stdout
                    if len(og_result.stderr)>0:
                        log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result+' with errors: '+og_result.stderr, user_op=session['username'])
                        return result, 500
                    else:
                        log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result, user_op=session['username'])
                        return result
                else:
                    try:
                        result = queued_running(f"kubectl rollout restart deployment {'-'.join(request.form.to_dict()['id'].split('-')[:-2])} -n $(kubectl get deployments --all-namespaces | awk '$2==\"{'-'.join(request.form.to_dict()['id'].split('-')[:-2])}\" {{print $1}}')")
                        #result = queued_running('kubectl rollout restart deployments/'+"-".join(request.form.to_dict()['id'].split("-")[:-2])).stdout
                        log_to_db('rebooting_containers', 'kubernetes restart '+request.form.to_dict()['id']+' resulted in: '+result.stdout, user_op=session['username'])
                        return result.stdout
                    except Exception:
                        return f"Issue while rebooting container/pod: {traceback.format_exc()}", 500
            else:
                try:
                    r = requests.post(request.form.to_dict()['source']+"/reboot_container", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=1)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM),"id":request.form.to_dict()['id']})
                    print(f"asking {request.form.to_dict()['source']} to reboot {request.form.to_dict()['id']} resulted in code {r.status_code} and body {r.text[:100]}...")
                    return r.text, r.status_code
                except:
                    return f"Issue while rebooting pod: {traceback.format_exc()}", 500
        else:
            try:
                jwt_token=jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])
            except jwt.ExpiredSignatureError:
                return "Token expired", 401
            except jwt.InvalidTokenError:
                return "Token invalid", 401
            except:
                return f"Issue while rebooting container/pod: {traceback.format_exc()}", 500
            if "False" == os.getenv("running-as-kubernetes","False"):
                og_result = queued_running('docker restart '+request.form.to_dict()['id'])
                result = og_result.stdout
                if len(og_result.stderr)>0:
                    log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result+' with errors: '+og_result.stderr,user_op=jwt_token["sub"])
                    return result, 500
                else:
                    log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result,user_op=jwt_token["sub"])
                    return result
            else:
                try:
                    result = queued_running(f"kubectl rollout restart deployment {'-'.join(request.form.to_dict()['id'].split('-')[:-2])} -n $(kubectl get deployments --all-namespaces | awk '$2==\"{'-'.join(request.form.to_dict()['id'].split('-')[:-2])}\" {{print $1}}')")
                    log_to_db('rebooting_containers', 'kubernetes restart '+request.form.to_dict()['id']+' resulted in: '+result.stdout,user_op=jwt_token["sub"])
                    return result.stdout
                except Exception:
                    return f"Issue while rebooting container/pod: {traceback.format_exc()}", 500
        

def get_muted_components(request):
    print_debug_log("Getting muted containers")
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
    return RedirectResponse(url=request.url_for("login"), status_code=302)

        

def mute_component_by_hours(request):
    print_debug_log("Getting muted containers by hout")
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
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def get_cron_jobs(request):
    print_debug_log("Getting cronjob results")
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''WITH RankedEntries AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY id_cronjob ORDER BY datetime DESC) AS row_num FROM cronjob_history) 
SELECT datetime,result,errors,name,command,categories.category FROM RankedEntries join cronjobs on cronjobs.idcronjobs=RankedEntries.id_cronjob join categories on categories.idcategories=cronjobs.category WHERE row_num = 1;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong during getting a cronjob because of:",traceback.format_exc())
            return traceback.format_exc(), 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    

def get_tests(request):
    print_debug_log("Getting tests results")
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
                log_to_db('getting_tests', 'Tests results were read')
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
    
# this is only called serverside
def log_to_db(table, log, which_test="", user_op=""):
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            try:
                user = session['username']
            except KeyError:
                user = user_op
            cursor = conn.cursor(buffered=True)
            if table != "test_ran":
                cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator) VALUES (NOW(),'{}','{}')'''.format(table, log.replace("'","''"), user))
            else:
                cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator, test) VALUES (NOW(),'{}','{}','{}')'''.format(table, log.replace("'","''"), user, which_test))
            conn.commit()
    except Exception:
        print("Something went wrong during db logging because of:",traceback.format_exc(), "- in:",table)
        

def get_complex_tests(request):
    print_debug_log("Getting complex test results")
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
                log_to_db('getting_tests', 'Tests results were read', user_op=session['username'])
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def get_container_logs(podname):
    podname = request.path_params["podname"]
    print_debug_log("Getting container logs")
    if 'username' not in session and os.getenv("is-master","False") == "True": # if we aren't logged in and this is a master, it could be that we are talking to a master as a master, in which case we should have a token
        try:
            jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])
        except:
            return RedirectResponse(url=request.url_for("login"), status_code=302)

    if os.getenv("is-multi","False") == "False":
        if "False" == os.getenv("running-as-kubernetes","False"):
            print("Debug for logs:", podname, request.form.to_dict())
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
            if "raw" not in request.form.to_dict().keys():
                return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
            else:
                r = r.replace("<br>","\n")
                return r, 200
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
            if namespace not in string_of_list_to_list(os.getenv("namespaces","['default']")):
                return templates.TemplateResponse("error_showing.html",{"r":f"{podname} wasn't found among the containers"},status_code=500)
            process = subprocess.Popen(
        f"""kubectl logs -n $(kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}') {podname} --tail {os.getenv('default-log-length')}""",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                text=True
            )
            out=[]
            if os.getenv('log-previous-container-if-kubernetes') !=None:
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
            if "raw" not in request.form.to_dict().keys():
                return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
            else:
                r = r.replace("<br>","\n")
                return r, 200
    else:
        try:
            jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])
            # if we are here, this was an intracluster call
            if "False" == os.getenv("running-as-kubernetes","False"):
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
                if "raw" not in request.form.to_dict().keys():
                    return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
                else:
                    r = r.replace("<br>","\n")
                    return r, 200
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
                if namespace not in string_of_list_to_list(os.getenv("namespaces","['default']")):
                    return templates.TemplateResponse("error_showing.html",{"r":f"{podname} wasn't found among the containers"},status_code=500)
                process = subprocess.Popen(
            f"""kubectl logs -n $(kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}') {podname} --tail {os.getenv('default-log-length')}""",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                    text=True
                )
                out=[]
                if os.getenv('log-previous-container-if-kubernetes') !=None:
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
                if "raw" not in request.form.to_dict().keys():
                    return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
                else:
                    r = r.replace("<br>","\n")
                    return r, 200
        except jwt.ExpiredSignatureError:
            return "Token expired", 401
        except jwt.InvalidTokenError:
            return "Token invalid", 401
        except KeyError: # we are on multi, there was no token, therefore this in not an internal call. So, unless it is us, call the proper sentinel and forward the answer
            if request.form.to_dict()['source'] == os.getenv("platform-url",""): # it is us
                if "False" == os.getenv("running-as-kubernetes","False"):
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
                    if "raw" not in request.form.to_dict().keys():
                        return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
                    else:
                        r = r.replace("<br>","\n")
                        return r, 200
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
                    if namespace not in string_of_list_to_list(os.getenv("namespaces","['default']")):
                        return templates.TemplateResponse("error_showing.html",{"r":f"{podname} wasn't found among the containers"},status_code=500)
                    process = subprocess.Popen(
                f"""kubectl logs -n $(kubectl get pods --all-namespaces --no-headers | awk '$2 ~ /{podname}/ {{ print $1; exit }}') {podname} --tail {os.getenv('default-log-length')}""",
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,  # Merge stderr into stdout to preserve order
                        text=True
                    )
                    out=[]
                    if os.getenv('log-previous-container-if-kubernetes') !=None:
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
                    if "raw" not in request.form.to_dict().keys():
                        return render_template('log_show.html', container_id = podname, r = r, container_name=podname)
                    else:
                        r = r.replace("<br>","\n")
                        return r, 200
            else:
                try:
                    print_debug_log(f"Asking {request.form.to_dict()['source']} for {podname} logs")
                    if "raw" not in request.form.to_dict().keys():
                        r = requests.post(request.form.to_dict()['source']+"/container/"+podname, data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)})
                        return r.text, r.status_code
                    else:
                        r = requests.post(request.form.to_dict()['source']+"/container/"+podname, data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM), "raw":"True"})
                        return r.text, r.status_code
                except:
                    return f"Issue while rebooting pod: {traceback.format_exc()}", 500
        except:
            return f"Issue while getting logs of container/pod: {traceback.format_exc()}", 500
    


def get_container_logs_advanced(request):
    container_name = request.path_params["container_name"]
    if 'username' in session: # probably unneeded
        try:
            r = get_container_logs(container_name)
            return r.text
        except Exception:
            print("Something went wrong during reading because of:",traceback.format_exc())
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def get_summary_status(request):
    if 'username' in session:
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                cursor.execute('''SELECT * FROM summary_status;''')
                results = cursor.fetchall()
                return results
        except Exception:
            print("Something went wrong during db logging because of:",traceback.format_exc())
    return RedirectResponse(url=request.url_for("login"), status_code=302)

def get_container_data(do_not_jsonify=False):
    if "False" == os.getenv("running-as-kubernetes","False"):
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
        new_containers_merged = []
        source = os.getenv("platform-url","")
        for current in containers_merged:
            td = {}
            #td["Command"] = current["Command"]
            td["CreatedAt"] = current["CreatedAt"]
            try: #it is set if it comes from elsewhere
                td["Source"] = current["Source"]
            except:
                td["Source"] = source
            td["ID"] = current["ID"]
            td["Image"] = current["Image"]
            td["Labels"] = current["Labels"]
            td["Mounts"] = current["Mounts"]
            td["Names"] = current["Names"]
            td["Name"] = current["Names"]
            td["Ports"] = current["Ports"]
            td["RunningFor"] = current["RunningFor"]
            td["State"] = current["State"]
            td["Status"] = current["Status"]
            td["Container"] = current["Container"]
            # host origin = node, sorta
            td["Node"] = os.getenv("platform-url","") #current[""]
            td["Volumes"] = current["LocalVolumes"]
            td["Namespace"] = "Docker - " + source
            new_containers_merged.append(td)
        containers_merged = new_containers_merged
        if do_not_jsonify:
            return containers_merged
        return containers_merged
    else:
        
        raw_jsons = []
        for a in string_of_list_to_list(os.getenv("namespaces","['default']")):
            raw_jsons.append(json.loads(subprocess.run(f'kubectl get pods -o json -n {a}',shell=True, capture_output=True, text=True, encoding="utf_8").stdout))
        conversions=[]
    source = os.getenv("platform-url","")
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
            conversion["Source"]=source
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
    return conversions



async def generate_pdf(request):
    print_debug_log("Generating a pdf")
    if 'username' in session:
        data_stored = []
        data = check_container_db()["result"]
        containers = {}
        for container in data:
            try:
                request=requests.post(os.getenv("platform-url")+"/container/"+container["Name"], data={"id":container["Name"], "source":container["Source"],"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM), "raw":"True"})
                request.raise_for_status()
                containers[container["Name"]+"-"+container["Source"]]=request.text
            except Exception:
                print(traceback.format_exc())
        for key, value in containers.items():
            data_stored.append({"header": key, "string": value})
        
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
        cronjobs_out = None
        extra_tests = []
        cronjobs = []
        
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''WITH RankedEntries AS ( 
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY container ORDER BY datetime DESC) AS row_num FROM tests_results
                    ) 
                    SELECT * FROM RankedEntries WHERE row_num = 1;'''
                cursor.execute(query)
                conn.commit()
                log_to_db('getting_tests', 'Tests results were read', user_op=session['username'])
                results = cursor.fetchall()
                tests_out = results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            
        try: # cronjobs
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''WITH RankedEntries AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY id_cronjob ORDER BY datetime DESC) AS row_num FROM cronjob_history) 
SELECT datetime,result,errors,name,command,categories.category FROM RankedEntries join cronjobs on cronjobs.idcronjobs=RankedEntries.id_cronjob join categories on categories.idcategories=cronjobs.category WHERE row_num = 1;'''
                cursor.execute(query)
                conn.commit()
                log_to_db('getting_tests', 'Cronjobs results were read', user_op=session['username'])
                results = cursor.fetchall()
                cronjobs_out = results
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
        # index
        content.append(Paragraph("The following are hyperlinks to logs of each container.", styles["Heading1"]))
        for pair in data_stored:
            if any(pair["header"].startswith(prefix) for prefix in ['dashboard-backend','myldap']):
                continue
            content.append(Paragraph(f'<a href="#c-{pair["header"]}" color="blue">Container {pair["header"]}</a>', styles["Normal"]))
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for root, dirs, files in os.walk(os.path.join(current_dir, os.pardir)): #maybe doesn't find the files while clustered but continues gracefully
            if 'log.txt' in files:
                #logs_file_path = os.path.join(root, 'log.txt')
                log_output = subprocess.run(f'cd {root}; tail -n {os.getenv("default-log-length",1000)} log.txt', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                content.append(Paragraph('<a href="#iot-directory-log" color="blue">iot-directory-log</a>', styles["Normal"]))
                extra_logs.append(Paragraph(f'<b><a name="iot-directory-log"></a>iot-directory-log</b>', styles["Heading1"]))
                extra_logs.append(Paragraph(log_output.replace("\n","<br></br>"), styles["Normal"]))
                break  # Stop searching after finding the first occurrence
        for test in tests_out:
            if not test:
                break
            content.append(Paragraph(f'<a href="#t-{test[3]}" color="blue">Test of {test[3]}</a>', styles["Normal"]))
            extra_tests.append(test)            
        for cronjob in cronjobs_out:
            if not cronjob:
                break
            content.append(Paragraph(f'<a href="#t-{cronjob[3]}" color="blue">Cronjob {cronjob[3]}</a>', styles["Normal"]))
            cronjobs.append(cronjob)
        content.append(PageBreak())
        
        
        # Iterate over pairs
        for pair in data_stored:
            if any(pair["header"].startswith(prefix) for prefix in ['dashboard-backend','myldap']):
                continue
            print(f"doing {pair['header']} with {pair['string'][:200]}")
            header = pair["header"]
            string = pair["string"]
            string = html.escape(string)
            string = string.replace("\n","<br>")
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
        for cronjob in cronjobs:
            content.append(Paragraph(f'<b><a name="c-{cronjob[3]}"></a>{cronjob[3]}</b>', styles["Heading1"]))
            content.append(Paragraph(html.escape(cronjob[1]).replace("\n","<br>").replace("<br>","<br></br>"), styles["Normal"]))
            if cronjob[2]:
                content.append(Paragraph(f'<br><b><a name="c-{cronjob[3]}-errors"></a>Errors</b>', styles["Heading2"]))
                content.append(Paragraph(html.escape(cronjob[2]).replace("\n","<br>").replace("<br>","<br></br>"), styles["Normal"]))
            content.append(PageBreak())
        # Add content to the PDF document
        doc.build(content)
        # Send the PDF file as a response
        response = FileResponse(pdf_output_path)
        return response
    return RedirectResponse(url=request.url_for("login"), status_code=302)

    

def redirect_to_download(request):
    if 'username' in session:
        return redirect('/downloads/')
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def list_files(request):
    subpath = request.path_params["subpath"]
    if 'username' in session:
        # Determine the full path relative to the base directory
        full_path = os.path.join(os.path.join(os.getcwd(), "data/"), subpath)
        if ".." in subpath:
            return templates.TemplateResponse("error_showing.html",{"r":"Issues during the retrieving of the resource: illegal path"},status_code=500)
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
                return templates.TemplateResponse("download_files.html",{"files":files_list, "subpath":subpath})
            except FileNotFoundError:
                return templates.TemplateResponse("error_showing.html",{"r":"Issues during the retrieving of the folder: "+ traceback.format_exc()},status_code=500)
        # If it's a file, serve the file
        elif os.path.isfile(full_path):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            return send_from_directory(directory, filename, as_attachment=True)
        else:
            return templates.TemplateResponse("error_showing.html",{"r":"No certification was ever produced"},status_code=500)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
        


def certification(request):
    if 'username' in session:
        if session['username'] != "admin":
            try:
                if jwt.decode(request.form.to_dict()['auth'], os.getenv("cluster-secret","None"), algorithms=[ALGORITHM])['sub'] == "admin": #maybe authenticate with token
                    pass
                else:
                    return templates.TemplateResponse("error_showing.html",{"r":"User is not authorized to perform the operation."},status_code=401)
            except jwt.ExpiredSignatureError:
                return {'error': 'Token expired'}, 401
            except jwt.InvalidTokenError:
                return {'error': 'Invalid token'}, 401
            except Exception:
                return templates.TemplateResponse("error_showing.html",{"r":"Something bad happened: " + traceback.format_exc()},status_code=401)
            
        try:
            subfolder = "cert"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
            script_to_run = "/app/scripts/make_dumps_of_database.sh"
            if os.getenv("running-as-kubernetes",None):
                script_to_run = "/app/scripts/make_dumps_of_database_k8.sh"
            make_certification = subprocess.run(f'mkdir -p /app/data; mkdir -p {os.getenv("conf-path","/home/debian")}; cp -r {os.getenv("conf-path","/home/debian")} /app/data/{subfolder}; cd /app/data/{subfolder} && bash {script_to_run} && rar a -k -p{password} snap4city-certification-{password}.rar */ *.*', shell=True, capture_output=True, text=True, encoding="utf_8")
            if len(make_certification.stderr) > 0:
                print(make_certification.stderr)
                return FileResponse(f'/app/data/{subfolder}/snap4city-certification-{password}.rar')
            else:
                return FileResponse(f'/app/data/{subfolder}/snap4city-certification-{password}.rar')
        except Exception:
            return templates.TemplateResponse("error_showing.html",{"r":f"Fatal error while generating configuration: {traceback.format_exc()}"},status_code=401)
    return RedirectResponse(url=request.url_for("login"), status_code=302)
        

def clustered_certification(request):
    if 'username' in session:
        if not os.getenv("is-multi","True"):
            return "Disabled for non-clustered environments", 500
        if session['username'] != "admin":
            return templates.TemplateResponse("error_showing.html",{"r":"User is not authorized to perform the operation"},status_code=401)
        try:
            results = None
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                query = '''SELECT hostname FROM checker.ip_table;'''
                cursor.execute(query)
                conn.commit()
                results = cursor.fetchall()
                error = False
                errorText = ""
                subfolder = "certifications/certcluster"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                subprocess.run(f'rm -f *snap4city*-certification-*.rar', shell=True)
                for r in results:
                    file_name, content_disposition = "", ""
                    obtained = requests.get(r[0]+"/sentinel/certification", data={"auth":jwt.encode({'sub': username,'exp': datetime.now() + timedelta(minutes=15)}, os.getenv("cluster-secret","None"), algorithm=ALGORITHM)})
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
                    return templates.TemplateResponse("error_showing.html",{"r":errorText.replace("\n","<br>")},status_code=500)
                else:
                    password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
                    subprocess.run(f'rar a -k -p{password} snap4city-clustered-certification-{password}.rar *snap4city-certification-*.rar; mkdir -p {subfolder}; cp snap4city-clustered-certification-{password}.rar {subfolder}/snap4city-clustered-certification-{password}.rar', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                    return FileResponse(f'snap4city-clustered-certification-{password}.rar')
        except Exception:
            return templates.TemplateResponse("error_showing.html",{"r":traceback.format_exc()},status_code=500)
# hosts stuff        

def hosts_control_panel(request):
    if 'username' in session:
        try:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT host, user, description, threshold_cpu, threshold_mem FROM host")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return templates.TemplateResponse("control_panel.html",{"hosts":rows})
        except Exception:
            return f"Error loading hosts: {traceback.format_exc()}"
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def connect_and_store(request):
    if 'username' in session:
        host = request.form.get('host')
        user = request.form.get('user')
        password = request.form.get('psw')
        description = request.form.get('description')
        threshold_cpu = request.form.get('cpu')
        threshold_mem = request.form.get('mem')

        try:
            private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")
            public_key_path = private_key_path + ".pub"

            if not os.path.exists(private_key_path):
                key = paramiko.RSAKey.generate(2048)
                key.write_private_key_file(private_key_path)
                with open(public_key_path, 'w') as f:
                    f.write(f"{key.get_name()} {key.get_base64()}")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, username=user, password=password)

            with ssh.open_sftp() as sftp:
                try:
                    sftp.mkdir(".ssh")
                except IOError:
                    pass
                with sftp.open(".ssh/authorized_keys", 'a') as ak:
                    with open(public_key_path, 'r') as f:
                        ak.write(f.read() + "\n")

            ssh.close()

            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO host (host, user, description, threshold_cpu, threshold_mem) VALUES (%s, %s, %s, %s, %s)", (host, user, description, threshold_cpu, threshold_mem))
            conn.commit()
            cursor.close()
            conn.close()

            return {"status": "ok"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def run_command(request):
    if 'username' in session:
        host = request.form.get('host')

        try:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user FROM host WHERE host=%s", (host,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                return {"error": "Host not found in DB"}, 400

            user = row['user']
            private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, username=user, key_filename=private_key_path)
            # later on make this something which can change, but only if it is safe!
            _, stdout, stderr = ssh.exec_command("pwd")
            output = stdout.read().decode()
            error = stderr.read().decode()

            ssh.close()

            if error:
                return {"error": error}, 500
            return {"output": output}

        except Exception as e:
            return {"error": str(e)}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def delete_host(request):
    if 'username' in session:
        host = request.form.get('host')

        try:
            # Fetch user from DB
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user FROM host WHERE host=%s", (host,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                return {"error": "Host not found in DB"}, 400

            user = row['user']
            cursor.execute("DELETE FROM host WHERE host=%s", (host,))
            conn.commit()
            cursor.close()
            conn.close()

            # Only delete keys if the host was present in DB
            private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")
            public_key_path = private_key_path + ".pub"
            for path in [private_key_path, public_key_path]:
                if os.path.exists(path):
                    os.remove(path)

            return {"status": "deleted"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def get_tops(request):
    if 'username' in session:
        try:
            # Fetch user from DB
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user, host FROM host;")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            outs = []
            errors = []
            for row in rows:
                try:
                    user = row['user']
                    host = row['host']
                    private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")

                    # Connect with key
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(host, username=user, key_filename=private_key_path)

                    _, stdout, _ = ssh.exec_command("top -b -n 1")
                    output = stdout.read().decode()

                    ssh.close()
                    generated_json=parse_top(output)
                    generated_json["source"] = host
                    outs.append(generated_json)
                except:
                    errors.append(traceback.format_exc())
            data_to_send={"result":outs,"error":errors}
            return templates.TemplateResponse("top-viewer.html",{"data":data_to_send})
        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)

# end host stuff

# begin sentinel host stuff
    

def sentinel_hosts_control_panel(request):
    if not os.getenv("is-multi","False") == "True":
        return "Disabled for non-clustered environments", 500
    if 'username' in session:
        try:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT hostname, ip FROM ip_table")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return templates.TemplateResponse("multi-host-sentinel-manager.html",{"hosts":rows})
        except Exception:
            return f"Error loading hosts: {traceback.format_exc()}"
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def add_sentinel_host(request):
    if not os.getenv("is-multi","False") == "True":
        return "Disabled for non-clustered environments", 500
    if 'username' in session:
        hostname = request.form.get('hostname')
        ip = request.form.get(key='ip')

        try:
            
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ip_table (hostname, ip) VALUES (%s, %s)", (hostname, ip))
            conn.commit()
            cursor.close()
            conn.close()

            return {"status": "ok"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)



def delete_sentinel_host(request):
    if not os.getenv("is-multi","False") == "True":
        return "Disabled for non-clustered environments", 500
    if 'username' in session:
        hostname = request.form.get('hostname')

        try:
            # Fetch user from DB
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT hostname FROM ip_table WHERE hostname=%s", (hostname,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                return {"error": "Host not found in DB"}, 400

            cursor.execute("DELETE FROM ip_table WHERE hostname=%s", (hostname,))
            conn.commit()
            cursor.close()
            conn.close()

            return {"status": "deleted"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


# end sentinel host stuff 


# begin snmp stuff

def snmp_control_panel(request):
    if 'username' in session:
        try:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT host, user, description, threshold_cpu, protocol, details, threshold_mem FROM snmp_host")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return templates.TemplateResponse("control_panel_snmp.html",{"hosts_snmp":rows})
        except Exception:
            return f"Error loading hosts: {traceback.format_exc()}"
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def add_snmp(request):
    if 'username' in session:
        user = request.form.get('user', None)
        description = request.form.get('description', None)
        details = request.form.get('details', None)
        cpu = request.form.get('cpu', None)
        mem = request.form.get('mem', None)
        protocol = request.form.get('protocol', None)
        host = request.form.get('host', None)
        PrivKey = request.form.get('PrivKey', None)
        AuthKey = request.form.get('AuthKey', None)
        try:
            
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor()
            if protocol=="True":
                details = json.dumps({"PrivKey":PrivKey, "AuthKey":AuthKey})
            elif protocol=="False":
                details = None
            else:
                return {"error": "Illegal protocol detected"}, 500
            cursor.execute("INSERT INTO snmp_host (host, user, description, threshold_cpu, threshold_mem, details, protocol) VALUES (%s, %s, %s, %s, %s)", (host, user, description, cpu, mem, details, protocol))
            conn.commit()
            cursor.close()
            conn.close()

            return {"status": "ok"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)


def delete_snmp_host(request):
    if 'username' in session:
        host = request.form.get('host')

        try:
            # Fetch user from DB
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user FROM snmp_host WHERE host=%s", (host,))
            row = cursor.fetchone()

            if not row:
                cursor.close()
                conn.close()
                return {"error": "Host not found in DB"}, 400

            cursor.execute("DELETE FROM snmp_host WHERE host=%s", (host,))
            conn.commit()
            cursor.close()
            conn.close()
            return {"status": "deleted"}

        except Exception:
            return {"error": traceback.format_exc()}, 500
    return RedirectResponse(url=request.url_for("login"), status_code=302)
# end snmp stuff


def snmp_info(request):
    if 'username' in session:
        host = request.args.get("host", None)
        if host is None:
            return templates.TemplateResponse("error_showing.html",{"r":"No SNMP host was selected, please ensure to provide it in the body of the request under 'host'"},status_code=400)
        try:
            conn = mysql.connector.connect(**db_conn_info)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM host WHERE host=%s", (host,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return templates.TemplateResponse("error_showing.html",{"r":"The provided host wasn't found in the db"},status_code=404)
            received_data={"host":row["host"],"user":row["user"],"description":row["description"],"threshold_cpu":row["threshold_cpu"],"threshold_mem":row["threshold_mem"],"details":row["details"],}
            data = asyncio.run(gather_snmp_info(received_data))
            return templates.TemplateResponse("snmp_shower.html",{"host":host, "data":data})
        except Exception as e:
            return {"error": str(e)}, 500
    
    return RedirectResponse(url=request.url_for("login"), status_code=302)

app.routes.append(Route("/", main_page, methods=["GET", "POST"]))
app.routes.append(Route("/add_category", add_category, methods=["POST"]))
app.routes.append(Route("/add_complex_test", add_complex_test, methods=["POST"]))
app.routes.append(Route("/add_container", add_container, methods=["POST"]))
app.routes.append(Route("/add_cronjob", add_cronjob, methods=["POST"]))
app.routes.append(Route("/add_extra_resource", add_extra_resource, methods=["POST"]))
app.routes.append(Route("/add_sentinel_host", add_sentinel_host, methods=["POST"]))
app.routes.append(Route("/add_snmp", add_snmp, methods=["POST"]))
app.routes.append(Route("/add_test", add_test, methods=["POST"]))
app.routes.append(Route("/advanced-container/{container_name}", get_container_logs_advanced, methods=["GET", "POST"]))
app.routes.append(Route("/certification", certification, methods=["GET"]))
app.routes.append(Route("/clustered_certification", clustered_certification, methods=["GET"]))
app.routes.append(Route("/connect_host", connect_and_store, methods=["POST"]))
app.routes.append(Route("/container/{podname}", get_container_logs, methods=["POST"]))
app.routes.append(Route("/container_is_okay", make_category_green, methods=["POST"]))
app.routes.append(Route("/cronjobs", get_cron_jobs, methods=["POST", "GET"]))
app.routes.append(Route("/deauthenticate", deauthenticate, methods=["POST","GET"]))
app.routes.append(Route("/delete_category", delete_category, methods=["POST"]))
app.routes.append(Route("/delete_complex_test", delete_complex_test, methods=["POST"]))
app.routes.append(Route("/delete_container", delete_container, methods=["POST"]))
app.routes.append(Route("/delete_cronjob", delete_cronjob, methods=["POST"]))
app.routes.append(Route("/delete_extra_resource", delete_extra_resource, methods=["POST"]))
app.routes.append(Route("/delete_saved_host", delete_host, methods=["POST"]))
app.routes.append(Route("/delete_sentinel_host", delete_sentinel_host, methods=["POST"]))
app.routes.append(Route("/delete_snmp_host", delete_snmp_host, methods=["POST"]))
app.routes.append(Route("/delete_test", delete_test, methods=["POST"]))
app.routes.append(Route("/download", redirect_to_download, methods=["GET", "POST"]))
app.routes.append(Route("/downloads/{subpath}", list_files, methods=["GET", "POST"]))
app.routes.append(Route("/edit_category", edit_category, methods=["POST"]))
app.routes.append(Route("/edit_complex_test", edit_complex_test, methods=["POST"]))
app.routes.append(Route("/edit_container", edit_container, methods=["POST"]))
app.routes.append(Route("/edit_cronjob", edit_cronjob, methods=["POST"]))
app.routes.append(Route("/edit_extra_resource", edit_extra_resource, methods=["POST"]))
app.routes.append(Route("/edit_test", edit_test, methods=["POST"]))
app.routes.append(Route("/generate_pdf", generate_pdf, methods=["GET"]))
app.routes.append(Route("/get_complex_test_buttons", get_complex_test_buttons, methods=["GET", "POST"]))
app.routes.append(Route("/get_complex_tests", get_complex_tests, methods=["GET"]))
app.routes.append(Route("/get_data_from_source", get_additional_data, methods=["GET"]))
app.routes.append(Route("/get_host_tops", get_tops, methods=["GET"]))
app.routes.append(Route("/get_local_top", get_local_top, methods=["GET"]))
app.routes.append(Route("/get_muted_components", get_muted_components, methods=["GET"]))
app.routes.append(Route("/get_summary_status", get_summary_status, methods=["GET", "POST"]))
app.routes.append(Route("/get_top", get_top_single, methods=["GET"]))
app.routes.append(Route("/hosts_control_panel", hosts_control_panel, methods=["GET", "POST"]))
app.routes.append(Route("/login", login, methods=["GET", "POST"]))
app.routes.append(Route("/mute_component_by_hours", mute_component_by_hours, methods=["POST"]))
app.routes.append(Route("/organize_categories", organize_categories, methods=["GET"]))
app.routes.append(Route("/organize_complex_tests", organize_complex_tests, methods=["GET"]))
app.routes.append(Route("/organize_containers", organize_containers, methods=["GET"]))
app.routes.append(Route("/organize_cronjobs", organize_cronjobs, methods=["GET"]))
app.routes.append(Route("/organize_extra_resources", organize_extra_resources, methods=["GET"]))
app.routes.append(Route("/organize_tests", organize_tests, methods=["GET"]))
app.routes.append(Route("/read_containers", check, methods=["POST"]))
app.routes.append(Route("/read_containers_db", check_container_db, methods=["GET"]))
app.routes.append(Route("/reboot_container", reboot_container, methods=["POST"]))
app.routes.append(Route("/run_command_host", run_command, methods=["POST"]))
app.routes.append(Route("/run_test", run_test, methods=["POST"]))
app.routes.append(Route("/run_test_complex", run_test_complex, methods=["POST"]))
app.routes.append(Route("/sentinel_hosts_control_panel", sentinel_hosts_control_panel, methods=["GET", "POST"]))
app.routes.append(Route("/snmp_control_panel", snmp_control_panel, methods=["GET"]))
app.routes.append(Route("/snmp_info", snmp_info, methods=["GET"]))
app.routes.append(Route("/test_all_ports", test_all_ports, methods=["GET"]))
app.routes.append(Route("/tests_results", get_tests, methods=["POST"]))
