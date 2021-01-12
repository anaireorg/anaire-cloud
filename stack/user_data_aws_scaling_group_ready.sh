#!/bin/bash
LOG_LOCATION=/home/ubuntu
exec > >(tee -i $LOG_LOCATION/userdata.txt)
exec 2>&1
sudo apt update && sudo apt install -y jq unzip git

#==========================VARIABLES=================================
#AWS variables
#-------------
# - AWS volume id used to provide persistence
export vol_id=vol-XXXXX
# - AWS elastict IP used to ensure new machines in the scaling group have always the same IP
export eip_id=eipalloc-XXXXXX

#Stack Variables
#---------------
# - Grafana NodePort
export GRAFANA_ADMIN_PASSWORD=yourpassword
export PUBLIC_IP=ipordns
#export SECONDARY_IP=useifneeded
export TLS=false
#===========================================================

#==============Attach devices to instance===================
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
sleep 5
#Get instance ID and attach to it the volume and the elastic IP
instance_id=$(curl http://169.254.169.254/latest/meta-data/instance-id)
echo "DEBUG:   instance_id: "$instance_id". Trying to attach volume"
aws ec2 attach-volume --volume-id $vol_id --instance-id $instance_id --device /dev/sdb
sleep 2
echo "DEBUG:   instance_id: "$instance_id". Trying to associate elastic IP"
aws ec2 associate-address --allocation-id $eip_id --instance-id $instance_id
sleep 2
#Mount /data partition for persistent storage
sudo bash -c 'echo "/dev/nvme1n1p1  /data  auto nosuid,nodev,nofail 0 0" >> /etc/fstab'
sudo mkdir -p /data
sudo mount -a
#===========================================================

#==============Initialize /data if needed===================
#Ensure there is a directory created for the applications persistent data
for application in prometheus pushgateway grafana mosquitto letsencrypt
do
  if [ ! -d /data/$application ]; then
    sudo mkdir -p /data/$application
    sudo chown -R ubuntu:ubuntu /data/$application
    sudo chmod o+w /data/$application
  fi
done
#===========================================================

#===============Install K8s and helm3=======================
#Create all in one kubernetes
sudo snap install microk8s --classic
sudo usermod -a -G microk8s ubuntu
sudo microk8s.enable dns
sudo microk8s.enable helm3
echo "alias sudo='sudo '" >> /home/ubuntu/.bashrc
echo "alias kubectl='microk8s.kubectl'" >> /home/ubuntu/.bashrc
echo "alias helm='microk8s.helm3'" >> /home/ubuntu/.bashrc
#===========================================================

#================Install anaire cloud stack=================
cd /home/ubuntu/
git clone https://github.com/anaireorg/anaire-cloud.git
#sudo microk8s.helm3 install  --set tls=$TLS --set secondaryPublicIP=$SECONDARY_IP --set publicIP=$PUBLIC_IP --set grafanaAdminPass=$GRAFANA_ADMIN_PASSWORD anairestack anaire-cloud/stack/anairecloud
sudo microk8s.helm3 install  --set tls=$TLS --set publicIP=$PUBLIC_IP --set grafanaAdminPass=$GRAFANA_ADMIN_PASSWORD anairestack anaire-cloud/stack/anairecloud
#===========================================================
