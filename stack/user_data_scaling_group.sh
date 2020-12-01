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

#Stack Variables
#---------------
# - Grafana NodePort
export PUBLIC_IP=$(aws ec2 describe-addresses --allocation-ids $eip_id --query 'Addresses[0].PublicIp'|tr -d '"')
export GRAFANA_NODEPORT_PORT=30300
export GRAFANA_ADMIN_PASSWORD="your_password"
#===========================================================


#==============Attach devices to instance===================
#Get instance ID and attach to it the volume and the elastic IP
instance_id=$(curl http://169.254.169.254/latest/meta-data/instance-id)
echo "DEBUG:   instance_id: "$instance_id". Trying to attach volume"
aws ec2 attach-volume --volume-id $vol_id --instance-id $instance_id --device /dev/sdb
sleep 2
echo "DEBUG:   instance_id: "$instance_id". Trying to associate elastic IP"
aws ec2 associate-address --allocation-id $eip_id --instance-id $instance_id
sleep 2
#Mount /data partition for persistent storage
sudo mount -a
#Ensure there is a directory created for the applications persistent data
for application in prometheus pushgateway grafana mosquitto
do
  if [ ! -d /data/$application ]; then 
    sudo mkdir /data/$application
    sudo chown -R ubuntu:ubuntu /data/$application
    sudo chmod o+w /data/$application
  fi
done
#===========================================================

#================Install K8s================================
#Create all in one kubernetes
sudo systemctl start docker
sudo hostnamectl set-hostname master-node
sudo swapoff -a
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p /home/ubuntu/.kube
sudo cp /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
sudo chown ubuntu:ubuntu /home/ubuntu/.kube/config
kubectl --kubeconfig /home/ubuntu/.kube/config taint node master-node node-role.kubernetes.io/master:NoSchedule-
kubectl --kubeconfig /home/ubuntu/.kube/config apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
#===========================================================

#================Install anaire cloud stack=================
for manifest in mqtt_broker mqttforward pushgateway prometheus grafana grafana-image-renderer; do
  wget -P /home/ubuntu https://raw.githubusercontent.com/anaireorg/anaire-cloud/main/stack/${manifest}.yaml
done

#Lauch pushgateway
kubectl --kubeconfig /home/ubuntu/.kube/config apply -f /home/ubuntu/pushgateway.yaml
sleep 2

#wait until pushgwateway cip is available
export PUSHGATEWAY_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc pushgateway-np -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}')
while [ -z $PUSHGATEWAY_CIP ]; do export PUSHGATEWAY_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc pushgateway-np -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}'); sleep 1; done

#launch prometheus including $PUSHGATEWAY_CIP as target
( echo "cat <<EOF" ; cat /home/ubuntu/prometheus.yaml ; echo EOF ) | sh | kubectl --kubeconfig /home/ubuntu/.kube/config apply -f -
sleep 2

#Launch grafana image renderer
kubectl --kubeconfig /home/ubuntu/.kube/config apply -f /home/ubuntu/grafana-image-renderer.yaml
sleep 2

#wait until prometheus cip is available
export PROMETHEUS_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc prometheus-cip -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}')
while [ -z $PROMETHEUS_CIP ]; do export PROMETHEUS_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc prometheus-cip -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}'); sleep 1; done

#wait until grafana-image-renderer cip is available
export RENDERER_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc grafana-image-renderer-cip -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}')
while [ -z $RENDERER_CIP ]; do export RENDERER_CIP=$(kubectl --kubeconfig /home/ubuntu/.kube/config get svc grafana-image-renderer-cip -o jsonpath='{.spec.clusterIP}{":"}{.spec.ports[0].targetPort}'); sleep 1; done

#launch grafana including $PROMETHEUS_CIP as target, setting GF_SERVER_ROOT_URL, GF_SECURITY_ADMIN_PASSWORD and the rendering variables
( echo "cat <<EOF" ; cat /home/ubuntu/grafana.yaml ; echo EOF ) | sh | kubectl --kubeconfig /home/ubuntu/.kube/config apply -f -
sleep 2

#Lauch MQTT broker
kubectl --kubeconfig /home/ubuntu/.kube/config apply -f /home/ubuntu/mqtt_broker.yaml
sleep 2

#Lauch MQTT forwarder to pushgateway
kubectl --kubeconfig /home/ubuntu/.kube/config apply -f /home/ubuntu/mqttforward.yaml
sleep 2
#===========================================================

#==============Watchdog to ensure K8s works=================
cat << EOF >> /home/ubuntu/watchdog.service
[Unit]
After=network.service

[Service]
ExecStart=/home/ubuntu/watchdog.sh

[Install]
WantedBy=default.target
EOF

cat << EOF >> /home/ubuntu/watchdog.sh
#!/bin/bash

while ((1))
do
  sleep 600
  kubectl get pods --kubeconfig /home/ubuntu/.kube/config || sudo reboot
done
EOF

sudo chmod 664 /home/ubuntu/watchdog.service
sudo chmod 744 /home/ubuntu/watchdog.sh
sudo mv /home/ubuntu/watchdog.service  /etc/systemd/system/watchdog.service
sudo systemctl daemon-reload
sudo systemctl enable watchdog.service
sudo systemctl start watchdog.service
#===========================================================
