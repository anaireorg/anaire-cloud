#!/bin/bash
LOG_LOCATION=/home/ubuntu
exec > >(tee -i $LOG_LOCATION/userdata.txt)
exec 2>&1

#==========================VARIABLES=================================
#AWS variables
#-------------
# - AWS credentials
export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
export AWS_DEFAULT_REGION="your_default_region"
# - AWS volume id used to provide persistence
export vol_id=vol-XXXXX
# - AWS elastict IP used to ensure new machines in the scaling group have always the same IP
export eip_id=eipalloc-XXXXXX
#===========================================================

curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add
sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"
sudo apt update
sudo apt-get install -y kubeadm kubelet kubectl docker.io software-properties-common parted bash-completion unzip vim
sudo apt-mark hold kubeadm kubelet kubectl 
sudo systemctl start docker
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
sleep 5
instance_id=$(curl http://169.254.169.254/latest/meta-data/instance-id)
echo "DEBUG:   instance_id: "$instance_id". Trying to attach volume"
aws ec2 attach-volume --volume-id $vol_id --instance-id $instance_id --device /dev/sdb
sleep 5
echo "DEBUG:   instance_id: "$instance_id". Trying to associate elastic IP"
aws ec2 associate-address --allocation-id $eip_id --instance-id $instance_id
sudo bash -c 'echo "/dev/nvme1n1p1  /data  auto nosuid,nodev,nofail 0 0" >> /etc/fstab'
sudo mkdir -p /data
sudo parted /dev/nvme1n1 mklabel msdos
sudo parted -a optimal /dev/nvme1n1 mkpart primary 0% 100%
sudo mkfs.ext4 /dev/nvme1n1p1
sudo mount -a

for application in prometheus pushgateway grafana mosquitto
do
  if [ ! -d /data/$application ]; then 
    sudo mkdir /data/$application
    sudo chown -R ubuntu:ubuntu /data/$application
    sudo chmod o+w /data/$application
  fi
done

