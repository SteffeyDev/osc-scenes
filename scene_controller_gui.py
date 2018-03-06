import yaml
import sys
from threading import Timer, Thread
from pythonosc import osc_server, dispatcher, udp_client
import toga
from toga.style.pack import *
import asyncio

debug = False

config = yaml.load(open('scenes.yaml', 'r'))
scenes = config['scenes']
endpoints = config['endpoints']
mapping = config['map']

last_scene = None 
input_port = config['server']['listen_port']

value_types = {}

active_scene = None

class OSCMessage:
  def __init__(self, message, delay = 0):
    if debug:
      print("Creating OSCMessage from message:", message)

    self._prefix = message.split("/")[1]
    self._addr = message.split(" ")[0]
    self._delay = delay
    if value_types[self._prefix] == "float":
      self._arg = float(message.split(" ")[1])
    elif value_types[self._prefix] == "int":
      self._arg = int(message.split(" ")[1])
    else: # By default use int
      self._arg = int(message.split(" ")[1])
  
  @property
  def address(self):
    return self._addr
  
  @property
  def argument(self):
    return self._arg

  @property
  def delay(self):
    return self._delay

  @delay.setter
  def delay(self, delay):
    self._delay = delay

  @property
  def prefix(self):
    return self._prefix

print("\nInput Settings")
print("Listening on 0.0.0.0:" + str(input_port))
print("Listening for OSC commands in the form:")
print("\t/scene/<key>")
print("\t/midi-scene/<number>")

print("\nOutput Settings")
udp_clients = {}
for endpoint in endpoints:
  udp_clients[endpoint['prefix']] = udp_client.SimpleUDPClient(endpoint['ip'], endpoint['port'], allow_broadcast=True)
  value_types[endpoint['prefix']] = endpoint['valueType']
  print("Sending commands that start with /" + endpoint['prefix'] + " to " + endpoint['ip'] + ":" + str(endpoint['port']))


### Generate the OSC commands that need to be sent for each scene
# by parsing the YAML file

def is_osc_command(item):
  return isinstance(item, str) and item.startswith("/") and len(item.split("/")) > 2 and len(item.split(" ")) > 1

def get_commands(key, value, map_value, array):

  def print_error(key, value, map_value):
    print("Could not process item with key ", key, ", value:", value, ", and map value:", map_value)

  if debug:
    print("Getting commands for key:", key, "and value:", value, "\nUsing map_value:", map_value)

  if isinstance(value, dict):
    for _key, _value in value.items():
      get_commands(_key, _value, map_value[_key], array)

  elif isinstance(value, list):
    delay = 0
    for item in value:
      if 'delay' in item:
        delay = int(item.split(" ")[1].replace("s", ""))

    for map_key, map_val in map_value.items():
      if map_key in value and map_key != "none":
        if map_key in map_value and 'in' in map_value[map_key] and is_osc_command(map_value[map_key]['in']):
          array.append(OSCMessage(map_value[map_key]['in'], delay))
        else:
          print_error(key, value, map_value)
      else:
        if map_key in map_value and 'out' in map_value[map_key] and is_osc_command(map_value[map_key]['out']):
          array.append(OSCMessage(map_value[map_key]['out'], delay))
        else:
          print_error(key, value, map_value)

  elif isinstance(value, str):
    string = value.split(" ")[0]
    delay = 0
    if len(value.split(" ")) > 1:
      delay = int(value.split(" ")[1].replace("s", ""))

    if string in map_value and is_osc_command(map_value[string]):
      array.append(OSCMessage(map_value[string], delay))
    else:
      print_error(key, value, map_value)

  elif isinstance(value, int):
    array.append(OSCMessage(map_value.replace('x', str(value / 127))))

  else:
    print_error(key, value, map_value)
  

scene_map = {}
scene_names = {}
midi_map = {}
for scene in scenes:
  arr = []

  for key, value in scene.items():
    if not (key == "key" or key == "name" or key == "midi"):
      get_commands(key, value, mapping[key], arr)
  
  if debug:
    print("Array generated for scene " + scene['name'] + ":")
    print(arr)
    print()

  if 'midi' in scene:
    midi_map[scene['midi']] = scene['key']

  scene_map[scene['key']] = arr
  scene_names[scene['key']] = scene['name']

def send_msg(message):
  if message.delay == 0:
    udp_clients[message.prefix].send_message(message.address, message.argument)
    print("Sending message:", message.address, message.argument)

  else:
    wait = message.delay
    message.delay = 0
    r = Timer(wait, send_msg, [message])  
    r.start()

#def trigger_atem_transition():
# send_msg('/atem/transition/auto', 1)

def respond_to_scene(addr, args):
  global last_scene

  new_scene = ""
  if addr.split("/")[1] == "scene":
    new_scene = addr.split("/")[2]
  elif addr.split("/")[1] == "midi-scene":
    new_scene = midi_map[int(round(float(addr.split("/")[2]) * 127))]
  else:
    return

  # If we are recieving one of the turn off signals that
  # we are sending, ignore it (prevent feedback loop)
  if args == 0 or new_scene == last_scene:
    return

  print("\nGot Message: ", addr, " ", args)

  ### First we need to send message to turn on the new scene
  send_msg(OSCMessage("/scene/" + new_scene + " 1"))


  ### Then we need to send message to turn off current scene

  # If we know what the last scene is, deselect it
  if last_scene is not None:
    send_msg(OSCMessage("/scene/" + last_scene + " 0"))

  # If we don't know what the last scene is, turn them all off
  #   except for the current scene
  else:
    for key in scene_map:
      if key != new_scene:
        send_msg(OSCMessage("/scene/" + key +" 0"))
      
  last_scene = new_scene

  # Update GUI
  global active_scene
  active_scene = scene_names[new_scene]

  ### Finally we need to actual send the OSC messages that make up the scene change
  for osc_command in scene_map[new_scene]:
    send_msg(osc_command)

active_scene_label = None
  
def button_handler(widget):
  print("HI")

def build(app):
  box = toga.Box()

  button = toga.Button('Test', on_press=button_handler)
#box.add(button)

  active_info_panel = toga.Box(style=Pack(direction=COLUMN, padding=20))

  global active_scene_label
  active_scene_label = toga.Label('Current Scene: ')
  active_info_panel.add(active_scene_label)

  osc_server_label = toga.Label('OSC Server Details')
  listening_address_label = toga.Label("Listening on 0.0.0.0:" + str(input_port))
  listening_form_label = toga.Label("Listening for OSC commands in the form: /scene/<key>|<number>")
  active_info_panel.add(osc_server_label)
  active_info_panel.add(listening_address_label)
  active_info_panel.add(listening_form_label)

  log_data = ['hi', 'sup']

  log_table = toga.Table(headings=['Log'], data=log_data)

  split = toga.SplitContainer(direction=toga.SplitContainer.HORIZONTAL)
  split.content = [active_info_panel, log_table]

  box.add(split)

  return box

async def updateGUI():
  while(True):
    global active_scene_label
    global active_scene
    if (active_scene_label is not None and active_scene is not None):
      active_scene_label.text = "Current Scene: " + active_scene
      active_scene_label.refresh()
    await asyncio.sleep(1)

class MyApp(toga.App):
  def main_loop(self):
    asyncio.ensure_future(updateGUI())
    return super(MyApp, self).main_loop()

def main():
  dispatch = dispatcher.Dispatcher()
  for key in scene_map:
    dispatch.map("/scene/" + key, respond_to_scene)
  for number in midi_map:
    dispatch.map("/midi-scene/" + str(round(number / 127, 2)), respond_to_scene)

  try:
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", input_port), dispatch)
    server_thread = Thread(target=server.serve_forever)
    server_thread.start()
  except KeyboardInterrupt:
    print("Exiting...")
    sys.exit(0)

  return MyApp("OSC Scene Controller", "com.peters.osc-scenes", startup=build)

if __name__ == "__main__":
  main().main_loop()
