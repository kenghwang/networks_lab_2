#!/bin/bash
# Install script for 50.012 Lab2 (Python 3)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo apt-get update
sudo apt-get install -y \
	dnsmasq \
	mininet \
	openvswitch-switch \
	openvswitch-testcontroller \
	isc-dhcp-client \
	net-tools \
	psmisc \
	procps \
	python3 \
	python3-pip \
    xterm

# Some Mininet setups look for ovs-controller specifically.
if ! command -v ovs-controller >/dev/null 2>&1 && command -v ovs-testcontroller >/dev/null 2>&1; then
	sudo ln -sf "$(command -v ovs-testcontroller)" /usr/local/bin/ovs-controller
fi

sudo python3 -m pip install --upgrade 'pip>=23,<24.1'
sudo python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
sudo python3 -m pip install 'termcolor>=1.1.0,<3'
