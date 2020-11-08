#!/usr/bin/env python

from datetime import datetime
import random
import time
import sys


if (len(sys.argv) != 2):
  print('Usage: '+sys.argv[0]+' <percentage 0-1 of opened window during class>')
  exit()

#general consts
accelerated = True
metrics_interval = 30   #How much to wait prior to send a new emulated measurement
#open_window_percentage_during_class= random.choice([0, 0.3, 0.5, 1])
open_window_percentage_during_class = float(sys.argv[1])

#CO2 consts
minimum_CO2 = 450  #minimum C=2 concentration in the room
CO2_base_increment = random.randint(4,6)  #ppm of CO2 incremented in a minute
open_window_CO2_decrement = 9 #ppm of CO2 decremented in a minute when a window is opened

#Temperature consts
minimum_temperature = 17.0
maximum_temperature = 22.0
temperature_base_increment = 0.07  #Celsius increment per minute during class
open_window_temp_decrement = 0.13 #Celsius decrement per minute when the window is opened

#Humidity consts
minimum_humidity = 50
maximum_humidity = 70
humidity_base_decrement = 0.1  #%humidity decremented per minute during class
open_window_humidity_increment = 0.13 #%humidity incremented per minute when the window is opened


schedule = [
    [8*60 + 35, 9*60 + 25],
    [9*60 + 35, 10*60 + 25],
    [10*60 + 35, 11*60 + 25],
    [12*60 + 0, 12*60 + 50],
    [13*60 + 0, 13*60 + 50]
  ]
  
def main():
    CO2_increment = CO2_base_increment
    temperature_increment = temperature_base_increment
    humidity_decrement = humidity_base_decrement
    
    #If the class has the door open decrement the per minute CO2 increment
    if random.choice([True,False]): CO2_increment -= 1
     
    #Emulate if the window is opened 30%, 50%, 100% during class
    CO2_increment -=  int(open_window_CO2_decrement * open_window_percentage_during_class )
    temperature_increment -= open_window_temp_decrement * open_window_percentage_during_class
    humidity_decrement += open_window_humidity_increment * open_window_percentage_during_class

    last_CO2_value = 0
    last_temperature_value = 0
    if accelerated: now = 8*60 + 30  #If accelerated is set emulate to start at 8:30AM
    while (True):
        if accelerated: now += 1    #If accelerated is set emulate increment a minute in each iteration
        else:
            #current time in minutes
            now = datetime.now()
            now_minutes = now.hour*60 + now.minute
        
        #Determine if there is class now
        class_time = False
        for slot in schedule:
            if slot[0] <= now <= slot[1]:
                class_time = True
                break
        
        if class_time:
            last_CO2_value = max(minimum_CO2, last_CO2_value + CO2_increment)
            last_temperature_value = min(max(minimum_temperature, last_temperature_value + temperature_increment), maximum_temperature)
            
            print('clase:  ' + str(int(now/60))+':'+str(now%60)+'   '+str(open_window_percentage_during_class*100)+'%    '+str(CO2_increment)+'   '+str(temperature_increment))
        else:
            last_CO2_value = max(minimum_CO2, last_CO2_value - open_window_CO2_decrement)
            last_temperature_value = min(max(minimum_temperature, last_temperature_value - open_window_temp_decrement), maximum_temperature)
            
            print('pausa:  ' + str(int(now/60))+':'+str(now%60)+'   '+str(open_window_percentage_during_class*100)+'%    '+str(-1 * open_window_CO2_decrement)+'   '+str(-1 * open_window_temp_decrement))
              
        new_CO2_value = last_CO2_value + random.randint(int(-1 * CO2_base_increment/2), int(CO2_base_increment/2))
        new_temp_value = last_temperature_value + 0.1 *random.randint(-1, 1)
        
        print('       '+str(new_CO2_value)+'ppm       '+"{:.2f}".format(new_temp_value)+'ºC')

        if accelerated: time.sleep(1)     #If accelerated is set repeat iteration every second
        else: time.sleep(metrics_interval)

if __name__ == "__main__":
  main()

    