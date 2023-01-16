import os
import time

import win32api
import win32con
import win32process
from psychopy import core, data, gui
from pynput import keyboard

from modules.arduino_comm import ArduinoComm
from modules.expert_interface import ExpertInterface
from modules.file_management import FileManager
from modules.kinect_comm import KinectComm


def setpriority(pid=None, priority=5):
    """ Set The Priority of a Windows Process.  Priority is a value between 0-5 where
        2 is normal priority.  Default sets the priority of the current
        python process but can take any valid process ID. """

    priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
                       win32process.BELOW_NORMAL_PRIORITY_CLASS,
                       win32process.NORMAL_PRIORITY_CLASS,
                       win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                       win32process.HIGH_PRIORITY_CLASS,
                       win32process.REALTIME_PRIORITY_CLASS]
    if pid is None:
        pid = win32api.GetCurrentProcessId()
    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
    win32process.SetPriorityClass(handle, priorityclasses[priority])

setpriority()

script_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_path)

# -- GET INPUT FROM THE EXPERIMENTER --
expt_info = {
    '01. Experiment Name': 'controlled-touch-MNG',
    '02. Participant Code': 'ST12',
    '03. Unit Number': 0,
    '04. Folder for saving data': 'data',
    '05. Start from block no.': 1
    }
dlg = gui.DlgFromDict(expt_info, title='Experiment details')
if dlg.OK:
    pass  # continue
else:
    core.quit()  # the user hit cancel so exit

# add the time when the user pressed enter:
expt_info['Date and time'] = data.getDateStr(format='%Y-%m-%d_%H-%M-%S')
date_time = expt_info['Date and time']
experiment_name = expt_info['01. Experiment Name']
participant_id = expt_info['02. Participant Code']
unit_name = expt_info['03. Unit Number']
data_folder = expt_info['04. Folder for saving data']
block_no = expt_info['05. Start from block no.']

# -- MAKE FOLDER/FILES TO SAVE DATA --
filename_core = experiment_name + '_' + participant_id + '_' + '{}' .format(unit_name)
filename_prefix = date_time + '_' + filename_core
fm = FileManager(data_folder, filename_prefix)
fm.generate_infoFile(expt_info)

# -- SETUP STIMULUS CONTROL --
types = ['tap', 'stroke']
contact_areas = ['one finger tip', 'whole hand', 'two finger pads']
#speeds = [3.0, 6.0, 9.0, 15.0, 18.0, 21.0, 24.0] #cm/s
speeds = [3.0] #cm/s
forces = ['light'] #, 'moderate', 'strong']

stim_list = []
for type in types:
    for contact_area in contact_areas:
        for speed in speeds:
            for force in forces:
                stim_list.append({
                'type': type,
                'contact_area': contact_area,
                'speed': speed,
                'force': force
                })

n_stim_per_block = len(speeds)*len(forces)
n_blocks = int(len(stim_list)/n_stim_per_block)

# -- SETUP AUDIO --
sounds_folder = "sounds"
#am = AudioManager(sounds_folder)


# -- SETUP KINECT CONNECTION --
kinect_recorder_path = r'C:\Program Files\Azure Kinect SDK v1.2.0\tools'
kinect_output_subfolder = r'C:\Program Files\Azure Kinect SDK v1.2.0\tools\data'
#kinect_output_subfolder = fm.data_folder + './' + date_time
kinect = KinectComm(kinect_recorder_path, kinect_output_subfolder)


# -- SETUP EXPERIMENT CLOCKS --
expt_clock = core.Clock()
stim_clock = core.Clock()


# -- MAIN EXPERIMENT LOOP --
stim_no = (block_no-1)*n_stim_per_block # start with the first stimulus in the block
start_of_block = True
expt_clock.reset()
fm.logEvent(expt_clock.getTime(), "experiment started")
while stim_no < len(stim_list):

    if start_of_block:
        # start kinect recording
        fm.logEvent(expt_clock.getTime(), "about to tell kinect to start recording")
        kinect.start_recording(filename_core + '_block{}' .format(block_no))
        kinect_start_time = expt_clock.getTime()
        fm.logEvent(kinect_start_time, "told kinect to start recording {}" .format(kinect.filename))
        kinect_start_delay = 2.0  # how long to wait to make sure the kinect has started
        time.sleep(kinect_start_delay)

        # trigger/sync signal -> TTL to nerve recording and LED to camera (make sure it is visible)
        fm.logEvent(expt_clock.getTime(), "about to tell triggerbox to send pulses/flashes")
        fm.logEvent(
            expt_clock.getTime(),
            "told triggerbox to send {} pulses/flashes for block number" .format(block_no)
        )
        start_of_block = False

    # pre-stimulus waiting period
    stim_clock.reset()
    while stim_clock.getTime() < 1.5:
        pass
    fm.logEvent(expt_clock.getTime(), "TTL/LED on")

    # metronome for timing during stimulus delivery
    if 1:
        ei = ExpertInterface(audioFolder="cues", imgFolder="img")
        ei.initialise(stim_list[stim_no]['type'],
                      stim_list[stim_no]['contact_area'],
                      stim_list[stim_no]['force'],
                      stim_list[stim_no]['speed'])
        ei.start_sequence()
        del ei

    fm.logEvent(
        expt_clock.getTime(),
        'stimulus presented: {}, {}cm/s, {}, {} force' .format(
            stim_list[stim_no]['type'],
            stim_list[stim_no]['speed'],
            stim_list[stim_no]['contact_area'],
            stim_list[stim_no]['force'],
        )
    )

    # stand-in for stimulus duration
    # stim_clock.reset()
    # while stim_clock.getTime() < 1:
    #     pass

    # trigger/sync signal off
    fm.logEvent(expt_clock.getTime(), "TTL/LED off")

    # write to data file
    fm.dataWrite([
        stim_no+1,
        stim_list[stim_no]['type'],
        stim_list[stim_no]['speed'],
        stim_list[stim_no]['contact_area'],
        stim_list[stim_no]['force'],
        block_no,
        kinect.filename
    ])

    fm.logEvent(
        expt_clock.getTime(),
        "stimulus {} of {} complete (in block {})" .format(stim_no+1, len(stim_list), block_no)
    )
    stim_no += 1

    # check if it's the end of the block
    if stim_no % n_stim_per_block == 0:

        # Kinect off
        fm.logEvent(expt_clock.getTime(), "about to tell the Kinect to stop")
        kinect.stop_recording(2)  # stop recording with a delay
        fm.logEvent(expt_clock.getTime(), "Kinect stopped")

        fm.logEvent(
            expt_clock.getTime(),
            "block {} of {} complete" .format(block_no, n_blocks)
        )
        block_no += 1
        start_of_block = True

fm.logEvent(expt_clock.getTime(), "Experiment finished")