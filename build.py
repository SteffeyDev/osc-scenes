import os
import platform
import shutil

# Removes current binaries if they exist
if os.path.exists('dist'):
  shutil.rmtree('dist')

if (platform.system() == "Windows"):
  os.system('pyinstaller --onefile -w -i app_icon.ico OSCSceneController.py')

if (platform.system() == "Darwin"): # MacOS
  
  # Generate spec file
  os.system('pyi-makespec --onefile -w --osx-bundle-identifier com.peters.osc-scenes -i app_icon.icns OSCSceneController.py')
  plist = """
            info_plist={
               'NSHighResolutionCapable': 'True',
               'CFBundleShortVersionString':'0.1.1',
               'CFBundleDisplayName':"OSC Scene Controller",
               'CFBundleName':"OSC Scene Controller"
             },\n"""

  # Add custom options into spec file
  with open('OSCSceneController.spec', 'r') as inFile:
    with open('OSCSceneController.spec.new', 'w') as outFile:
      for line in inFile.readlines():
        outFile.write(line)
        if 'BUNDLE' in line:
          outFile.write(plist)
  os.rename('OSCSceneController.spec.new', 'OSCSceneController.spec')

  # Run from spec file
  os.system('pyinstaller OSCSceneController.spec')
            
