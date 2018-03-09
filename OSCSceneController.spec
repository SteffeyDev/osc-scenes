# -*- mode: python -*-

block_cipher = None


a = Analysis(['OSCSceneController.py'],
             pathex=['/Users/petersteffey/Documents/osc-scenes'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='OSCSceneController',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='OSCSceneController')
app = BUNDLE(coll,
             name='OSCSceneController.app',
             icon='applet.icns',
             bundle_identifier='com.peters.osc-scenes',
             info_plist={
               'NSHighResolutionCapable': 'True',
               'CFBundleShortVersionString':'0.1.1',
               'CFBundleDisplayName':"OSC Scene Controller",
               'CFBundleName':"OSC Scene Controller"
             }
            )
