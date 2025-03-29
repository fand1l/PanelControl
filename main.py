from flask import Flask, render_template, redirect, request, jsonify
import sys
import libvirt
from os import getcwd
import json
import hashlib
import subprocess
import paramiko
import time


root_folder = getcwd()
app = Flask(__name__, template_folder=f"{root_folder}/html")


def load_passwords():
    with open("settings/checksum.json", "r") as f:
        return json.load(f)


def hash_password(password):
    return hashlib.sha3_512(password.encode('utf-8')).hexdigest()


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/license')
def license():
    return redirect("https://github.com/fand1l/PanelControl?tab=GPL-3.0-1-ov-file", code=302)

@app.route('/login', methods=["post", "get"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        passwords = load_passwords()
        
        if username in passwords:
            if hash_password(password) == passwords[username]["pass"]:
                return redirect("choose_os")
            else:
                return "Неправильний пароль"
        else:
            return "Користувача не знайдено"

cpu_prev_time = 0
prev_timestamp = time.time()

@app.route('/stats/<vm_name>')
def stats(vm_name):
    global cpu_prev_time, prev_timestamp

    try:
        conn = libvirt.open("qemu:///system")
        dom = conn.lookupByName(vm_name)

        # Отримання поточного CPU часу
        cpu_stats = dom.getCPUStats(True)[0]
        new_cpu_time = cpu_stats["cpu_time"]

        # Отримання поточного часу
        new_timestamp = time.time()
        time_diff = new_timestamp - prev_timestamp

        # Обчислення використання CPU
        if time_diff > 0:
            cpu_usage = ((new_cpu_time - cpu_prev_time) / 1e9) / time_diff * 100
        else:
            cpu_usage = 0

        # Оновлення змінних для наступного виклику
        cpu_prev_time = new_cpu_time
        prev_timestamp = new_timestamp

        # Використання пам'яті
        mem_stats = dom.memoryStats()
        
        # Перевірка інших полів для пам'яті
        used_memory = (mem_stats.get("rss", 0) / 1024)  # може бути інший параметр, наприклад "actual"

        conn.close()
        return jsonify({"cpu": round(cpu_usage, 2), "memory": round(used_memory, 2)})

    except Exception as e:
        return jsonify({"error": str(e)})



@app.route('/choose_os', methods=["post", "get"])
def choose_os():
    return render_template("panel/choose_os.html")

@app.route('/panel_debian', methods=["post", "get"])
def panel_debian():
    return render_template("panel/panel_debian.html")

@app.route('/panel_archlinux', methods=["post", "get"])
def panel_archlinux():
    return render_template("panel/panel_archlinux.html")

@app.route('/panel_fedora', methods=["post", "get"])
def panel_fedora():
    return render_template("panel/panel_fedora.html")


@app.route('/power_on', methods=["POST"])
@app.route('/power_off', methods=["POST"])
@app.route('/reboot', methods=["POST"])
def handle_vm_action():
    vm_name = request.form.get("vm_name")
    if vm_name:
        if request.path == '/power_on':
            print(f"Powering on {vm_name}")
            subprocess.run(['sudo', 'virsh', 'start', vm_name])

        elif request.path == '/power_off':
            print(f"Powering off {vm_name}")
            subprocess.run(['sudo', 'virsh', 'shutdown', vm_name])

        elif request.path == '/reboot':
            print(f"Rebooting {vm_name}")
            subprocess.run(['sudo', 'virsh', 'reboot', vm_name])

        return "", 204
    else:
        return "", 400


if __name__ == '__main__':
    app.run(debug=True, port=1234)
