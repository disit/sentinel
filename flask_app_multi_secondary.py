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
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import telegram
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import base64
import random
import string
import traceback
import re
from urllib.parse import urlparse
from datetime import datetime, timedelta


f = open("conf.json")
config = json.load(f)


API_TOKEN = config['telegram-api-token']
bot = telegram.Bot(token=API_TOKEN)
greendot = """&#128994"""
reddot = """&#128308"""

# edit this block according to your mysql server's configuration
db_conn_info = {
        "user": config['db-user'],
        "passwd": config['db-passwd'],
        "host": config['db-host'],
        "port": config['db-port'],
        "database": "checker",
        "auth_plugin": 'mysql_native_password'
    }


def send_telegram(chat_id, message):
    if not config['is-master']:
        return
    if isinstance(message, list):
        message[2]=filter_out_muted_containers_for_telegram(message[2])
    asyncio.run(bot.send_message(chat_id=chat_id, text=str(message)))
    return

def format_error_to_send(instance_of_problem, containers, because = None, explain_reason=None):
    using_these = ', '.join('"{0}"'.format(w) for w in containers.split(","))
    if because:
        becauses=because.split(",")
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        query2 = 'SELECT category, component, position FROM checker.component_to_category where component in ({}) order by category;'.format(using_these)
        cursor.execute(query2)
        now_it_is = cursor.fetchall()
    newstr=""
    for a in now_it_is:
        curstr="In category " + a[0] + ", located in " + a[2] + " the docker container named " + a[1] + " " + instance_of_problem
        if because:
            newstr += curstr + explain_reason + becauses.pop(0)+"\n"
        else:
            newstr += curstr+"\n"
    return newstr

def get_top():
    process = subprocess.Popen(['top', '-b', '-n', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, _ = process.communicate()

    # Initialize dictionaries to hold parsed data
    parsed_data = {
        'system_info': {},
        'cpu_usage': {},
        'memory_usage': {},
        'processes': [],
        "memory_measuring_unit": "B"
    }
    
    # Split output into lines
    lines = stdout.splitlines()
    
    # Parse system information (first line typically)
    system_info_line = lines[0]
    parsed_data['system_info'] = {
        'time': re.search(r'\d{2}:\d{2}:\d{2}', system_info_line).group(),
        'up_time': re.search(r'up\s+([^,]+)', system_info_line).group(1),
        'users': re.search(r'(\d+)\s+users', system_info_line).group(1),
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

def send_email(sender_email, sender_password, receiver_emails, subject, message):
    if not config['is-master']:
        return
    composite_message = config['platform-explanation'] + "\n" + message
    smtp_server = config['smtp-server']
    smtp_port = config['smtp-port']
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender_email, sender_password)
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ','.join(receiver_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(str(composite_message), 'plain'))
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
    if config['is-master']:
        send_email(config["sender-email"], config["sender-email-password"], config["email-recipients"], config["platform-url"]+" is alive", config["platform-url"]+" is alive")
        send_telegram(config['telegram-channel'], config["platform-url"]+" is alive")
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
                command_ran = subprocess.run(r[0], shell=True, capture_output=True, text=True, encoding="cp437").stdout
                total_result += command_ran
                if "Failure" in command_ran:
                    badstuff.append({"container":r[1], "result":command_ran, "command":r[2]})
            return badstuff
    except Exception:
        print("Something went wrong during tests running because of:",traceback.format_exc())
        return badstuff

def auto_alert_status():
    results = None
    
    # grab all but containers on this host
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        query = '''SELECT distinct position FROM checker.component_to_category;'''
        cursor.execute(query)
        conn.commit()
        results = cursor.fetchall()
        total_answer=[]
        for r in results:
            obtained = requests.post(r[0]+"/read_containers").text
            try:
                total_answer = total_answer + json.loads(obtained)
            except:
                try:
                    obtained = requests.post(r[0]+"/sentinel/read_containers", headers=request.headers).text
                    total_answer = total_answer + json.loads(obtained)
                except:
                    pass
        
    # now grab containers from this host
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
    containers_merged = containers_merged + total_answer
    components = [a[0].replace("*","") for a in results]
    components_original = [a[0] for a in results]
    containers_which_should_be_running_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and (c["State"] != "running")]
    containers_which_should_be_exited_and_are_not = [c for c in containers_merged if any(c["Names"].startswith(value) for value in ["certbot"]) and c["State"] != "exited"]
    containers_which_are_running_but_are_not_healthy = [c for c in containers_merged if any(c["Names"].startswith(value) for value in components) and "unhealthy" in c["Status"]]
    problematic_containers = containers_which_should_be_exited_and_are_not + containers_which_should_be_running_and_are_not + containers_which_are_running_but_are_not_healthy
    #containers_which_are_fine = list(set([n["Names"] for n in containers_merged]) - set([n["Names"] for n in problematic_containers]))
    names_of_problematic_containers = [n["Names"] for n in problematic_containers]
    containers_which_are_not_expected = list(set(components_original)-set([a["Names"] for a in containers_merged]))
    containers_which_are_not_expected = [a for a in containers_which_are_not_expected if not a.endswith("*")]
    if len(names_of_problematic_containers) > 0 or len(is_alive_with_ports) > 0 or len(containers_which_are_not_expected):
        try:
            issues = ["","",""] # maybe make this a real object, later
            if len(names_of_problematic_containers) > 0:
                issues[0]=problematic_containers
            if len(is_alive_with_ports) > 0:
                issues[1]=is_alive_with_ports #this has to be refined
            if len(containers_which_are_not_expected) > 0:
                issues[2]=containers_which_are_not_expected
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


mutex = Lock()
def queued_running(command):
    answer = None
    print("Locking executor due to running", command)
    with mutex:
        answer = subprocess.run(command, shell=True, capture_output=True, text=True, encoding="utf_8")
    print ("Unlocked executor")
    return answer
    
    
def send_alerts(message):
    if not config['is-master']:
        return
    try:
        send_email(config["sender-email"], config["sender-email-password"], config["email-recipients"], config["platform-url"]+" is in trouble!", message)
        send_telegram(config["telegram-channel"], message)
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
        
def update_container_state_db():
    if not config['is-master']:
        return        
    results = None
    # grab all but containers on this host
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        query = '''SELECT distinct position FROM checker.component_to_category;'''
        cursor.execute(query)
        conn.commit()
        results = cursor.fetchall()
        total_answer=[]
        for r in results:
            obtained = requests.post(r[0]+"/read_containers").text
            try:
                total_answer = total_answer + json.loads(obtained)
            except:
                try:
                    obtained = requests.post(r[0]+"/sentinel/read_containers", headers=request.headers).text
                    total_answer = total_answer + json.loads(obtained)
                except:
                    pass
        
    # now grab containers from this host
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
    try:
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''SELECT * FROM checker.component_to_category;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
    except Exception:
        send_alerts("Can't reach db, didn't update cluster status:"+ traceback.format_exc())
        return
    containers_merged = containers_merged + total_answer
    with mysql.connector.connect(**db_conn_info) as conn:
        cursor = conn.cursor(buffered=True)
        query = '''INSERT INTO `checker`.`container_data` (`containers`) VALUES (%s);'''
        cursor.execute(query,(json.dumps(containers_merged),))
        conn.commit()


def send_advanced_alerts(message):
    if not config['is-master']:
        return
    try:
        text_for_email, em1, em2, em3 = "", "", "", ""
        if len(message[0])>0:
            em1 = format_error_to_send("is not in the correct status ",", ".join([a["Name"] for a in message[0]]),", ".join([a["Status"] for a in message[0]]),"as its status currently is: ")
            text_for_email = "These containers are not in the correct status: " + ", ".join([a["Name"] for a in message[0]])+"\n"
        if len(message[1])>0:
            em2 = format_error_to_send("is not answering correctly to its 'is alive' test ",", ".join([a["container"] for a in message[1]]),", ".join([a["command"] for a in message[1]]),"given the failure of: ")
            text_for_email+= 'These containers are not answering correctly to their "is alive" test: '+ ", ".join([a["container"] for a in message[1]])+"\n"
        if len(message[2])>0:
            em3 = format_error_to_send("wasn't found running in docker ",", ".join(message[2]))
            text_for_email+= "These containers weren't found in docker: "+ ", ".join(message[2])+"\n"
        try:
            send_email(config["sender-email"], config["sender-email-password"], config["email-recipients"], config["platform-url"]+" is in trouble!", em1+"\n"+em2+"\n"+em3)
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
            t3=format_error_to_send("wasn't found running in docker ",filter_out_muted_containers_for_telegram(message[2]))
            text_for_telegram+= "These containers weren't found in docker: "+ str(filter_out_muted_containers_for_telegram(message[2]))+"\n"
        if len(text_for_telegram)>0:
            try:
                send_telegram(config['telegram-channel'], t1+"\n"+t2+"\n"+t3)
            except:
                print("[ERROR] while sending telegram:",t1+"\n"+t2+"\n"+t3,"\nDue to",traceback.format_exc())
    except Exception:
        print("Error sending alerts:",traceback.format_exc())
 
        
    
scheduler = BackgroundScheduler()
scheduler.add_job(auto_alert_status, trigger='interval', minutes=5)
scheduler.add_job(isalive, 'cron', hour=8, minute=0)
scheduler.add_job(isalive, 'cron', hour=20, minute=0)
scheduler.start()
auto_alert_status()
def create_app():
    app = Flask(__name__)
    app.secret_key = b'\x8a\x17\x93kT\xc0\x0b6;\x93\xfdp\x8bLl\xe6u\xa9\xf5x'

    @app.route("/")
    def main_page():
        if config['is-master']:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    user = ""
                    try:
                        user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
                        user = user[:user.find(":")]
                    except Exception:
                        pass
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''SELECT complex_tests.*, GetHighContrastColor(button_color), COALESCE(categories.category, "System") as category FROM checker.complex_tests left join category_test on id = category_test.test left join categories on categories.idcategories = category_test.category;'''
                    cursor.execute(query)
                    conn.commit()
                    results = cursor.fetchall()
                    if user != "admin":
                        return render_template("checker.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),timeout=config['requests-timeout'],user=user)
                    else:
                        query_2 = '''select * from all_logs limit %s;'''
                        cursor.execute(query_2, (config['admin-log-length'],))
                        conn.commit()
                        results_log = cursor.fetchall()
                        return render_template("checker-admin.html",extra=results,categories=get_container_categories(),extra_data=get_extra_data(),admin_log=results_log,timeout=config['requests-timeout'],user=user,platform=config["platform-url"])
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403

    @app.route("/organize_containers", methods=["GET"])
    def organize_containers():
        if config['is-master']:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    user = ""
                    try:
                        user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
                        user = user[:user.find(":")]
                    except Exception:
                        pass
                    if user!="admin":
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
                    return render_template("organize_containers.html",containers=results, categories=results_2,timeout=config['requests-timeout'])
            except Exception:
                print("Something went wrong because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        
    @app.route("/add_container", methods=["POST"])
    def add_container():
        if config['is-master']:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    user = ""
                    try:
                        user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
                        user = user[:user.find(":")]
                    except Exception:
                        pass
                    if user!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''INSERT INTO `checker`.`component_to_category` (`component`, `category`, `references`, `position`) VALUES (%s, %s, %s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],request.form.to_dict()['category'],request.form.to_dict()['contacts'], request.form.to_dict()['position'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the addition of a new container because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        
    @app.route("/delete_container", methods=["POST"])
    def delete_container():
        if config['is-master']:
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    user = ""
                    try:
                        user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
                        user = user[:user.find(":")]
                    except Exception:
                        pass
                    if user!="admin":
                        return render_template("error_showing.html", r = "You do not have the privileges to access this webpage."), 401
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''DELETE FROM `checker`.`component_to_category` WHERE (`component` = %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],))
                    conn.commit()
                    return "ok", 201
            except Exception:
                print("Something went wrong during the deletion of a container because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403

    @app.route("/get_data_from_source", methods=["GET"])
    def get_additional_data():
        try:
            response = requests.get(request.args.to_dict()['url_of_resource'])
            response.raise_for_status()
            return response.text
        except Exception:
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    
    @app.route("/get_complex_test_buttons")
    def get_complex_test_buttons():
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
        
    @app.route("/container_is_okay", methods=['POST'])
    def make_category_green():
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
        
    @app.route("/read_containers", methods=['POST'])
    def check():
        return get_container_data()
    
    @app.route("/read_containers_db", methods=['GET'])
    def check_container_db():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
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
            
    @app.route("/advanced_read_containers", methods=['POST'])
    def check_adv():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
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
                    obtained = requests.post(r[0]+"/read_containers", headers=request.headers).text
                    try:
                        total_answer = total_answer + json.loads(obtained)
                    except:
                        try:
                            obtained = requests.post(r[0]+"/sentinel/read_containers", headers=request.headers).text
                            total_answer = total_answer + json.loads(obtained)
                        except Exception as E:
                            errors.append("Reading containers from "+r[0]+" failed: the backed received this exception: "+str(E))
                tobereturned_answer = {"result":total_answer, "error":errors}
                return tobereturned_answer
        except Exception:
            print("Something went wrong because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500

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
        
    @app.route("/run_test", methods=['POST','GET'])
    def run_test():
        if request.method == "POST":
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
                    print(total_result)
                    return jsonify(total_result, command_ran_explained)
            except Exception:
                print("Something went wrong during tests running because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        else:
            log_to_db('asking_containers', "POST wasn't used in the request", request)
            return "False"
        
    @app.route("/run_test_complex", methods=['POST','GET'])
    def run_test_complex():
        if request.method == "POST":
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
                        log_to_db('test_ran', "Executing the complex test " + test_name + " resulted in: " +string_used, request, test_name="advanced test - "+r[1])
                    return jsonify(total_result)
            except Exception:
                print("Something went wrong during tests running because of",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        else:
            log_to_db('asking_containers', "POST wasn't used in the request", request)
            return "False"
        
    @app.route("/reboot/<container_id>", methods=['POST', 'GET'])
    def reboot(container_id):
        try:
            return render_template("reboot.html", container=container_id)
        except Exception:
            print("Something went wrong during rebooting because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 500
        
    @app.route("/get_top", methods=["GET"])
    def get_all_top():
        with mysql.connector.connect(**db_conn_info) as conn:
            cursor = conn.cursor(buffered=True)
            query = '''SELECT distinct position FROM checker.component_to_category;'''
            cursor.execute(query)
            conn.commit()
            results = cursor.fetchall()
            total_answer=[]
            errors = []
            for r in results:
                obtained = requests.post(r[0]+"/get_local_top", headers=request.headers).text
                try:
                    currentjson=json.loads(obtained)
                    currentjson["source"]=r[0]
                    total_answer.append(currentjson)
                except:
                    try:
                        obtained = requests.post(r[0]+"/sentinel/get_local_top", headers=request.headers).text
                        currentjson=json.loads(obtained)
                        currentjson["source"]=r[0]
                        total_answer.append(json.loads(obtained))
                    except Exception as E:
                        errors.append("Reading top from "+r[0]+" failed: the backed received this exception: "+str(E))
            #tobereturned_answer = {"result":total_answer, "error":errors}
            #return tobereturned_answer
        return render_template("top-viewer.html", data=total_answer), 200
        

    @app.route("/get_local_top", methods=["GET"])
    def get_local_top():
        json_data=get_top()
        try:
            form_dict = request.form.to_dict()
            amount_of_lines = form_dict.pop('top_lines')
            json_data['processes']=json_data['processes'][:int(amount_of_lines)]
        except Exception as E:
            json_data['processes']=json_data['processes'][:40]
            pass
        return json_data
        
        
    @app.route("/test_all_ports", methods=['GET'])
    def test_all_ports():
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
            
    @app.route("/deauthenticate", methods=['POST','GET'])
    def deauthenticate():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        return "You have been deauthenticated", 401
        
    @app.route("/reboot_container", methods=['POST','GET'])
    def reboot_container():
        if request.method == "POST":
            something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
            psw = something[something.find(":")+1:]
            if psw == request.form.to_dict()['psw']:
                result = queued_running('docker restart '+request.form.to_dict()['id']).stdout
                log_to_db('rebooting_containers', 'docker restart '+request.form.to_dict()['id']+' resulted in: '+result, request)
                return result
            else:
                log_to_db('rebooting_containers', 'wrong authentication while restarting '+request.form.to_dict()['id'], request)
                return "Container not rebooted", 401
        else: 
            log_to_db('rebooting_containers', "POST wasn't used in the request", request)
            return "False"
            
    @app.route("/reboot_container_advanced/<container_id>", methods=['POST','GET'])
    def reboot_container_advanced(container_id):
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        if request.method == "POST":
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
                    psw = something[something.find(":")+1:]
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''SELECT position FROM checker.component_to_category where component=%s;'''
                    cursor.execute(query, (container_id,))
                    conn.commit()
                    results = cursor.fetchall()
                    try:
                        r = requests.post(results[0][0]+"/sentinel/reboot_container", headers=request.headers, data={"id": container_id, "psw": psw})
                        return r.text
                    except:
                        r = requests.post(results[0][0]+"/reboot_container", headers=request.headers, data={"id": container_id, "psw": psw})
                        return r.text
            except Exception:
                print("Something went wrong during advanced container rebooting because of:",traceback.format_exc())
                return render_template("error_showing.html", r = traceback.format_exc()), 500
        else: 
            log_to_db('rebooting_containers', "POST wasn't used in the request", request)
            return "False"
            
    @app.route("/get_muted_components", methods=['GET'])
    def get_muted_components():
        if request.method == "GET":
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
        else: 
            return "You can't use a POST here.", 400
            
    @app.route("/mute_component_by_hours", methods=['POST'])
    def mute_component_by_hours():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        if request.method == "POST":
            try:
                with mysql.connector.connect(**db_conn_info) as conn:
                    something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
                    psw = something[something.find(":")+1:]
                    cursor = conn.cursor(buffered=True)
                    # to run malicious code, malicious code must be present in the db or the machine in the first place
                    query = '''INSERT INTO telegram_alert_pauses (`component`, `until`) VALUES (%s, %s);'''
                    cursor.execute(query, (request.form.to_dict()['id'],(datetime.now() + timedelta(hours=int(request.form.to_dict()['hours']))).strftime("%Y-%m-%d %H:%M:%S"),))
                    conn.commit()
                    return "ok", 200
            except Exception:
                print("Something went wrong during muting a component because of:",traceback.format_exc())
                return traceback.format_exc(), 500
        else: 
            return "You may only use a POST here.", 400
        
    @app.route("/tests_results", methods=['POST','GET'])
    def get_tests():
        if request.method == "POST":
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
        else: 
            log_to_db('getting_tests', "POST wasn't used in the request", request)
            return "False"
        
    # this is only called serverside
    def log_to_db(table, log, request=None, which_test=""):
        if (request):
            user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
            user = user[:user.find(":")] 
        else:
            user = "Unidentified user"
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                if table != "test_ran":
                    cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator) VALUES (NOW(),'{}','{}')'''.format(table, log.replace("'","''"), user))
                else:
                    cursor.execute('''INSERT INTO `{}` (datetime, log, perpetrator, test) VALUES (NOW(),'{}','{}','{}')'''.format(table, log.replace("'","''"), user, which_test))
                conn.commit()
        except Exception:
            print("Something went wrong during db logging because of:",traceback.format_exc(), "- in:",table)
            
    @app.route("/load_db",methods=['POST'])
    def load_db():
        trying_to_load_db_resulted_in = subprocess.run(f"mysql -u {config['db-user']} --password={config['db-passwd']} -D checker < just_complex.sql", shell=True, capture_output=True, text=True, encoding="utf_8")
        out = trying_to_load_db_resulted_in.stdout
        err = trying_to_load_db_resulted_in.stderr
        if "mysql: [Warning] Using a password on the command line interface can be insecure" in err:
            err = ""
        else:
            err = '<p style="color:#FF0000";>'+err+'</p>'
        if len(err)==0 and len(out)==0:
            out = '<input type="button" name="db-success" id="db-success" value="Success! Click to reload" class="form-control" onclick="location.reload()"/>'
        return err+out
    
    
    @app.route("/get_complex_tests", methods=["GET"])
    def get_complex_tests():
        if request.method == "GET":
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
        else: 
            log_to_db('getting_tests', "POST wasn't used in the request", request)
            return "False"
    
    @app.route("/container/<container_id>") #still answers to everyone
    def get_container_logs(container_id):
        something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
        try:
            user = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
            psw = something[something.find(":")+1:]
            # maybe use user and psw later
        except Exception:
            print("Probably fucked up the authentication:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc()), 401
        r = '<br>'.join(subprocess.run('docker logs '+container_id+" --tail "+str(config["default-log-length"]), shell=True, capture_output=True, text=True, encoding="utf_8").stdout.split('\n'))
        #print('docker logs '+container_id+" --tail "+str(config["default-log-length"]))
        #container_name = subprocess.run('docker ps -a -f id='+container_id+' --format "{{.Names}}"', shell=True, capture_output=True, text=True, encoding="utf_8").stdout.split('\n')[0]
        return render_template('log_show.html', container_id = container_id, r = r, container_name=container_id)
        
    @app.route("/advanced-container/<container_id>")
    def get_container_logs_advanced(container_id):
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                something = str(base64.b64decode(request.headers["Authorization"][len("Basic "):]))[:-1]
                psw = something[something.find(":")+1:]
                cursor = conn.cursor(buffered=True)
                # to run malicious code, malicious code must be present in the db or the machine in the first place
                query = '''SELECT position FROM checker.component_to_category where component=%s;'''
                cursor.execute(query, (container_id,))
                conn.commit()
                results = cursor.fetchall()
                if len(results) == 0:
                    return render_template("error_showing.html", r = "It appears that the container "+container_id+" doesn't exist in the cluster."), 500
                try:
                    r = requests.get(results[0][0]+"/sentinel/container/"+container_id, headers=request.headers, data={"id": container_id, "psw": psw})            
                    return r.text
                except:
                    r = requests.get(results[0][0]+"/container/"+container_id, headers=request.headers, data={"id": container_id, "psw": psw})
                    return r.text
        except Exception:
            print("Something went wrong during advanced container rebooting because of:",traceback.format_exc())
            return render_template("error_showing.html", r = traceback.format_exc() + str(results)), 500
    
    @app.route("/get_summary_status")
    def get_summary_status():
        try:
            with mysql.connector.connect(**db_conn_info) as conn:
                cursor = conn.cursor(buffered=True)
                cursor.execute('''SELECT * FROM summary_status;''')
                results = cursor.fetchall()
                return jsonify(results)
        except Exception:
            print("Something went wrong during db logging because of:",traceback.format_exc())
    
    def get_container_data(do_not_jsonify=False):
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
    
    @app.route('/generate_clustered_pdf', methods=['GET'])
    def generate_clustered_pdf():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        user = ""
        try:
            user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
            user = user[:user.find(":")]
        except Exception:
            return render_template("error_showing.html", r = "Issues during the establishing of the user: "+ traceback.format_exc()), 500
        if user != "admin":
            return render_template("error_showing.html", r = "User is not authorized to perform the operation."), 401
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
                subprocess.run(f'rm -f *-*logs.pdf snap4city-clustered-reports.pdf.rar', shell=True)
                for r in results:
                    file_name, content_disposition = "", ""
                    obtained = requests.get(r[0]+"/sentinel/generate_pdf", headers=request.headers)
                    if 'Content-Disposition' in obtained.headers:
                        content_disposition = obtained.headers['Content-Disposition']
                    if 'filename=' in content_disposition:
                        file_name = content_disposition.split('filename=')[1].strip('"')
                    if len(file_name) < 1:
                        errorText += "Couldn't quite get the file: " + r[0] + "\n"
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
                    subfolder = "pdf-cluster-"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    print(subprocess.run(f"rar a snap4city-clustered-reports.pdf.rar *-*logs.pdf; mkdir {subfolder}; cp snap4city-clustered-reports.pdf.rar {subfolder}/snap4city-clustered-reports.pdf.rar", shell=True, capture_output=True, text=True, encoding="utf_8").stdout)
                    return send_file(f'snap4city-clustered-reports.pdf.rar')
        except Exception:
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    
    @app.route('/generate_pdf', methods=['GET'])
    def generate_pdf():
        data_stored = []
        for container_data in get_container_data(True):
            r = '<br>'.join(subprocess.run('docker logs '+container_data['ID'] + ' --tail '+str(config["default-log-length"]), shell=True, capture_output=True, text=True, encoding="utf_8").stdout.split('\n'))
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
                logs_file_path = os.path.join(root, 'log.txt')
                log_output = subprocess.run(f'cd {root}; tail -n {config["default-log-length"]} log.txt', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
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
                content.append(Paragraph(substring, styles["Normal"]))
            content.append(PageBreak())
        for extra in extra_logs:
            content.append(extra)
        content.append(PageBreak())
        for test in extra_tests:
            content.append(Paragraph(f'<b><a name="t-{test[3]}"></a>{test[3]}</b>', styles["Heading1"]))
            content.append(Paragraph(test[2].replace("<br>","<br></br>"), styles["Normal"]))
            content.append(PageBreak())
        # Add content to the PDF document
        doc.build(content)
        # Send the PDF file as a response
        response = send_file(pdf_output_path)
        return response
    
    def find_target_folder(parent_folder):
        for root, dirs, files in os.walk(parent_folder):
            if "docker-compose.yml" in files and "setup.sh" in files:
                return root
        return None
    
    @app.route('/clear_certifications', methods=['GET'])
    def clear_certifications():
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
        
    
    @app.route('/certification', methods=['GET'])
    def certification():
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
        subfolder = "cert"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_folder = find_target_folder(parent_folder)
        
        if target_folder:
            password = ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(16))
            make_certification = subprocess.run(f'cd {target_folder}; mkdir {subfolder}; bash make_dumps_of_database.sh; rar a -k -p{password} snap4city-certification-{password}.rar iotapp-00*/flows.json d*conf iot-directory-conf m*conf n*conf ownership-conf/config.php nifi/conf servicemap-conf/servicemap.properties ../placeholder_used.txt *dump.* php-css-dump servicemap-iot-conf/iotdeviceapi.dtd servicemap-superservicemap-conf/settings.xml synoptics-conf/ mongo_dump virtuoso_dump php ../checker/flask_app.py sysinfo.txt ; cp snap4city-certification-{password}.rar {subfolder}/snap4city-certification-{password}.rar', shell=True, capture_output=True, text=True, encoding="utf_8")
            if len(make_certification.stderr) > 0:
                return send_file(target_folder + f'/{subfolder}/snap4city-certification-{password}.rar')
                # bypass this shit, for now
                return render_template("error_showing.html", r = "There were issues: "+ make_certification.stderr), 500
            else:
                return send_file(target_folder + f'/snap4city-certification-{password}.rar')
        else:
            return render_template("error_showing.html", r = "Couldn't find the snap4city installation."), 500
            
    @app.route('/clustered_certification', methods=['GET'])
    def clustered_certification():
        if not config['is-master']:
            return render_template("error_showing.html", r = "This Snap4Sentinel instance is not the master of its cluster."), 403
        user = ""
        try:
            user = base64.b64decode(request.headers["Authorization"][len('Basic '):]).decode('utf-8')
            user = user[:user.find(":")]
        except Exception:
            return render_template("error_showing.html", r = "Issues during the establishing of the user: "+ traceback.format_exc()), 500
        if user != "admin":
            return render_template("error_showing.html", r = "User is not authorized to perform the operation."), 401
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
                subfolder = "certcluster"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
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
                    subprocess.run(f'rar a -k -p{password} snap4city-clustered-certification-{password}.rar *snap4city-certification-*.rar; mkdir {subfolder}; cp snap4city-clustered-certification-{password}.rar {subfolder}/snap4city-clustered-certification-{password}.rar', shell=True, capture_output=True, text=True, encoding="utf_8").stdout
                    return send_file(f'snap4city-clustered-certification-{password}.rar')
        except Exception:
            return render_template("error_showing.html", r = traceback.format_exc()), 500
    return app
    
if __name__ == "__main__":
    create_app().run(host='localhost', port=4080)
