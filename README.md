# OSC Scene Controller

A lot of lighting, sound, and video control software supports the [OSC](http://opensoundcontrol.org/introduction-osc) protocol, so users can you tools like [TouchOSC](https://hexler.net/software/touchosc) or [OSCulator](https://osculator.net) to control a live production.  This scene controller listens for OSC input in the form `/scene/<scene-key>` and sends out a sequence of user-defined OSC commands to various endpoints so that lighting, sound, and video can be controlled with one command.  All configuration is through a YAML file that is provided by the user.

## Introduction

### Features
* Powerful OSC automation using stateful scenes
* Lightweight OSC message routing

### What is YAML?
YAML is a human readable markdown language.  It serves the same purpose as XML and JSON, but is much easier to understand and use.  Check out [yaml.org](http://www.yaml.org) for more information.

### The OSC protocol
OSC messages contain 2 parts:
* Address: a string delimited by forward slashes ("/") specifying the resource to control
  - e.g. `/this/is/an/osc/address`
* Value: a float, integer, string, or boolean, that is sent to the resource at the specified address
 - e.g. `3.6` or `5` or `"This is a string value"` or `true`
 - multiple values can be sent in each message, and each value should be separated by a space.


## Download

### MacOS

1. Download the `OSCSceneController-Version.app.zip` file from the [latest release](https://github.com/steffeydev/osc-scenes/releases/latest) that matches your MacOS Version.
2. Create the YAML Configuration File by following the format described below.
3. Double-click the `OSCSceneController.app` file to run it.

### Windows

1. Download the `OSCSceneController.exe` file from the [latest release](https://github.com/steffeydev/osc-scenes/releases/latest).
2. Create the YAML Configuration File by following the format described below.
3. Double-click the `OSCSceneController.exe` file to run it.

### Linux

1. Download the `OSCSceneController.elf` file from the [latest release](https://github.com/steffeydev/osc-scenes/releases/latest).
2. Create the YAML Configuration File by following the format described below.
3. From the command line, `cd` into the folder with the executable and run `./OSCSceneController.elf`.

Note: The executable was built for debian-based 64-bit systems.  If it doesn't work on your system, follow the Contributing guide below to setup the environment and build it manually.

## Tutorial

### Basic OSC Router - Getting started with the YAML configuration file

So, you want to send all your packets to one location and have them be routed to the appropriate endpoints? Here's a basic configuration file that should work.

```
endpoints:
  -
    prefix: atem
    ip: 10.0.0.2
    port: 3456
  -
    prefix: dmxis
    ip: 127.0.0.1
    port: 8001
```

Go ahead and open up your favorite text editor (if you don't have one, Notepad will work on Windows, TextEdit on MacOS, and gEdit on Gnome), then copy and paste this in.  You'll need to change up the values to whatever your configuration is.  For example, if you have an app that listens for OSC messages in the form `/train/start <int_value>` on port `3849` on a computer with the IP address of `192.168.15.254`, then you would change one of the endpoints to be:

```
    prefix: train
    ip: 192.168.15.254
    port: 3849
```

Save that file as `router.yml`.  Open up the OSC Scene Controller, load in `router.yml`, and start sending messages to port `8002` (or whatever input port you set).  You'll see in the log on the right side when it recieves a message and where it forwards that message to.

So, pretty basic, right? Just create a list of endpoints and specify the prefix and routing details for each.  You can add as many enpoints as you want, each separated by that line containing nothing but a `-`.  And unfortunately yes, the indentation is important, so try to keep the format consistent.

In case you haven't figured it out by now, the prefix is the first part of the address after the inital `/`. For example, if the address is `/train/start 1`, then the prefix is just `train`.  Most OSC endpoints have a dedicated prefix, so you should be able to use this schema to route to most endpoints.  What is an endpoint?  An endpoint is any application or service capable of processing incoming OSC messages and taking some action on that message.

If you don't know, the `127.0.0.1` address is called your `localhost` address; use that if the OSC endpoint is on the same computer that you are running the scene controller on.

### Creating and Triggering Scenes

Ok, so now that you have routing down, let's have some fun! Open up that text editor again and paste this in to a new file:

```
endpoints:
  -
    prefix: foo
    ip: 192.168.15.254
    port: 3849
  -
    prefix: music
    ip: 192.168.15.23
    port: 8005
```

Continuing with our previous example, let's say that our endpoint is connected to your working model train and takes commands `/foo/bar <int>` that starts the train at the given speed.  You also have a cool speaker that can play music when it recieves an OSC command, and it listens for commands `/music/play <string>` and then plays the song you pass in.  Of course, you want a quick and easy way to start up your train and also play music to match, so let's create a scene! Add this right after the endpoints section:

```
scenes:
  -
    name: Slow & Steady
    key: start_slow
    train:
      start: slow
    music:
      mood: somber
  -
    name: Ramping It Up
    key: start_normal
    train:
      start: normal
    music:
      mood: happy
  -
    name: Goin' Crazy
    key: start_fast
    train:
      start: fast
    music:
      mood: excited
```

Now, if you send the command `/scene/start_slow` to the scene controller, it will trigger that scene, starting the train slowly and playing somber music.  But wait!  How does it know what OSC messages to send to make the train go a certain speed?  I forgot to tell you about maps, so check this out:

```
map:
  train:
    start:
      slow: /train/start 2
      normal: /train/start 5
      fast: /train/start 10
  music:
    mood:
      somber: /music/play "<insert name of somber song here>"
      happy: /music/play "<insert name of happy song here>"
      excited: /music/play "<insert name of excited song here>"
```

The map, well, maps the values used in scenes to actual OSC messages to send.  This means that your scenes can use very meaningful names and be read and created easily, while you keep the cluttered OSC messages in one section.  This has the added benifit of adding a layer of abstraction, so that if the OSC API changed for an endpoint, you only have to update the message in one place.  For example, if your speaker got an update and now you have to send `/music/play_song` instead of `/music/play`, you can just change the command in the map to be `somber: /music/play_song ...` and not have to worry about messing up the scenes.

You can put this section anywhere you want in your file, I like to put it between the `endpoints` and `scenes` sections.

Now, just save the file as `first_scenes.yml` and load it up! Unless you have a model train and OSC-equipped speaker, this won't actually do anything, but you can still send `/scene/start_slow` and watch what OSC messages are sent out in the log panel.

### More Advanced Scenes

Alright, so now that you have the basics down, let's improve our setup.  Our train can do more than just start; it can stop with `/train/stop` and blow it's whistle with `/train/whistle`.  We want to make a scene that will stop the music and blow the train's whistle.  Here's our new scene and map:

```
map:
  train:
    start:
      ...
    stop: /train/stop
    make_sound: /train/whistle
  music:
    mood:
      ...
    action:
      pause: /music/pause

scenes:
  ...
  -
    name: Blow Whistle
    key: choo_choo
    train: stop 2s
    music:
      action: pause
```

Ok, so a few new things here.  You can pass a time after the name in the scenes map to cause a `delay`.  Now, when you send the `/scene/choo_choo` message, this will immediately pause the music and then schedule the `/train/whistle` message to be sent 2 seconds later.  Hopefully, the music will stop in time for the whistle to actually be heard. (The `...` in the above example just means that I am omitting the parts I discussed previsouly, but in the actual file you still need those parts).

You may have also noticed that this time, the `stop` in the scene was immediately after the `train:`, instead of inside another option like `start`.  In truth, the level of mapping is completely arbituary, and you can set it up to suit your needs.  The following map and scene is completely valid:

```
map:
  this:
    is:
      a:
        really:
          long:
            path: /train/stop

scenes:
  -
    name: Stop Train
    key: train_stop
    this:
      is:
        a:
          really:
            long: path
```

Now that that's out of the way, let me introduce you to another cool feature: lists!  Let's say that you just upgraded your music player, and now have 8 speakers positioned around the house for playing the music in various rooms.  We can use lists to turn certain speakers on and off to match a given scene.

```
map:
  music:
    ...
    speakers:
      living_room:
        in: /music/speakers/living_room 1
        out: /music/speakers/living_room 0
      dining_room:
        in: /music/speakers/dining_room 1
        out: /music/speakers/dining_room 0
      kitchen:
        in: /music/speakers/kitchen 1
        out: /music/speakers/kitchen 0
      bedroom:
        in: /music/speakers/bedroom 1
        out: /music/speakers/bedroom 0

scenes:
  -
    name: Play on all
    key: play_all
    music:
      mood: ecstatic
      speakers:
        - living_room
        - dining_room
        - kitchen
        - bedroom
  -
    name: Dinner Party
    key: dinner
    music:
      mood: calm
      speakers:
        - kitchen
        - dining_room
  -
    name: All Off
    key: off
    music:
      action: pause
    speakers:
      - none
  -
    name: Change Song
    key: new_song
    music:
      mood: stressed
```

If you load this up and send `/scene/dinner`, you'll notice that it sends these messages:
```
/music/play <some calm song>
/music/speakers/living_room 0
/music/speakers/dining_room 1
/music/speakers/kitchen 1
/music/speakers/living_room 0
```

Because the scenes always try to match the specified *state*, if you don't include speakers in the list, it will turn them off, and if you do include them, it will turn them on.  This way, it doesn't matter what the current state of the system is, when you want to set up for a dinner party it will send all of the necessary commands to do so.  It will send the mapped `in` command for the items in the list and the mapped `out` command for those not.

If the list is simply `- none`, it will send the `out` commands for all the items.  If you omitted the list entirely (like in the `Change Song` scene), no commands from that list will be sent.

### Wrapping Up

Hopefully you are well on your way to writing powerful Yaml configuration files for your show control needs!  Obviously these examples were overly simplistic, check out the sample file below for a more realistic example.

One last thing that is worth mentioning is that all value types are supported, both for routing and in the map, so you can send crazy messages like this this lots of values attached:

```
map:
  some_endpoint:
    crazy_message: /foo/bar/baz 5.43345 8 "Hello, World!" true false true
```


## The YAML Configuration File - Specifications
The scenes.yaml configuration file should contain the following sections:

### Endpoints

This is a list of the applications you would like to send OSC commands to.  Options for each item include:
* `prefix` (string) - What commands should be sent to this endpoint?
  - Most OSC commands start with a device indicator, such as `/dmxis/command/...`.  Setting the prefix as `dmxis` will cause all OSC commands that start with `/dmxis/` to be sent to this endpoint.
* `ip` (string) - A valid IPv4 address of where to send the commands.
  - If the endpoint is running on the same computer as the scene controller, use `127.0.0.1`.
* `port` (int) - The UDP port to send the OSC commands to

### Map

A Yaml hiearchy that eventually maps to OSC commands.

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

### Scenes

This is a list of scenes, each with the following options:
* `name`:string - The descriptive display name of the scene
* `key`:string - A lowercase, one-word string that represents how this scene will be called
  - If you want to call this using `/scenes/scene1`, then the `key` would be `scene1`
* The actual scene parameters, as defined in the map


## Sample `scenes.yaml` file
Here is what a basic `scenes.yaml` file should look like:

```yaml
endpoints:
  -
    prefix: atem
    ip: 10.0.0.2
    port: 3456
  -
    prefix: sc
    ip: 127.0.0.1
    port: 8001

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

### Sending complex data using argument lists

The above example only showed integers in the map, but many types of OSC messages are supported. The type is assumed as follows:
* Only digits 0-9: `int`
* Digits 0-9 with one decimal point: `float`
* "true" and "false" (case-insensitive): `bool`
* All others: `string`

For example, you could specify the following in the map:
```
foo: /this/is/a/complex/message 45 testing 4.5689 false
```

The types for this message would be: `int`, `string`, `float`, and `bool`

### Infinite levels
In the above example file, the mapping only went 3/4 levels deep.  You can go as deep as needed, as long as the levels in your map match the levels in your scene

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
source env/bin/activate  # Might be /env/Scripts/activate on Windows
pip3 install -r requironments.txt
```

### Developing

Modify the OSCSceneController.py file to fix issues or add new features
Test your changes by running `python3 OSCSceneController.py`

### Building the Executable

Run the included build script to generate the new executable file for your operating system:
```sh
python3 build.py
```

### Submitting Pull Request

Feel free to submit a pull request with your fix or feature!  I'll review it as soon as I can.
