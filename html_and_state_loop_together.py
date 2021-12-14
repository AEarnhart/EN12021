import ssd1306
from microdot import Microdot, Response
from machine import I2C
from machine import Pin
import network
from umqttsimple import MQTTClient
from time import sleep
import _thread
import time
from max6675 import MAX6675
# from simpletemplate import render_template

# this sets up the OLED display
i2c = I2C(0, scl=Pin(18), sda=Pin(19))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# this sets up the thermocouple
test = MAX6675(cs=Pin(15), sck=Pin(2), so=Pin(4))

display.fill(0)
count = 0
start = 0
WAITING = 1
PREHEAT = 2
COOKING = 3
DONE = 4
state = WAITING
goaltemp = 22     # goal temperature to be reached to switch from preheating mode to cooking mode
goaltime = 60     # cook time in seconds
found_start_time = False
#startbutton = 1  # um, this can be a variable that monitors the "start cooking" on the website. Maybe?

red = Pin(22, Pin.OUT)    # indicates we're in heating mode
green = Pin(23, Pin.OUT)  # indicates we're in cooking mode

red.off()
green.off()

# Make sure we're connected to the network
wlan = network.WLAN(network.STA_IF)
if not wlan.isconnected():
    # If we're not connected, try to connect to Tufts_Wireless:
    wlan.active(True)
    ssid = "Tufts_Wireless"
    print("Connecting to {}...".format(ssid))
    wlan.connect(ssid)
    while not wlan.isconnected():
        print('.', end='')
        sleep(1)

# Print out our IP address so we know where to point the web browser!
ip_address = wlan.ifconfig()[0]
print("Site will be accessible at http://{}".format(ip_address))

# Set up our connection to the MQTT server
mqttclient = MQTTClient("esp32-sousvide", "en1-pi.eecs.tufts.edu")
mqttclient.connect()
SMARTPLUG_TOPIC = "ESPURNA-BF5BFD/relay/0/set"

# Set up the microdot server
app = Microdot()

# Waiting State
@app.route('/')
def index(request):
    return Response.send_file('waiting_state.html')

# CSS style file
@app.route('/style.css')
def style(request):
    return Response.send_file('style.css')

# Preheating State
@app.route('/preheat')
def preheat(request):
    global state
    state = PREHEAT
    
    # We can use request.args to read the values sent from the HTML form, e.g.,
    global goaltemp
    global goaltime
    goaltemp = request.args['cook_temp']
    goaltime = request.args['cook_time']

    # And then we can use that number (or anything else) as a template parameter
    # to customize what appears on the page.
    return Response.send_file('preheating_state.html')

# Cooking State
@app.route('/cook')
def cook(request):
    global state
    state = COOKING
    return Response.send_file('cooking_state.html')

# Data update for the preheating state
# Updates webpage live and goal temperature data
@app.route('/data_preheat')
def data(request):
    # Here we're just returning a Python dictionary, which gets automatically converted to JSON
    return {"temp":test.read(), "g_temp":goaltemp}

# Data update for the cooking state
# Updates webpage live and goal temperature data as well as the remaining cooking time
@app.route('/data_cooking')
def data(request):
    # Here we're just returning a Python dictionary, which gets automatically converted to JSON
    return {"temp":test.read(), "g_temp":goaltemp, "time":goaltime}

# Stop/Done state
@app.route('/stop')
def stop(request):
    global state
    state = DONE
    return Response.redirect('/')

_thread.start_new_thread(app.run, ('0.0.0.0', 80, True))

while True:
    
    if state == WAITING:
        red.off()
        green.off()
    
    elif state == PREHEAT:
        temp = test.read()
        
        red.on()
        mqttclient.publish(SMARTPLUG_TOPIC, '1') # this should turn on the smart plug
        current_time = time.time()
        temp = test.read()
        print("{},{},\n".format(current_time, temp))   #prints to computer for now...
        #add some code here to display "heating in progress" and the current temp on the website
        sleep(1)
            
            
    elif state == COOKING:
        if (not found_start_time):
            start = time.ticks_ms()     # this designates when the countdown should begin
            count = goaltime
            found_start_time = True
        
        green.on()             #indicates we've entered the cooking stage
        temp = test.read()
        
        current_time = time.time()
        temp = test.read()
        print("{},{},\n".format(current_time, temp))   #prints to computer for now...
        sleep(1)
        # add code to display timer and currenet temp on website
        
        timer = count - ((time.ticks_ms() - start) / 1000)  # variable designated as "timer" starts counting down, converting ms to seconds
        timer = int(timer)
        
        display.fill(0)
        display.text(str(timer), 52, 29)      # OLED displays the current timer value for now
        display.show()
        
        if temp < goaltemp:
            mqttclient.publish(SMARTPLUG_TOPIC, '1') # this should turn on the smart plug
            red.on()
        elif temp >= goaltemp:
            mqttclient.publish(SMARTPLUG_TOPIC, '0') # this should turn off the smart plug
            red.off()
            
        if timer <= 0:
            mqttclient.publish(SMARTPLUG_TOPIC, '0') # this should turn off the smart plug
            state = DONE
            #how do we want to tell the user it's done? Some kind of notification on the webpage?
            
    elif state == DONE:
        found_start_time = False
        red.off()
        green.off()
        mqttclient.publish(SMARTPLUG_TOPIC, '0') # this should turn off the smart plug
        display.fill(0)
        display.text(("DONE"), 52, 29)      # OLED displays the current timer value
        display.show()
        count = 0
