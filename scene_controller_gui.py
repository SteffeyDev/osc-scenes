import yaml
import sys
from threading import Timer, Thread
from pythonosc import osc_server, dispatcher, udp_client
import asyncio
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import font
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

debug = False

active_scene = None
log_data = []
value_types = {}

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



### Generate the OSC commands that need to be sent for each scene
# by parsing the YAML file

class SceneParser():
  def __init__(self):
    self.scene_map = None
    self.midi_map = None
    self.scene_names = None

  def parseFromFile(self, filename):
    config = yaml.load(open(filename, 'r'))
    scenes = config['scenes']
    endpoints = config['endpoints']
    mapping = config['map']

    self.scene_map = {}
    self.scene_names = {}
    self.midi_map = {}
    self.udp_clients = {}

    print("\nOutput Settings")
    udp_clients = {}
    for endpoint in endpoints:
      self.udp_clients[endpoint['prefix']] = udp_client.SimpleUDPClient(endpoint['ip'], endpoint['port'], allow_broadcast=True)
      value_types[endpoint['prefix']] = endpoint['valueType']
      print("Sending commands that start with /" + endpoint['prefix'] + " to " + endpoint['ip'] + ":" + str(endpoint['port']))

    for scene in scenes:
      arr = []

      for key, value in scene.items():
        if not (key == "key" or key == "name" or key == "midi"):
          self.get_commands(key, value, mapping[key], arr)
      
      if debug:
        print("Array generated for scene " + scene['name'] + ":")
        print(arr)
        print()

      if 'midi' in scene:
        self.midi_map[scene['midi']] = scene['key']

      self.scene_map[scene['key']] = arr
      self.scene_names[scene['key']] = scene['name']


  def is_osc_command(self, item):
    return isinstance(item, str) and item.startswith("/") and len(item.split("/")) > 2 and len(item.split(" ")) > 1

  def get_commands(self, key, value, map_value, array):

    def print_error(key, value, map_value):
      print("Could not process item with key ", key, ", value:", value, ", and map value:", map_value)

    if debug:
      print("Getting commands for key:", key, "and value:", value, "\nUsing map_value:", map_value)

    if isinstance(value, dict):
      for _key, _value in value.items():
        self.get_commands(_key, _value, map_value[_key], array)

    elif isinstance(value, list):
      delay = 0
      for item in value:
        if 'delay' in item:
          delay = int(item.split(" ")[1].replace("s", ""))

      for map_key, map_val in map_value.items():
        if map_key in value and map_key != "none":
          if map_key in map_value and 'in' in map_value[map_key] and self.is_osc_command(map_value[map_key]['in']):
            array.append(OSCMessage(map_value[map_key]['in'], delay))
          else:
            print_error(key, value, map_value)
        else:
          if map_key in map_value and 'out' in map_value[map_key] and self.is_osc_command(map_value[map_key]['out']):
            array.append(OSCMessage(map_value[map_key]['out'], delay))
          else:
            print_error(key, value, map_value)

    elif isinstance(value, str):
      string = value.split(" ")[0]
      delay = 0
      if len(value.split(" ")) > 1:
        delay = int(value.split(" ")[1].replace("s", ""))

      if string in map_value and self.is_osc_command(map_value[string]):
        array.append(OSCMessage(map_value[string], delay))
      else:
        print_error(key, value, map_value)

    elif isinstance(value, int):
      array.append(OSCMessage(map_value.replace('x', str(value / 127))))

    else:
      print_error(key, value, map_value)
    
  def getSceneMap(self):
    return self.scene_map

  def getSceneNames(self):
    return self.scene_names

  def getMidiMap(self):
    return self.midi_map

  def getUdpClients(self):
    return self.udp_clients


#def trigger_atem_transition():
# send_msg('/atem/transition/auto', 1)

class OSCSceneController():
  def __init__(self, parser):
    self.parser = parser
    self.dispatch = dispatcher.Dispatcher()
    for key in parser.getSceneMap():
      self.dispatch.map("/scene/" + key, self.respond_to_scene)
    for number in parser.getMidiMap():
      self.dispatch.map("/midi-scene/" + str(round(number / 127, 2)), self.respond_to_scene)

    self.server_thread = None
    self.server = None

    self.last_scene = None


  def start(self, input_port):
    try:
      self.server = osc_server.BlockingOSCUDPServer(("0.0.0.0", input_port), self.dispatch)
      self.server_thread = Thread(target=self.server.serve_forever)
      self.server_thread.start()

    except KeyboardInterrupt:
      print("Exiting...")
      sys.exit(0)


  def stop(self):
    if (self.server_thread is not None and self.server is not None):
      self.server.shutdown()
      self.server_thread.join()
      self.server = None
      self.server_thread = None


  def respond_to_scene(self, addr, args = 1):
    scene_map = self.parser.getSceneMap()
    midi_map = self.parser.getMidiMap()
    scene_names = self.parser.getSceneNames()
    new_scene = ""

    if addr.split("/")[1] == "scene":
      new_scene = addr.split("/")[2]
    elif addr.split("/")[1] == "midi-scene":
      new_scene = midi_map[int(round(float(addr.split("/")[2]) * 127))]
    else:
      return

    if new_scene not in scene_map:
      log_data.append("\nReceived undefined scene '{0}'".format(new_scene))
      return

    # If we are recieving one of the turn off signals that
    # we are sending, ignore it (prevent feedback loop)
    if args == 0 or new_scene == self.last_scene:
      return

    print("\nGot Message: ", addr, " ", args)
    log_data.append("")
    log_data.append("Received: " + addr + " " + str(args))

    ### First we need to send message to turn on the new scene
    self.send_msg(OSCMessage("/scene/" + new_scene + " 1"))


    ### Then we need to send message to turn off current scene

    # If we know what the last scene is, deselect it
    if self.last_scene is not None:
      self.send_msg(OSCMessage("/scene/" + self.last_scene + " 0"))

    # If we don't know what the last scene is, turn them all off
    #   except for the current scene
    else:
      for key in scene_map:
        if key != new_scene:
          self.send_msg(OSCMessage("/scene/" + key +" 0"))
        
    self.last_scene = new_scene

    # Update GUI
    global active_scene
    active_scene = scene_names[new_scene]

    ### Finally we need to actual send the OSC messages that make up the scene change
    for osc_command in scene_map[new_scene]:
      self.send_msg(osc_command)


  def send_msg(self, message):
    if message.delay == 0:
      self.parser.getUdpClients()[message.prefix].send_message(message.address, message.argument)
      print("Sending message:", message.address, message.argument)
      log_data.append("Sending: " + message.address + " " + str(message.argument))

    else:
      wait = message.delay
      message.delay = 0
      r = Timer(wait, self.send_msg, [message])  
      r.start()



class MyApp():
  def __init__(self, name, app_id, icon=None):
    self.filename = 'scenes.yaml'
    self.parser = SceneParser()
    self.parser.parseFromFile(self.filename)
    self.controller = OSCSceneController(self.parser)
    self.log_data_len = None

    self.root = tk.Tk()
    self.root.title(name)
    self.root.minsize(450, 350)
    self.root.configure(bg="#000000")

  def updateGUI(self):

    global active_scene
    if (active_scene is not None):
      self.active_scene_text.set(active_scene)

    global log_data
    log_data_store = log_data
    log_data = []
    self.log_text_box.configure(state='normal')
    for item in log_data_store:
      self.log_text_box.insert('end', item + '\n')
      self.log_text_box.yview('end')
    self.log_text_box.configure(state='disabled')

    self.root.after(1000, self.updateGUI)
    
  def main_loop(self):
    self.controller.start(input_port=8002)
    self.updateGUI()
    self.root.mainloop()

  def reload_scene_handler(self):
    self.parser.parseFromFile(self.filename)
    self.log("Reloaded configuration from file: {0}".format(self.filename))

  def load_from_file_handler(self):
    new_filename = filedialog.askopenfilename()
    if new_filename.split(".")[-1] != "yaml":
      messagebox.showerror("Invalid File", "Please select a YAML file with the extension .yaml")
    else:
      self.filename = new_filename
      self.parser.parseFromFile(new_filename)
      self.scene_file_text.set(new_filename.split("/")[-1])
      self.log("Successfully loaded new configuration from file: {0}".format(new_filename))

  def isPort(self, value_if_allowed, text, action, widgetName):
    if value_if_allowed == "":
      return True
    if text in '0123456789':
      try:
        return (int(value_if_allowed) < 65536)
      except ValueError:
        return False
    else:
      return False

  def log(self, text):
    self.log_text_box.configure(state='normal')
    self.log_text_box.insert('end', '\n' + text + '\n')
    self.log_text_box.configure(state='disabled')

  def input_port_changed(self, text):
    try:
      self.controller.stop()
      self.controller.start(int(self.input_port_text.get()))
      self.root.focus()
      self.log("Input port changed, now listening on port {0}".format(self.input_port_text.get()))
    except PermissionError:
      messagebox.showerror("Invalid Port", "It looks like that port is already in use or is reserved, try another one!")

  def generateLine(self, rootComponent, width):
    canvas = tk.Canvas(rootComponent, width=width, height=3)
    canvas.create_line(0, 4, width, 4, fill="gray")
    canvas.pack()

  def build(self):
    print(ttk.Style().theme_use())
    ttk.Style().theme_use('alt')

    style=ttk.Style()
    style.configure("TLabel", background="white")
    style.configure("Left.TFrame", background="white")
    style.configure("Right.TFrame", background="white")
    style.configure("TButton", relief="flat", background="lightgray")
    style.map("TButton",
      background=[('pressed', 'lightgray'), ('active', 'gray')],
      relief=[('pressed', 'flat'), ('active', 'flat')]
    )

    largeBoldFont = font.Font(size=25, weight='bold')
    mediumBoldFont = font.Font(size=18, weight='bold')
    smallBoldFont = font.Font(size=13, weight='bold')

    isPortCommand = (self.root.register(self.isPort), '%P', '%S', '%V', '%W')

    split = ttk.Frame(self.root)

    left_side = ttk.Frame(split, width=250, height=400, borderwidth=5, style="Left.TFrame")

    active_scene_box = tk.Frame(left_side, bg="white") #ttk.Frame(left_side, style="Left.TFrame")
    self.active_scene_text = tk.StringVar()
    self.active_scene_text.set("None")
    ttk.Label(active_scene_box, textvariable=self.active_scene_text, font=largeBoldFont).pack()
    self.generateLine(active_scene_box, 100)
    ttk.Label(active_scene_box, text="Current Scene").pack()
    active_scene_box.pack(pady=10)
    active_scene_box.config()

    input_box = ttk.Frame(left_side, style="Left.TFrame")
    self.input_port_text = tk.StringVar()
    listening_address_entry = ttk.Entry(input_box, width=5,textvariable=self.input_port_text, font=largeBoldFont, justify="center", validate="key", validatecommand=isPortCommand)
    listening_address_entry.bind('<Return>', self.input_port_changed)
    listening_address_entry.pack()
    self.input_port_text.set("8002")
    self.generateLine(input_box, 100)
    ttk.Label(input_box, text="Listening Port").pack()
    input_box.pack(pady=15)

    scene_box = ttk.Frame(left_side, style="Left.TFrame")
    self.scene_file_text = tk.StringVar()
    self.scene_file_text.set(self.filename)
    ttk.Label(scene_box, wraplength=210, font=mediumBoldFont, textvariable=self.scene_file_text).pack()
    self.generateLine(scene_box, 140)
    ttk.Label(scene_box, text="Loaded Configuration").pack()
    scene_button_box = ttk.Frame(scene_box, style="Left.TFrame")
    ttk.Button(scene_button_box, text='Reload Scene', command=lambda: self.reload_scene_handler()).pack(side='left', padx=2)
    ttk.Button(scene_button_box, text='Load from File', command=lambda: self.load_from_file_handler()).pack(side='right', padx=2)
    scene_button_box.pack(pady=10)
    scene_box.pack(pady=15)
    
    right_side = ttk.Frame(split, style="Right.TFrame")
    self.log_text_box = ScrolledText(right_side, bg='lightgray', highlightthickness=10, highlightbackground='lightgray', wrap='word')
    self.log_text_box.pack(side="left", expand=1, fill="both", padx=(5,0))
    self.log_text_box.insert('insert', """
Welcome to the OSC Scene Controller!
        
Send OSC messages in the form: /scene/<key> or /midi-scene/<number> to trigger a scene change.

When I receive a scene message, I’ll automatically send out “/scene/<last_key> 0”, where <last_key> is the key of the previous current scene.  If you want to receive this, set the Outgoing Reply IP address and port.

Listening on all interfaces on port {0}...
""".format(self.input_port_text.get()))
    self.log_text_box.configure(state='disabled')
    
    left_side.pack(side="left", fill="y")
    right_side.pack(side="right", fill="both", expand=1)

    split.grid(column=0, row=0, sticky='news')
    self.root.grid_columnconfigure(0, weight=1)
    self.root.grid_rowconfigure(0, weight=1)

if __name__ == "__main__":
  app = MyApp("OSC Scene Controller", "com.peters.osc-scenes")
  app.build()
  app.main_loop()
