#!/bin/bash

if [ "$(id -u)" -ne 0 ];
then
	echo "This script can only run as root"
	exit 1
fi

if [ ! -f "./img/gkd.png" ];
then
	echo "Unable to find required files"
	exit 1
fi

cp ./img/gkd.png /usr/share/pixmaps/
chmod 644 /usr/share/pixmaps/gkd.png

mkdir -p /opt/gkd/
chmod 755 /opt/gkd/

cp ./gatekeeperdesktop.py /opt/gkd/
chmod 755 /opt/gkd/gatekeeperdesktop.py

cp share/gkd.program  /usr/share/applications
chmod 644 /usr/share/applications/gkd.program
