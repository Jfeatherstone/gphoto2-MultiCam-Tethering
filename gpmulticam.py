#!/usr/bin/env python3

# gphoto2 MultiCam Tethering Utility
# https://github.com/acropup/gphoto2-MultiCam-Tethering/
# Requires gphoto2 (linux-only): http://gphoto.org/doc/manual/using-gphoto2.html
# To run from command line, type: python3 -i gpmulticam.py

import re
import os
import time
import subprocess #https://docs.python.org/3/library/subprocess.html
from multiprocessing import Pool

cameras = []
name_ind = 0
port_ind = 1

output_folder = './output/'
filename_format = output_folder + '{0}_{1}' #0 is filename, 1 is camera name
simultaneous_capture = True
keep_on_camera = True

#TODO: notes for how to use subprocess
# p = subprocess.run(['dir', '/p'], stdout=subprocess.PIPE, universal_newlines=True)
# p = subprocess.run(['xdg-open', picfilename.jpg], stdout=subprocess.PIPE, universal_newlines=True)

# p= subprocess.Popen('ping google.com /t', stdout=subprocess.PIPE, universal_newlines=True)
# p.stdout.readline()

def main():
    welcome = '*' * 3 + ' Welcome to Better Way Camera Tethering ' + '*' * 3
    print('*' * len(welcome))
    print(welcome)
    print('*' * len(welcome))
    print()
    input('Press Enter to find cameras...')

    initCameras()

    while(True):
        print('-'*40)

        cmd = input(f'{os.getcwd().strip()} > ')
        if not processCommand(cmd):
            break

def queryCameras():
    "queries for connected cameras, and returns an array of their port mappings"
    p = subprocess.run(['gphoto2', '--auto-detect'], stdout=subprocess.PIPE, universal_newlines=True)
    # p.stdout should return something like this:
    # Model                          Port                                             
    # ----------------------------------------------------------
    # Canon PowerShot G2             usb:001,014
    # Canon PowerShot G2             usb:001,023
    if p.returncode == 0:
        r = re.compile(r'^(.*?)   +(usb:\S*)\s', re.MULTILINE)
        matches = r.findall(p.stdout)
        #tuples are immutable, so convert list of tuples to list of lists (so we can edit the name later)
        cameras = [{'name':n, 'port':p} for n,p in matches]
        return True, cameras

    return False, []


def listCameras():
    """
    """
    id_width = 4
    name_width = 2 + max([len(cam["name"]) for cam in cameras])
    # Print header
    print(f'{"ID".ljust(id_width)} {"Name".ljust(name_width)} Port')

    # Print camera info
    for i, cam in enumerate(cameras):
        print(f'{str(i).ljust(id_width)} {cam["name"].ljust(name_width)} ({cam["port"]})')
    print()


def renameCameras():
    """
    Lets the user rename each camera. Takes a picture with
    each camera sequentially, to identify which camera it is.
    """

    print('''The camera name is part of the filename for all pictures taken with it.
    Choose a different name for every camera.
    ''')

    for i, cam in enumerate(cameras):
        name = ''
        print(f'Taking a picture with camera {i}!')

        takePicture(cam["port"], 'test.jpg')
        openPicture('test.jpg')

        while(len(name) == 0):
            name = input(f'Enter name for camera {i}: ')
        cam["name"] = name

    print('All cameras have been named!\n')


def initCameras():
    """
    Initialize cameras
    """
    global cameras
    success, result = queryCameras()

    if not success:
        print('Query Camera failed! Make sure gphoto2 is installed.')
        return

    if (len(result) == 0):
        print('No cameras found! Make sure that cameras are connected by USB and powered on.')
        print('If camera is accessible as an external drive, you may have to "Eject..." it.')
        return

    cameras = result
    print(f'{len(cameras)} cameras found:\n')
    listCameras()

    if (input_yn('Name cameras?')):
        renameCameras() 
        listCameras()


def openPicture(filename):
    """
    """
    if (os.path.exists(filename)):
        #This should open the image using the default image viewer
        subprocess.Popen(['xdg-open', filename], universal_newlines=True)
    else:
        print(f'Could not open "{filename}"')

def takePicture(port, filename):
    """
    """
    cmd_params = ['gphoto2', '--port', port, '--capture-image-and-download', '--force-overwrite', '--filename', filename]
    subprocess.run(cmd_params, stdout=subprocess.DEVNULL)


def executeAtSpecificTime(tup):
    """
    Execute a command at (or as soon as possible after) a specific
    time

    Parameters
    ----------
    tup : tuple(command, time)

        command : str
            The command to execute.

        executionTime : float
            The time in seonds at which to execute the command.
    """
    command, executionTime = tup
    while time.perf_counter() < executionTime:
        continue

    subprocess.run(command, stdout=subprocess.PIPE)

    return


def takePictures(name):
    """
    """
    sim_cmds = []
    if (not cameras):
        print('There are no cameras connected. Use fc command to find cameras.')
        return

    for cam in cameras:
        filename = filename_format.format(name, cam["name"]) + '.jpg'

        if os.path.exists(filename) and not input_yn('File with same name already exists. Overwrite?'):
            print(f'Aborting capture sequence. File already exists:\n{os.path.abspath(filename)}')
            return

        cmd_params = ['gphoto2', '--port', cam["port"], '--capture-image-and-download', '--force-overwrite', '--filename', filename]
        print(f'Taking picture: "{filename}"')

        if not simultaneous_capture:
            subprocess.run(cmd_params, stdout=subprocess.PIPE)    #this line blocks until the photo capture and download completes
            openPicture(filename)
        else:
            # We add the command to a list to then execute later
            sim_cmds.append(cmd_params)

    if simultaneous_capture:
        # Choose a time a second or so in the future at which we want to execute
        # all of the commands. Doesn't need to have any specific value, but should
        # be enough time for all of the processes to be registered and queued.
        executionTime = time.perf_counter() + 0.5 # 0.5 seconds after
        
        def combinedGenerator():
            for cmd in sim_cmds:
                yield cmd, executionTime

        # Generate a pool of workers
        with Pool(processes=len(cameras)) as pool:
            # Each of which waits until the specified time and takes the picture
            for res in pool.imap_unordered(executeAtSpecificTime, combinedGenerator()):
                pass

def recordMovie(duration, name):
    """
    """
    sim_cmds = []
    if (not cameras):
        print('There are no cameras connected. Use fc command to find cameras.')
        return

    for cam in cameras:
        filename = filename_format.format(name, cam["name"]) + '.mov'

        if os.path.exists(filename) and not input_yn('File with same name already exists. Overwrite?'):
            print(f'Aborting capture sequence. File already exists:\n{os.path.abspath(filename)}')
            return

        cmd_params = ['gphoto2', '--port', cam["port"], '--set-config', 'movie=1', f'--wait-event={duration}s', '--set-config', 'movie=0', '--wait-event-and-download=2s', '--filename', filename]
        #cmd_params = ['gphoto2', '--port', cam["port"], '--capture-movie={duration}s', '--force-overwrite', '--filename', filename]
        print(f'Recording video: "{filename}"')

        if not simultaneous_capture:
            subprocess.run(cmd_params, stdout=subprocess.PIPE)    #this line blocks until the photo capture and download completes
            openPicture(filename)
        else:
            # We add the command to a list to then execute later
            sim_cmds.append(cmd_params)

    if simultaneous_capture:
        # Choose a time a second or so in the future at which we want to execute
        # all of the commands. Doesn't need to have any specific value, but should
        # be enough time for all of the processes to be registered and queued.
        executionTime = time.perf_counter() + 0.5 # 0.5 seconds after
        
        def combinedGenerator():
            for cmd in sim_cmds:
                yield cmd, executionTime

        # Generate a pool of workers
        with Pool(processes=len(cameras)) as pool:
            # Each of which waits until the specified time and takes the picture
            for res in pool.imap_unordered(executeAtSpecificTime, combinedGenerator()):
                pass


def processCommand(cmd):
    global filename_format
    global simultaneous_capture
    global keep_on_camera
 
    args = cmd.split(' ')

    # The function to call
    c = args[0]
    # Potential parameters
    params = args[1:] if len(args) > 1 else None

    # HELP
    if c == '' or c == 'help':
        print('''Management:
        fc - find cameras
        cn - camera names
        sc - toggle sequential/simultaneous capture
        kc - toggle keep photo on camera card
        ff - filename format (ex. "{0} - {1}.jpg")
        cd - change directory
        ls - list directory contents
        od - open directory in file browser
        q  - quit''')

        print('''Photo capture:
        pic [name] - capture a picture and store it as [name]
        mov [t] [name] - record a movie for [t] seconds and store it as [name]
        ''')


    # QUIT
    if (c == 'q'):
        if input_yn('Are you sure you want to quit?'):
            print('Quitting...')
            return False
       
    # FIND CAMERAS
    elif c == 'fc':
        if cameras:
            print('Current camera list:\n')
            listCameras()

            if input_yn('Search for cameras?'):
                initCameras()
        else:
            initCameras()
       
    # CAMERA NAMES
    elif c == 'cn':
        if cameras:
            print('Current camera list:\n')
            listCameras()

            if (input_yn('Rename all cameras?')):
                renameCameras()
        else:
            print('There are no cameras to name. Use fc command to find cameras.')
       
    # SIMULTANEOUS CAPTURE TOGGLE
    elif c == 'sc':
        simultaneous_capture = not simultaneous_capture
        print('Capture mode: ' + ('Simultaneous' if simultaneous_capture else 'Sequential'))

    # KEEP ON CAMERA CARD TOGGLE
    elif c == 'kc':
        keep_on_camera = not keep_on_camera
        print('Camera card retention mode: ' + ('Keep on camera card' if keep_on_camera else 'Delete from camera after download'))

    # CHANGE FILENAME FORMAT
    elif c == 'ff':
        # If there is a parameter, it is taken as the new format
        if param:
            filename_format = ' '.join(params)
            print(f'Filename format: "{filename_format}"')
        else:
            # Otherwise, we input the format now
            print('{0} for shot name, and {1} for camera name')
            param = input('Set to: ')
            
        print('Filename format: "{}"'.format(filename_format))
       
    # CHANGE DIRECTORY
    elif c == 'cd':
      if not param:
        param = input('Change directory to: ')
      if param:
        changed = cd(param)
        if (not changed):
          print('Path does not exist: ' + os.path.abspath(param))
          if (input_yn("Make new directory?")):
            if(mkdir(param)): #Make directory and try to cd again
              changed = cd(param)
            else:
              print('Could not make directory')
      else:
        print('No change')

    # LIST DIRECTORY CONTENTS
    elif (c == 'ls'):
      all_items = os.listdir('.')
      dirs = [i for i in all_items if os.path.isdir(i)]
      files = [i for i in all_items if os.path.isfile(i)]
      if (dirs):
        print('Folders:\n  ' + '\n  '.join(dirs))
      else:
        print('No folders.')
      if (files):
        maxfiles = len(files) if (param == '-a') else 10
        print('Files:\n  ' + '\n  '.join(files[:maxfiles]))
        if (len(files) > maxfiles):
          print('...and {} more. Show all with "ls -a"'.format(len(files)-maxfiles))
      else:
        print('No files.')

    # OPEN DIRECTORY IN FILE BROWSER
    elif (c == 'od'):
      print('Opening file browser to "{}"'.format(os.getcwd()))
      #TODO This only works now because openPicture depends on xdg-open to do the right thing
      openPicture('./')

    # TAKE PICTURE
    elif (c == 'pic'):
        takePictures(params[0])

    # TAKE MOVIE
    elif (c == 'mov'):
        recordMovie(params[0], params[1])
    
    return True

def cd(path):
  try:
    os.chdir(path)
  except FileNotFoundError:
    return False
  except NotADirectoryError:
    return False
    
  return True

def mkdir(path):
  try:
    os.makedirs(path)
  except FileNotFoundError:
    return False
  except FileExistsError:
    return False
    
  return True

def input_yn(msg):
  return 'y' == input(msg + ' (y/n) ')[:1].lower()
  
 
if __name__ == '__main__':
    main()
