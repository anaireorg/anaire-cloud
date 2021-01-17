#!/bin/bash
#remove all persistent data

echo "Esto borrará todos los datos almacenados. No es posible deshacer esta acción. Telclee 'borrar' para eliminar todos los datos del portal"
read confirmation
if [ "$confirmation" != "borrar" ]; then
        echo "Cancelado"
        exit
fi
echo "Eliminando stack helm"
microk8s.helm3 uninstall anairestack
echo "Borrando datos persistentes"
sudo rm -rf /data
for application in prometheus pushgateway grafana mosquitto letsencrypt
do
  if [ ! -d /data/$application ]; then
    sudo mkdir -p /data/$application
    sudo chown -R $USER:$USER /data/$application
    sudo chmod o+w /data/$application
  fi
done
