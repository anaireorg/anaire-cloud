#!/bin/bash
#execution example: ./launchDevices 54.229.227.193:32322../sample_project_configs/sample_config_5.yaml

PUSHGATEWAY_URL=$1
config_file=$2

cont=1
for device_uid in `egrep "uid\:" $config_file | awk '{print $3}'`
do
  helm install --name "device"$cont helm_template --set pusgatewayURL=$PUSHGATEWAY_URL --set device_uid=$device_uid --set windowPercentage=$((RANDOM%100)) --namespace generadores
  cont=$((cont+1))
done