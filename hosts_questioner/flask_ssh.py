from flask import Flask, request, jsonify, render_template, render_template_string
import paramiko
import mysql.connector
import os
import re
import traceback

app = Flask(__name__)

# MySQL connection details
DB_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'connections'
}

# Path to store SSH keys
KEY_DIR = "./ssh_keys"
os.makedirs(KEY_DIR, exist_ok=True)



def parse_top(data):
    # Initialize dictionaries to hold parsed data
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

###


@app.route('/')
def index():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("CREATE TABLE IF NOT EXISTS host (host VARCHAR(255), user VARCHAR(255))")
        cursor.execute("SELECT host, user FROM host")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("control_panel.html", hosts=rows)
    except Exception as e:
        return f"Error loading hosts: {e}"

###

@app.route('/connect', methods=['POST'])
def connect_and_store():
    host = request.form.get('host')
    user = request.form.get('user')
    password = request.form.get('password')

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

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS host (host VARCHAR(255), user VARCHAR(255))")
        cursor.execute("INSERT INTO host (host, user) VALUES (%s, %s)", (host, user))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/run', methods=['POST'])
def run_command():
    host = request.form.get('host')

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user FROM host WHERE host=%s", (host,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify({"error": "Host not found in DB"})

        user = row['user']
        private_key_path = os.path.join(KEY_DIR, f"{user}_{host}")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, key_filename=private_key_path)

        stdin, stdout, stderr = ssh.exec_command("ps -aux | head -n 10")
        output = stdout.read().decode()
        error = stderr.read().decode()

        ssh.close()

        if error:
            return jsonify({"error": error})
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/delete', methods=['POST'])
def delete_host():
    host = request.form.get('host')

    try:
        # Fetch user from DB
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user FROM host WHERE host=%s", (host,))
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Host not found in DB"})

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

        return jsonify({"status": "deleted"})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/get_tops', methods=['GET'])
def get_tops():

    try:
        # Fetch user from DB
        conn = mysql.connector.connect(**DB_CONFIG)
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
        return render_template("top-viewer.html",data=data_to_send)

    except Exception as e:
        return jsonify({"error": traceback.format_exc()}), 500


if __name__ == '__main__':
    app.run(debug=True)

