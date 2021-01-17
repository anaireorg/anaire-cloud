#/bin/bash

GRAFANA_PASS='yourpassword'
PUBLIC_IP=`ip a l enp0s3 | awk '($1=="inet"){split($2,a,"/");print a[1]}'`
if [ $# -ge 1 ]; then GRAFANA_PASS=$1;fi
if [ $# -eq 2 ]; then PUBLIC_IP=$2;fi
pushd ~/anaire-cloud/
git pull
popd
microk8s.helm3 list | grep anairestack && microk8s.helm3 uninstall anairestack
microk8s.helm3 install --set tls=false --set publicIP=$PUBLIC_IP --set grafanaAdminPass=$GRAFANA_PASS anairestack anaire-cloud/stack/anairecloud
