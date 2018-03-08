# OSC Scene Controller

A lot of lighting, sound, and video control software supports the [OSC](http://opensoundcontrol.org/introduction-osc) protocol, so users can you tools like [TouchOSC](https://hexler.net/software/touchosc) or [OSCulator](https://osculator.net) to control a live production.  This scene controller listens for OSC input in the form `/scene/<scene-key>` and sends out a sequence of user-defined OSC commands to various endpoints so that lighting, sound, and video can be controlled with one command.  All configuration is through a YAML file that is provided by the user.

## Introduction

### What is YAML?
YAML is a human readable markdown language.  It serves the same purpose as XML and JSON, but is much easier to understand and use.  Check out [yaml.org](http://www.yaml.org) for more information.

### The OSC protocol
OSC messages contain 2 parts:
* Address: a string delimited by forward slashes ("/") specifying the resource to control
  - e.g. `/this/is/an/osc/address`
* Value: a float, integer, or string that is sent to the resource at the specified address
 - e.g. `3.6` or `5` or `This is a string value`

## Getting Started

1. Download the `OSCSceneController.app.zip` file from the [latest release](https://github.com/steffeydev/osc-scenes/releases/latest).
2. Create the YAML Configuration File by following the format described below
3. Double-click the `OSCSceneController.app` file to run it, and load in your configuration

## The YAML Configuration File
The scenes.yaml configuration file should contain the following sections:

### Server

This is where you configure the OSC Server.  Options include:
* `listen_port`:int - This if the port that the OSC Scene controller will listen on

### Endpoints

This is a list of the other applications you would like to send OSC commands to.  Options for each item include:
* `prefix`:string - What commands should be sent to this endpoint?
  - Most OSC commands start with a device indicator, such as `/dmxis/command/...`.  Setting the prefix as `dmxis` will cause all OSC commands that start with `/dmxis/` to be sent to this endpoint.
* `ip`:string - A valid IPv4 address of where to send the commands.
  - If the endpoint is running on the same computer as the scene controller, use `127.0.0.1`.
* `port`:int - The UDP port to send the OSC commands to
* `valueType`:string - A value (either `float` or `int`) that defines how numbers should be sent to this device
  - Optional - Default is `float`

### Map

This is where things get fun.  In this section, you define the OSC commands that sould be sent for a given value in a scene.  Each command should be an OSC address and value, separated by a single space.

For example, given the scene:
```yaml
name: First Scene
key: first
lights: blue
video: wide
```
you would need the following map to fully define the scene:
```yaml
lights:
  blue: /device/color/blue 1
  red: /device/color/red 1
  ...
video:
  wide: /video-device/camera/0 1
  center: /video-device/camera/1 1
  ...
```

In your actual `scenes.yaml`, you would replace these fake OSC commands with the actual commands you want to be sent when the corresponsing key is set in a scene.
By mapping the values, it makes it very easy to create a large number of scene layouts in plain text, and not have to worry about copying around obscure OSC commands to every scene.

This is a very basic example, for a more in-depth look into the types of maps available, see the *Advanced Mapping* section below

### Scenes

This is a list of scenes, each with the following options:
* `name`:string - The descriptive display name of the scene
* `key`:string - A lowercase, one-word string that represents how this scene will be called
  - If you want to call this using `/scenes/scene1`, then the `key` would be `scene1`
* The actual scene parameters, as defined in the map


## Sample `scenes.yaml` file
Here is what a basic `scenes.yaml` file should look like:

```yaml
server:
  listen_port: 8002

endpoints:
  -
    prefix: atem
    ip: 10.0.0.2
    port: 3456
    valueType: float
  -
    prefix: sc
    ip: 127.0.0.1
    port: 8001
    valueType: int

map:
  video:
    camera:
      wide: /atem/camera/7 1
      close: /atem/camera/2 1
    transition:
      cut: /atem/transition/cut 1
      auto: /atem/transition/auto 1
  lights:
    color:
      starting: /sc/btn/run/3/5/5 1
      ending: /sc/btn/run/3/6/5 1
    spotlights:
      overhead: 
        in: /sc/btn/2/2/4 1
        out: /sc/btn/2/2/4 0
      center:
        in: /sc/btn/2/3/4 1
        out: /sc/btn/2/3/4 0

scenes:
  -
    name: Welcome
    key: welcome
    video:
      camera: close
      transition: cut
    lights:
      color: starting
      spotlights:
        - center
        - overhead
  -
    name: Main
    key: main
    video:
      camera: wide
      transition: auto 1s
    lights:
      color: ending
      spotlights:
        - overhead
```

## Advanced Mapping

### Infinite levels
In the above example, the mapping only went 3/4 levels deep.  You can go as deep as needed, as long as the levels in your map match the levels in your scene

### List notation
In addition to the standard direct mapping, you can define OSC commands in lists.  If the command is in the list, the corresponding `in` command will be sent.  If the command is not in the list for a given scene, the `out` command will be sent.  For example, for the scene `main` above, because `overhead` is the only item in the `spotlights` list, the `/sc/btn/2/2/4 1` command will be run (corresponding to `overhead: in` and the `/sc/btn/2/2/4 0` command will be run as well (corresponding to `center:out`), because `center` was not in the list.  Note that for every scene, if the list is included, every value in the list will either have it's `in` or `out` command sent, depending on whether that item is in the list.

If a list is entirely ommited from a scene, no values will be sent for any of the items in that list's map.

If you want to send the `out` command for all values in the list, you can include `none` as the only value in the list.  In the above example, you could do the following:
```
    spotlights:
      - none
```

### Delayed sending
You can send delay the sending of a command for a whole number of seconds after the scene command is received.  In the example above, we wanted to delay sending of the video OSC command until 1 second after the lights, so we put `transition: auto 1s` in the scene.  The `auto` corresponded to the value in the map, and the `1s` instructed it to send with a 1 second delay.  You can also delay the sending of all the values in a list by including a `- delay 1s` item anywhere in the list.  This will cause all of the `on`/`off` commands to be delayed by that many seconds.

### Sending variable numbers
If you don't want to send a constant value every time a mapped command is used, you can use an `x`, and then specify the value in the scene.

For example, I can have the following map:
```yaml
map:
  cmd: /out/command x
...
scenes:
  name: Example
  key: example
  cmd: 57
...
```
When the `example` scene is called, `/out/command 57` will be sent to the endpoint with the `out` prefix.

## Contributing

### Setting up the environment

```sh
# Clone repository
git clone https://github.com/SteffeyDev/osc-scenes.git
cd osc-scenes

# Setup virtual environment
python3 -m pip install --user virtualenv
python3 -m virtualenv env
source env/bin/activate
pip3 install -r requironments.pip
```

### Developing

Modify the OSCSceneController.py file to fix issues or add new features
Test your changes by running `python3 OSCSceneController.py`

### Building New Executable

Run the included `build_app` script to generate the new `OSCSceneController.app` file:
```sh
./build_app
```

### Submitting Pull Request

Feel free to submit a pull request with your fix or feature!  I'll review it as soon as I can.
