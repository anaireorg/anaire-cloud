#!/usr/bin/env python
import sys
import requests
from paho.mqtt import client as mqtt
import yaml

HEADERS = {'X-Requested-With': 'Python requests', 'Content-type': 'text/xml'}


def pushdata(DATA, URL):
  try:
    print(DATA)
    response = requests.post(url=URL, data=DATA,headers=HEADERS)
    print(response.content)
  except requests.exceptions.RequestException as e:  # This is the correct syntax
    raise SystemExit(e)

def on_connect(client, userdata, flags, rc):
    # connect mqtt broker
    client.subscribe([("measurement", 0)])
    
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    payload = yaml.safe_load(msg.payload.decode("utf-8"))
    device_id = payload.pop('id', None)
    co2 = payload.pop('CO2', None)
    temperature = payload.pop('temperature', None)
    humidity = payload.pop('humidity', None)
    msg = ""
    if co2: msg = msg+'CO2 '+str(co2)+'\n'
    if temperature: msg = msg+'Temperature '+str(temperature)+'\n'
    if humidity: msg = msg+'Humidity '+str(humidity)+'\n'
    URL  = 'http://'+sys.argv[1]+':30991/metrics/job/'+device_id
    pushdata(msg, URL)
    

def main():
  if (len(sys.argv) != 2):
      print 'Usage: '+sys.argv[0]+' <machine IP>'
      exit()
  
  client = mqtt.Client()
  client.connect(sys.argv[1], 30183)
  client.on_connect = on_connect
  client.on_message = on_message
  client.loop_forever()

if __name__ == "__main__":
    main()
