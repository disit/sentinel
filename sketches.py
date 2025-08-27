from flask import Flask, jsonify, render_template_string, redirect

# --- Config: list of VMs ---
VMs = [
    {"name": "VM1", "ip": "192.168.1.10", "community": "public"},
    {"name": "VM2", "ip": "192.168.1.11", "community": "public"},
    {"name": "VM3", "ip": "192.168.1.12", "community": "public"}
]

# --- Config: list of Hosts ---
Hosts = [
    {"name": "Host1", "ip": "192.168.2.10", "community": "public"},
    {"name": "Host2", "ip": "192.168.2.11", "community": "public"}
]

# fake SNMP function (replace with real SNMP code from earlier example)
def get_system_data(node):
    import random
    return {
        "name": node["name"],
        "ip": node["ip"],
        "cpu": [{"core": 1, "usage_percent": random.randint(10, 90)},
                {"core": 2, "usage_percent": random.randint(10, 90)}],
        "storage": [
            {"name": "/disk", "total_bytes": 1000000,
             "used_bytes": random.randint(200000, 900000),
             "usage_percent": random.randint(20, 90)}
        ],
        "network": [
            {"name": "eth0", "rx_bytes": random.randint(100000, 999999),
             "tx_bytes": random.randint(100000, 999999)}
        ]
    }

# --- Flask App ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f9f9f9; }
        h1 { color: #222; }
        nav { margin-bottom: 20px; }
        nav a { margin-right: 20px; text-decoration: none; font-weight: bold; color: #007bff; }
        nav a:hover { text-decoration: underline; }
        .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); margin-bottom: 30px; padding: 20px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f4f4f4; }
        .buttons { margin-top: 10px; }
        .btn { background: #007bff; color: white; padding: 8px 12px; margin-right: 10px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <nav>
        <a href="{{ url_for('show_vms') }}">VMs</a>
        <a href="{{ url_for('show_hosts') }}">Hosts</a>
    </nav>

    <div id="content"></div>

    <script>
        async function fetchData() {
            const res = await fetch("{{ api_url }}");
            const data = await res.json();
            render(data);
        }

        function render(nodes) {
            const container = document.getElementById("content");
            container.innerHTML = "";
            nodes.forEach(node => {
                let html = `
                <div class="card">
                    <h2>${node.name} (${node.ip})</h2>
                    <h3>CPU Usage</h3>
                    <table><tr><th>Core</th><th>Usage (%)</th></tr>
                        ${node.cpu.map(c => `<tr><td>${c.core}</td><td>${c.usage_percent}</td></tr>`).join("")}
                    </table>
                    <h3>Storage</h3>
                    <table><tr><th>Name</th><th>Total (bytes)</th><th>Used (bytes)</th><th>Usage (%)</th></tr>
                        ${node.storage.map(s => `<tr><td>${s.name}</td><td>${s.total_bytes}</td><td>${s.used_bytes}</td><td>${s.usage_percent}</td></tr>`).join("")}
                    </table>
                    <h3>Network Interfaces</h3>
                    <table><tr><th>Interface</th><th>RX Bytes</th><th>TX Bytes</th></tr>
                        ${node.network.map(n => `<tr><td>${n.name}</td><td>${n.rx_bytes}</td><td>${n.tx_bytes}</td></tr>`).join("")}
                    </table>
                    {% if show_buttons %}
                    <div class="buttons">
                        <a href="/logs/${node.name}" class="btn">Logs</a>
                        <a href="/reboot/${node.name}" class="btn">Reboot</a>
                        <a href="/force_reboot/${node.name}" class="btn">Force Reboot</a>
                    </div>
                    {% endif %}
                </div>`;
                container.innerHTML += html;
            });
        }

        // Initial load
        fetchData();
        // Refresh every 5 seconds
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return redirect("/vms")

@app.route("/vms")
def show_vms():
    return render_template_string(HTML_TEMPLATE, title="VM Dashboard", api_url="/api/vms", show_buttons=True)

@app.route("/hosts")
def show_hosts():
    return render_template_string(HTML_TEMPLATE, title="Host Dashboard", api_url="/api/hosts", show_buttons=False)

# JSON APIs
@app.route("/api/vms")
def api_vms():
    vms_data = [get_system_data(vm) for vm in VMs]
    return jsonify(vms_data)

@app.route("/api/hosts")
def api_hosts():
    hosts_data = [get_system_data(host) for host in Hosts]
    return jsonify(hosts_data)

@app.route("/logs/<node_name>")
def logs(node_name):
    return f"<h2>Logs for {node_name}</h2><p>(Placeholder for logs)</p><a href='/vms'>Back</a>"

@app.route("/reboot/<node_name>")
def reboot(node_name):
    return f"<h2>Rebooting {node_name}</h2><p>(Fake reboot triggered)</p><a href='/vms'>Back</a>"

@app.route("/force_reboot/<node_name>")
def force_reboot(node_name):
    return f"<h2>Force Reboot {node_name}</h2><p>(Fake force reboot triggered)</p><a href='/vms'>Back</a>"

if __name__ == "__main__":
    app.run(debug=True)


from paramiko import SSHClient

# Connect
client = SSHClient()
client.load_system_host_keys()
client.connect('150.217.15.197', username='debian', password='uIkUsCskWee3sc4v')

# Run a command (execute PHP interpreter)
stdin, stdout, stderr = client.exec_command('cd /; ls')
print(type(stdin))  # <class 'paramiko.channel.ChannelStdinFile'>
print(type(stdout))  # <class 'paramiko.channel.ChannelFile'>
print(type(stderr))  # <class 'paramiko.channel.ChannelStderrFile'>

# Optionally, send data via STDIN, and shutdown when done
stdin.write('-lt')
stdin.channel.shutdown_write()

# Print output of command. Will wait for command to finish.
print(f'STDOUT: {stdout.read().decode("utf8")}')
print(f'STDERR: {stderr.read().decode("utf8")}')

# Get return code from command (0 is default for success)
print(f'Return code: {stdout.channel.recv_exit_status()}')

# Because they are file objects, they need to be closed
stdin.close()
stdout.close()
stderr.close()

# Close the client itself
client.close()