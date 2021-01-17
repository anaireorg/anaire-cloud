#!/bin/bash
LOG_LOCATION=$HOME
exec > >(tee -i $LOG_LOCATION/userdata.txt)
exec 2>&1
sudo apt update && sudo apt install -y jq unzip git snapd

#====================VARIABLES==============================
export PUBLIC_IP=$(hostname -I)
export GRAFANA_ADMIN_PASSWORD="your_password"
#===========================================================

#==============Initialize /data if needed===================
#Ensure there is a directory created for the applications persistent data
for application in prometheus pushgateway grafana mosquitto letsencrypt
do
  if [ ! -d /data/$application ]; then
    sudo mkdir -p /data/$application
    sudo chown -R $USER:$USER /data/$application
    sudo chmod o+w /data/$application
  fi
done
#===========================================================

#===============Install K8s and helm3=======================
#Create all in one kubernetes
sudo snap install microk8s --classic
sudo usermod -a -G microk8s $USER
sudo microk8s.enable dns
sudo microk8s.enable helm3
echo "alias sudo='sudo '" >> $HOME/.bashrc
echo "alias kubectl='microk8s.kubectl'" >> $HOME/.bashrc
echo "alias helm='microk8s.helm3'" >> $HOME/.bashrc
#===========================================================

#================Install anaire cloud stack=================
cd $HOME
git clone https://github.com/anaireorg/anaire-cloud.git
ln -s anaire-cloud/stack/virtualbox/delete_stack.sh
ln -s anaire-cloud/stack/virtualbox/upgrade_stack.sh
ln -s anaire-cloud/stack/virtualbox/start_stack.sh
sudo microk8s.helm3 install --set tls=false --set publicIP=$PUBLIC_IP --set grafanaAdminPass=$GRAFANA_ADMIN_PASSWORD anairestack anaire-cloud/stack/anairecloud
#===========================================================
