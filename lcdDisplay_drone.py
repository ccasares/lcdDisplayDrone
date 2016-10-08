import pifacecad
import sys
import subprocess
import time
import requests
import json
import pprint
import os

INIT=0
WIFI=1
REVERSEPORTS=2
currentInfoDisplay=0
maxInfoDisplay=2
buttonWaitingForConfirmation=-1

BUTTON1=0
BUTTON2=1
BUTTON3=2
BUTTON4=3
BUTTON5=4
BUTTONMIDDLE=5
BUTTONLEFT=6
BUTTONRIGHT=7

GET_IP_CMD = "hostname --all-ip-addresses"
GET_WIFI_CMD = "iwconfig wlan0 | grep ESSID | awk -F\":\" '{print $2}' | awk -F'\"' '{print $2}'"
RESET_WIFI_CMD = "sudo ifdown wlan0;sleep 2;sudo ifup wlan0"
CHECK_INTERNET_CMD = "sudo ping -q -w 1 -c 1 8.8.8.8 > /dev/null 2>&1 && echo U || echo D"
CHECK_REVERSEPROXY_CMD = "ssh -i /home/pi/.ssh/anki_drone $reverseProxy \"netstat -ant | grep LISTEN | grep $PORT | wc -l\""
CHECK_NODEUP_CMD = "wget -q -O - http://$reverseProxy:$PORT/drone > /dev/null && echo OK || echo NOK"
RESET_AUTOSSH_CMD = "pkill autossh;/home/pi/bin/setupReverseSSHPorts.sh /home/pi/bin/redirects"
RESET_NODEJS_CMD = "forever stop drone;forever start --uid drone --append /home/pi/dronecontrol/server.js"
REBOOT_CMD = "sudo reboot"
POWEROFF_CMD = "sudo poweroff"

def displayInfoRotation(cad):
  global currentInfoDisplay
  if currentInfoDisplay == INIT:
    initDisplay(cad)
  elif currentInfoDisplay == WIFI:
    wifiDisplay(cad)
  elif currentInfoDisplay == REVERSEPORTS:
    reversePortsDisplay(cad)

def initDisplay(cad):
  cad.lcd.clear()
  cad.lcd.set_cursor(0, 0)
  cad.lcd.write("Pi Version:"+getPiVersion())
  cad.lcd.set_cursor(0, 1)
  cad.lcd.write(getPiName())

def wifiDisplay(cad):
  cad.lcd.clear()
  cad.lcd.set_cursor(0, 0)
  cad.lcd.write("Wifi: "+get_my_wifi())
  cad.lcd.set_cursor(0, 1)
  cad.lcd.write(get_my_ip())
  cad.lcd.set_cursor(15, 1)
  cad.lcd.write(check_internet())

def reversePortsDisplay(cad):
  cad.lcd.clear()
  cad.lcd.set_cursor(0, 0)
  cad.lcd.write("Checking")
  cad.lcd.set_cursor(0, 1)
  cad.lcd.write("Please, wait...")
  prx_status=check_reverse_proxy()
  node_status=check_nodejs()
  cad.lcd.clear()
  cad.lcd.set_cursor(0, 0)
  cad.lcd.write("PROXY STATUS:"+prx_status)
  cad.lcd.set_cursor(0, 1)
  cad.lcd.write("NODE STATUS: "+node_status)

def handleButton(button, screen, event):
  global buttonWaitingForConfirmation
#  print "Button %s at screen %s" % (button,screen)
  if screen == INIT:
    # 1: REBOOT
    # 2: POWEROFF
    # 5: CONFIRM
    if buttonWaitingForConfirmation != -1 and button == BUTTON5:
	  # Confirmation to previous command
	  if buttonWaitingForConfirmation == BUTTON1:
	    # REBOOT
	    CMD = REBOOT_CMD
	    msg = "REBOOTING"
	  else:
	    # POWEROFF
	    CMD = POWEROFF_CMD
	    msg = "HALTING SYSTEM"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  run_cmd(CMD)      
    if button == BUTTON1 or button == BUTTON2:
	  buttonWaitingForConfirmation = button
	  if button == BUTTON1:
	     msg = "REBOOT REQUEST"
	  else:
	     msg = "POWEROFF REQUEST"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  cad.lcd.set_cursor(0, 1)
	  cad.lcd.write("CONFIRM RIGHTBTN")
    else:
	  if buttonWaitingForConfirmation != -1:
	    displayInfoRotation(event.chip)
	    buttonWaitingForConfirmation = -1
  elif screen == WIFI:
    # 1: RESET WIFI
    # 5: CONFIRM
    if buttonWaitingForConfirmation != -1 and button == BUTTON5:
	  # Confirmation to previous command
	  buttonWaitingForConfirmation = -1
	  msg = "RESETING WIFI"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  run_cmd(RESET_WIFI_CMD)
	  displayInfoRotation(event.chip)
    if button == BUTTON1:
	  buttonWaitingForConfirmation = button
	  msg = "WIFI RST REQUEST"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  cad.lcd.set_cursor(0, 1)
	  cad.lcd.write("CONFIRM RIGHTBTN")
    else:
	  if buttonWaitingForConfirmation != -1:
	    displayInfoRotation(event.chip)
	    buttonWaitingForConfirmation = -1
  elif screen == REVERSEPORTS:
    # 1: RESTART AUTOSSH PROCESS
    # 2: RESTART NODEJS
    # 5: CONFIRM
    if buttonWaitingForConfirmation != -1 and button == BUTTON5:
	  # Confirmation to previous command
	  if buttonWaitingForConfirmation == BUTTON1:
	    # RESTART AUTOSSH PROCESS
	    CMD = RESET_AUTOSSH_CMD
	    msg = "RESTARTING SSH\nTUNNELING"
	  else:
	    # RESTART NODEJS
	    CMD = RESET_NODEJS_CMD
	    msg = "RESTARTING\nNODEJS"
	  buttonWaitingForConfirmation = -1
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  run_cmd(CMD)      
	  displayInfoRotation(event.chip)
    if button == BUTTON1:
	  buttonWaitingForConfirmation = button
	  msg = "AUTOSSH RST REQ"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  cad.lcd.set_cursor(0, 1)
	  cad.lcd.write("CONFIRM RIGHTBTN")
    elif button == BUTTON2:
	  buttonWaitingForConfirmation = button
	  msg = "NODEJS RESET REQ"
	  cad.lcd.clear()
	  cad.lcd.set_cursor(0, 0)
	  cad.lcd.write(msg)
	  cad.lcd.set_cursor(0, 1)
	  cad.lcd.write("CONFIRM RIGHTBTN")
    else:
	  if buttonWaitingForConfirmation != -1:
	    displayInfoRotation(event.chip)
	    buttonWaitingForConfirmation = -1
  else:
    print "UNKNOWN SCREEN: %s" % screen

def buttonPressed(event):
#  print "Event: "+str(event.pin_num)
  global currentInfoDisplay
  
  if event.pin_num == BUTTONLEFT:
    if currentInfoDisplay > 0:
      currentInfoDisplay=currentInfoDisplay-1
    else:
      currentInfoDisplay=maxInfoDisplay
    displayInfoRotation(event.chip)
    buttonWaitingForConfirmation = -1
  elif event.pin_num == BUTTONRIGHT:
    if currentInfoDisplay < maxInfoDisplay:
      currentInfoDisplay=currentInfoDisplay+1
    else:
      currentInfoDisplay=0
    displayInfoRotation(event.chip)
    buttonWaitingForConfirmation = -1
  elif event.pin_num == BUTTONMIDDLE:
    displayInfoRotation(event.chip)
    buttonWaitingForConfirmation = -1
  elif event.pin_num >= BUTTON1 and event.pin_num <= BUTTON5:
    handleButton(event.pin_num,currentInfoDisplay, event)
  else:
    event.chip.lcd.set_cursor(0, 14)
    event.chip.lcd.write(str(event.pin_num))
  
def run_cmd(cmd):
  msg = subprocess.check_output(cmd, shell=True).decode('utf-8')
  return msg

def get_my_wifi():
  return run_cmd(GET_WIFI_CMD)[:-1]

def get_my_ip():
  return run_cmd(GET_IP_CMD)[:-1]

def check_internet():
  return run_cmd(CHECK_INTERNET_CMD)

def check_reverse_proxy():
  listeners=int(run_cmd(CHECK_REVERSEPROXY_CMD))
  if listeners > 0:
     return "OK"
  else:
     return "NOK"

def check_nodejs():
   return run_cmd(CHECK_NODEUP_CMD)

def getPiName():
  with open('/home/pi/PiInfo.txt', 'r') as f:
    first_line = f.readline()
    PiName = first_line.split("=",1)[1]
    PiName = PiName[0:-1] # Strip trailing cr
    if PiName.startswith('"'):
      PiName = PiName[1:]
    if PiName.endswith('"'):
      PiName = PiName[0:-1]
    return(PiName)

def getPiVersion():
  with open('/home/pi/piImgVersion.txt', 'r') as f:
    first_line = f.readline()
    return(first_line)

cad = pifacecad.PiFaceCAD()
cad.lcd.backlight_on()
cad.lcd.blink_off()
cad.lcd.cursor_off()
initDisplay(cad)

listener = pifacecad.SwitchEventListener(chip=cad)
for i in range(8):
  listener.register(i, pifacecad.IODIR_FALLING_EDGE, buttonPressed)
listener.activate()
