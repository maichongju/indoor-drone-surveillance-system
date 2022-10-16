# Script for Pi Monitor Voltage

# import modules
import RPi.GPIO as GPIO
import time
import requests


import netifaces as ni
import requests

API = '/camera/low_battery'
PORT = 8080


def get_ip():
    try:
        ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        return ip
    except Exception:
        return None


def get_host(ip):
    ip = ip.split('.')
    ip[-1] = '1'
    ip = '.'.join(ip)
    return ip


def send_signal():
    global ip
    if ip is None:
        ip = get_ip()
        if ip is None:
            return
    host_ip = get_host(ip)

    # host_ip = '192.168.0.171'

    url = f'http://{host_ip}:{PORT}{API}'
    data = {
        'ip': ip
    }

    try:
        resp = requests.post(url=url, data=data, timeout=1.5)
        print(resp.text)
    except Exception as e:
        print(f'Connection error {url} {e}')


# setup pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN)

ip = get_ip()

while True:
    try:
        if GPIO.input(4) == GPIO.LOW:
            send_signal()
        time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        break
