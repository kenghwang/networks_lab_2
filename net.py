#!/usr/bin/env python3
# Lab 6 network script
# Based on original BGP exercise

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import OVSController
from mininet.node import OVSKernelSwitch
from argparse import ArgumentParser

import os
import termcolor as T

setLogLevel('info')

parser = ArgumentParser('Configure simple network in Mininet.')
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()


class myTopo(Topo):
    "Simple topology example."

    def __init__(self):
        'Create custom topo.'

        Topo.__init__(self, sopts={'failMode': 'standalone'})

        # Add external AS and switches
        serverOne = self.addHost('extH1', ip='8.8.8.2/24')
        serverTwo = self.addHost('extH2', ip='8.8.8.8/24')
        extGW = self.addHost('extGW', ip='8.8.8.1/24')
        extSwitch = self.addSwitch('extS1')
        self.addLink(serverOne, extSwitch)
        self.addLink(serverTwo, extSwitch)
        self.addLink(extGW, extSwitch)

        # Add internal hosts and switches
        serverOne = self.addHost('srv1', ip='10.0.0.10/24')
        serverTwo = self.addHost('srv2', ip='10.0.0.11/24')
        intGW = self.addHost('intGW')
        desktops = [self.addHost(f'h{i}', ip='0.0.0.0/24') for i in range(5)]
        leftSwitch = self.addSwitch('s1')
        rightSwitch = self.addSwitch('s2')

        # Add links
        self.addLink(serverOne, leftSwitch)
        self.addLink(serverTwo, leftSwitch)
        self.addLink(leftSwitch, rightSwitch)
        self.addLink(intGW, rightSwitch)
        for i in range(len(desktops)):
            self.addLink(rightSwitch, f'h{i}')
        self.addLink(intGW, extGW)


def log(msg, col='green'):
    print(T.colored(msg, col))


def enableNAT(net, hostn):
    # Assumes internal interface eth0, external interface eth1 and LAN 10.0.0.0/24.
    host = net.getNodeByName(hostn)
    host.cmd(
        'iptables -A FORWARD -o %s-eth1 -i %s-eth0 -s 10.0.0.0/24 '
        '-m conntrack --ctstate NEW -j ACCEPT' % (hostn, hostn)
    )
    host.cmd('iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT')
    host.cmd('iptables -t nat -F POSTROUTING')
    host.cmd('iptables -t nat -A POSTROUTING -o %s-eth1 -j MASQUERADE' % hostn)


def startWebserver(net, hostname, text='Default web server'):
    host = net.getNodeByName(hostname)
    return host.popen("python3 webserver.py --text '%s'" % text, shell=True)


def main():
    os.system('rm -f /tmp/R*.log /tmp/R*.pid logs/*')
    os.system('mn -c >/dev/null 2>&1')
    os.system('pgrep -f webserver.py | xargs kill -9')
    os.system('killall -9 dnsmasq')

    net = Mininet(topo=myTopo(), controller=OVSController, autoSetMacs=True)
    net.start()

    # Set default routes for ext hosts
    for h in ['extH1', 'extH2']:
        host = net.getNodeByName(h)
        host.cmd('route add default gw 8.8.8.1')

    # Let extGW drop all private network packets.
    host = net.getNodeByName('extGW')
    host.cmd('iptables -I FORWARD -s 10.0.0.0/24 -j DROP')

    # Enable forwarding for the routers
    routes = {'intGW': '2.2.2.1', 'extGW': '2.2.2.2'}
    firstIP = {'intGW': '10.0.0.1', 'extGW': '8.8.8.1'}
    secondIP = {'intGW': '2.2.2.2', 'extGW': '2.2.2.1'}
    for h in ['intGW', 'extGW']:
        host = net.getNodeByName(h)
        host.cmd('sysctl -w net.ipv4.ip_forward=1')
        host.cmd('ifconfig %s-eth0 %s netmask 255.255.255.0' % (h, firstIP[h]))
        host.cmd('ifconfig %s-eth1 %s netmask 255.255.255.0' % (h, secondIP[h]))
        host.cmd('route add default gw %s' % routes[h])

    # Enable NAT on intGW
    enableNAT(net, 'intGW')

    log('Configured the routers')

    # Start DNS server on 8.8.8.8
    host = net.getNodeByName('extH2')
    host.cmd('dnsmasq -C ./extH2DNS.conf')
    log('Done with dnsmasq')

    # Start DHCP on srv1
    host = net.getNodeByName('srv1')
    host.cmd('dnsmasq -C ./srv1DHCP.conf')
    host.cmd('route add default gw 10.0.0.1')
    log('Done with dnsmasq start')

    # Configure server 2
    host = net.getNodeByName('srv2')
    host.cmd('route add default gw 10.0.0.1')
    log('Added the route')

    # Request DHCP leases for internal hosts
    for i in range(5):
        host = net.getNodeByName(f'h{i}')
        host.cmd(f'dhclient -r h{i}-eth0')
        host.cmd(f'dhclient h{i}-eth0')
        log(f'Received IP for h{i}')

    log('Starting web servers', 'yellow')
    startWebserver(net, 'extH1', '50.012 Networks web server')

    # resolv.conf is shared between guests and host. Updating is generally unreliable.
    os.system("echo 'nameserver 8.8.8.8' > /etc/resolv.conf")
    CLI(net)
    net.stop()
    os.system('killall -9 dnsmasq')
    os.system('pgrep -f webserver.py | xargs kill -9')


if __name__ == '__main__':
    main()
