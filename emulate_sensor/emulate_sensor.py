#!/usr/bin/env python

from datetime import datetime
import random
import time

#general consts
accelerated = True
metrics_interval = 30   #How much to wait prior to send a new emulated measurement

#CO2 consts
minimum_CO2 = 450  #minimum C=2 concentration in the room
CO2_base_increment = random.randint(4,6)  #ppm of CO2 incremented in a minute
open_window_CO2_decrement = 9 #ppm of CO2 decremented in a minute when a window is opened

schedule = [
    [8*60 + 35, 9*60 + 25],
    [9*60 + 35, 10*60 + 25],
    [10*60 + 35, 11*60 + 25],
    [12*60 + 0, 12*60 + 50],
    [13*60 + 0, 13*60 + 50]
  ]
  
def main():
    CO2_increment = CO2_base_increment
    #If the class has the door open decrement the per minute CO2 increment
    if random.choice([True,False]): CO2_increment -= 1
     
    #Emulate if the window is opened 30%, 50%, 100% during class
    CO2_increment -=  open_window_CO2_decrement * int(random.choice([0.3, 0.5, 1]) )

    last_value = 0
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
            last_value = max(minimum_CO2, last_value + CO2_increment)
            print('clase:  ' + str(int(now/60))+':'+str(now%60)+'   '+str(CO2_increment))
        else:
            last_value = max(minimum_CO2, last_value - open_window_CO2_decrement)
            print('pausa:  ' + str(int(now/60))+':'+str(now%60)+'   '+str(-1 * open_window_CO2_decrement))
              
        new_value = last_value + random.randint(int(-1 * CO2_base_increment/2), int(CO2_base_increment/2))
        
        print('       '+str(new_value))

        if accelerated: time.sleep(1)     #If accelerated is set repeat iteration every second
        else: time.sleep(metrics_interval)

if __name__ == "__main__":
  main()

    