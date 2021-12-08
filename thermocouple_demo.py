import time
from time import sleep
from machine import Pin
from max6675 import MAX6675

test = MAX6675(cs=Pin(15), sck=Pin(2), so=Pin(4))

for i in range(10):
   current_time = time.time()
   test_temp = test.read()
   print("{},{},\n".format(current_time, test_temp))
   sleep(1)
   
