#!/bin/bash
apt update && apt install -y python python-requests
/config/emulate_sensor.py $@