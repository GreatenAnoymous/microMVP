'''

 All components of this library are licensed under the BSD 3-Clause
 License.

 Copyright (c) 2015-, Algorithmic Robotics and Control Group @Rutgers
 (http://arc.cs.rutgers.edu). All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are
 met:

 Redistributions of source code must retain the above copyright notice,
 this list of conditions and the following disclaimer.  Redistributions
 in binary form must reproduce the above copyright notice, this list of
 conditions and the following disclaimer in the documentation and/or
 other materials provided with the distribution. Neither the name of
 Rutgers University nor the names of the contributors may be used to
 endorse or promote products derived from this software without specific
 prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
"""
GUI for micro MVP

"""

import pygame
from pygame.locals import *

from colorama import Fore, Back, Style
from pgu import gui
from random import random
import math
import os
import sys
import argparse
import positionZMQSub
import threading
import time
import DDR
import imp
from os import listdir
from os.path import isfile, join
from munkres import Munkres
from queue import Queue
import utils
import common
import json
import openai
import re
# import os
import sounddevice as sd
import wave
import pyaudio
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./alpine-inkwell-383218-a4ad34b18412.json"


from google.cloud import speech


if "-s" not in sys.argv:
    import CrazyRadioMVP

lock = threading.Lock()


class colors:  # You may need to change color settings
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"

# Simulation screen
class Painter(gui.Widget):
    
    def __init__(self,**params):
        gui.Widget.__init__(self,**params)       
        self.surface = None
        self.font = pygame.font.SysFont("comicsansms", int(utils.wheelBase))
        self.carImage = pygame.image.load("./images/carImage.png")
        self.carImage = pygame.transform.smoothscale(self.carImage, (int(utils.wheelBase * 2.0 / (9.0 / 8.0)), int(utils.wheelBase * 2.0)))
        self.bound = None
        self.pointPool = Queue()
        self.record = False

    def init(self, v):
        # thread lock for screen 2
        self.lock2 = threading.Lock()

        self.surface = pygame.Surface((int(v['width']),int(v['height'])))
        self.surface.fill(utils.RGB_WHITE)
        self.repaint()
        self.t1 = threading.Thread(target = self.recordMouse)
        self.t1.setDaemon(True)
        self.showMode = 0
    
    def paint(self, s):
        # Update the screen
        s.blit(self.surface,(0,0))


    
  

    def event(self, e):
        # Screen 2 event handler (basically the mouse movement)
        if not self.surface: return
        
        if e.type == gui.MOUSEBUTTONDOWN:
            with self.lock2:
                self.record = True
        elif e.type == gui.MOUSEBUTTONUP:
            with self.lock2:
                self.record = False

    def recordMouse(self):
        # Record the position of mouse, if leftbutton is down
        rec = False
        while True:
            with self.lock2:
                rec = self.record
            if rec:
                self.pointPool.put(pygame.mouse.get_pos())
            time.sleep(0.01)

    def draw(self, locs, paths):
        # Draw screen 2
        self.surface.fill(utils.RGB_WHITE)

        with self.lock2:
            sm = self.showMode

        # Draw Boundary
        pygame.draw.rect(self.surface, utils.RGB_GREY, self.bound, 1)

        # Show the grid for mrpp (can be deleted if you dont use mrpp)
        if sm == 1:
            for i in range(len(utils.gridCopy)):
                for j in range(len(utils.gridCopy[0]) - 1):
                    if i % 2 != j % 2:
                        continue 
                    pygame.draw.line(self.surface, utils.RGB_BLACK, utils.gridCopy[i][j], utils.gridCopy[i][j + 1])
            for i in range(len(utils.gridCopy) - 1):
                for j in range(len(utils.gridCopy[0])):
                    pygame.draw.line(self.surface, utils.RGB_BLACK, utils.gridCopy[i][j], utils.gridCopy[i + 1][j])
            for i in range(len(utils.gridCopy)):
                for j in range(len(utils.gridCopy[0])):
                    pygame.draw.circle(self.surface, utils.RGB_BLACK, (int(utils.gridCopy[i][j][0]), int(utils.gridCopy[i][j][1])), 3, 0)

        # Draw Path
        for index, path in enumerate(paths):
            if len(path) <= 1:
                continue
            if sm != 2:
                pygame.draw.lines(self.surface, utils.RGB_PATH_COLORS[index], False, path, 5)
            text = self.font.render("Goal"+ str(locs[index][3]), 1, utils.RGB_PATH_COLORS[index])
            self.surface.blit(text, path[-1])
            pygame.draw.circle(self.surface, utils.RGB_PATH_COLORS[index], (int(path[-1][0]), int(path[-1][1])), 5, 0)

        # Draw Car
        for index, stat in enumerate(locs):
            car = pygame.transform.rotate(self.carImage, - 180.0 * stat[2] / math.pi - 90)
            text = self.font.render(str(stat[3]), 1, utils.RGB_PATH_COLORS[index])
            self.surface.blit(car, (stat[0] - utils.wheelBase, stat[1] - utils.wheelBase)) 
            self.surface.blit(text, (stat[0] - utils.wheelBase / 2, stat[1] - utils.wheelBase / 2))    

        # Collosion Detection
        for ind1, i in enumerate(locs):
            for ind2, j in enumerate(locs):
                if ind1 == ind2:
                    continue
                else:
                    if utils.CheckCollosion(utils.wheelBase * 1.5, i[0], i[1], j[0], j[1]):
                        text = self.font.render("TOO CLOSE!", 1, utils.RGB_BLACK)
                        text_width, text_height = self.font.size("TOO CLOSE!")
                        self.surface.blit(text, ((i[0] + j[0]) / 2 - text_width / 2, (i[1] + j[1]) / 2 - text_height / 2))

        self.repaint()  


# Main screen
class App(gui.Desktop):

    # t1 = threading.Thread()
    # t2 = threading.Thread()
    # t3 = threading.Thread()
    # t4 = threading.Thread()

    testflag = True
    
    def startApp(self):
        self.t1 = threading.Thread(target = self.Draw)
        self.t2 = threading.Thread(target = self.Follow)
        self.t3 = threading.Thread(target = self.GetLocation)
        self.t4 = threading.Thread(target = self.SendSpeed)
        self.t5=threading.Thread(target=self.shell_interface)

        self.t1.setDaemon(True)
        self.t2.setDaemon(True)
        self.t3.setDaemon(True)
        self.t4.setDaemon(True)
        self.t5.setDaemon(True)

        self.t3.start()
        self.t1.start()
        self.t2.start()
        self.t4.start()
        self.t5.start()

    def __init__(self, **params):
        gui.Desktop.__init__(self, **params)
        self.init_openai_prompt()
        self.connect(gui.QUIT, self.FlushQuit, None)
        # Setup everything
        self.SetupArgv()
        self.SetupCars()
        self.SetupGUI()

    def extract_python_code(self,content):
        code_blocks=None
        try:
            code_blocks = self.code_block_regex.findall(content)
        except:
            pass
        if code_blocks:
            full_code = "\n".join(code_blocks)

            if full_code.startswith("python"):
                full_code = full_code[7:]

            return full_code
        else:
            return None

    # def init_speech_module(self):
    def record_wav(self):
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1024
        RECORD_SECONDS = 5
        WAVE_OUTPUT_FILENAME = "recording1.wav"
        time.sleep(2)
        audio = pyaudio.PyAudio()

        # Start recording
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

        frames = []
        print("start recording!")
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        # Stop recording
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # Save the recorded data to a WAV file
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def speech_to_text(self):
        client = speech.SpeechClient()
        # Set the path to your audio file
        file_name = "./recording1.wav"

        # Load the audio file into memory
        with open(file_name, "rb") as audio_file:
            content = audio_file.read()

        # Set the encoding and language code
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            enable_automatic_punctuation=True,
            language_code="en-US",
        )

        # Send the transcription request to the Speech-to-Text API
        response = client.recognize(request={"config": config, "audio": audio})
        # print(response.results)
        # Print the transcription
        text=""
        for result in response.results:
            text=result.alternatives[0].transcript
        return text

    
    def shell_interface(self):
        while True:
            print("Welcome to the MircoMVP chatbot! I am ready to help you with your micromvp questions and commands.")
            question = input(colors.GREEN + "MicroMVP> " + colors.ENDC)

            if question == "!quit" or question == "!exit":
                break

            if question == "!clear":
                os.system("cls")
                continue

            response = self.ask_prompt(question)

            print(f"\n{response}\n")

            code = self.extract_python_code(response)
            if code is not None:
                print("Please wait while I run the code in MicroMVP...")
                print("code:",code)
                exec(code)
                print("Done!\n")

    def ask_prompt(self,prompt):
        # print("prompt")
        # return self.chat_history[-1]["content"] 
        self.chat_history.append(
            {
                "role": "user",
                "content": prompt,
            }
        )
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.chat_history,
            temperature=0
        )
        self.chat_history.append(
            {
                "role": "assistant",
                "content": completion.choices[0].message.content,
            }
        )
        return self.chat_history[-1]["content"] 
    

    def sampling_the_paths(self,paths,frequency=20):
        new_paths=[]
        for path in paths:
            new_p=[]
            for i in range(0,len(path)-1):
                vt=path[i]
                vtt=path[i+1]
                for k in range(frequency):
                    vk=(vt[0]+(vtt[0]-vt[0])*k/frequency,vt[1]+(vtt[1]-vt[1])*k/frequency)
                    new_p.append(vk)
            new_p.append(path[-1])
            new_paths.append(new_p)
        return new_paths    


    def init_openai_prompt(self):
        with open("config.json", "r") as f:
            config = json.load(f)
        self.code_block_regex = re.compile(r"```(.*?)```", re.DOTALL)
        print("Initializing ChatGPT...")
        openai.api_key = config["OPENAI_API_KEY"]

        with open("./prompt/micromvp_basic.txt", "r") as f:
            sysprompt = f.read()

            self.chat_history = [
                {
                    "role": "system",
                    "content": sysprompt
                },
                {
                    "role": "user",
                    "content": "move 10 units up"
                },
                {
                    "role": "assistant",
                    "content": """```python print("hello")```

                    This code uses the `fly_to()` function to move the drone to a new position that is 10 units up from the current position. It does this by getting the current position of the drone using `get_drone_position()` and then creating a new list with the same X and Y coordinates, but with the Z coordinate increased by 10. The drone will then fly to this new position using `fly_to()`."""
                }
            ]

            self.ask_prompt(sysprompt)
            print("Welcome to the MircoMVP chatbot! I am ready to help you with your micromvp questions and commands.")

    def FlushQuit(self, garbage):
        with lock:
            if not self.sim:
                print(self.CrazyRadio)
                self.CrazyRadio.CrazyRadioFlush7()
        self.quit()

    def SetupArgv(self):
        self.paths_name=None
        parser = argparse.ArgumentParser(description = "microMVP")
        parser.add_argument("-s", dest = "sim", action = "store_true", default = False, help = "Simulation Mode")
        parser.add_argument("--i", help="path file name")
        args = parser.parse_args()
        self.sim = bool(os.environ.get("sim", args.sim))
        if args.i:
            self.paths_name=args.i
        self.vMax = 1.0
        self.simSpeed = utils.simSpeed
        if not self.sim:
            self.simSpeed = 0.6
        self.runCar = False
        if not self.sim:
            # CrazyRadio is the object
            # CrazyRadioMVP is the file that was imported
            # CrazyRadioTransmitter is the class, it is not named CrazyRadio
            #   because the original class made by Crazyflie is called Crazyradio
            self.CrazyRadio = CrazyRadioMVP.CrazyRadioTransmitter()
            self.CrazyRadio.CrazyRadioFlush7()
        self.syn = False

    def tranlate_paths(self,paths):
        trajs=[]
        for path in paths:
            traj=[]
            for v in path:
                x=self.bound.width/self.map_w*v[0]+self.bound.l
                y=self.bound.height/self.map_h*v[1]+self.bound.u
                traj.append((x,y))
            trajs.append(traj)
        return trajs

    def SetupCars(self):
        # cars
        self.cars = dict()
        paths=None
        if self.paths_name is not None:
            paths,self.map_w,self.map_h=common.read_paths_from_txt(self.paths_name)
            # paths=paths[:2]
        
        
        # Sense the tag
        if not self.sim:
            # if not in simulation pull data from ZMQ data
            positionZMQSub._pull_zmq_data_once()
        else:
            if self.paths_name is not None:
                num_cars=len(paths)
                utils.carInfo=[]
                for i in range(num_cars):
                    utils.carInfo.append((i+1,i+1))

            else:
                utils.carInfo = [ 
                    (1, 1), 
                    (2, 2), 
                    (3, 3), 
                    (4, 4), 
                    (5, 5), 
                    (6, 6), 
                    (7, 7), 
                    (8, 8), 
                    (9, 9),
                    (10, 10)]
     
        for item in utils.carInfo:
            self.cars[item[1]] = utils.UnitCar(tag = item[1], ID = item[0])
        if self.sim:
            self.SetupWB()
            # paths=self.tranlate_paths(paths)
            # paths=self.sampling_the_paths(paths,100)
    
            if self.paths_name is not None:
                for key,item in utils.carInfo:
                    self.cars[item].path=paths[item-1]
                    (self.cars[item].x, self.cars[item].y)=paths[item-1][0]
                    self.cars[item].theta=0
            else:
               
                self.GetRandomArrangement()
        else:
            positionZMQSub._initialize_zmq()
            self.SetupWB()
            if self.paths_name is not None:
                self.tranlate_paths(paths)
                for key,item in utils.carInfo:
                    self.cars[item].path=paths[item]
    def SetupWB(self):
        # Auto-detect the size of cars
        if self.sim:
            pass
        else:
            utils.wheelBase -= 30
            data = positionZMQSub._get_all_car_position_data()
        
            read = 0
            for garbage, key in utils.carInfo:
                # print(garbage,key)
                if key not in data:
                    continue
                if data[key] == "":
                    continue
                else:
                    read += 1
                    x0, y0, x1, y1, x2, y2, x3, y3 = data[key].split()
                    tagSize = math.sqrt(math.pow(float(x0) - float(x1), 2) + math.pow(float(y0) - float(y1), 2)) 
                    utils.wheelBase += tagSize / utils.tagRatio
            utils.wheelBase = utils.wheelBase / read  
            # print(utils.wheelBase)
        self.bound = utils.Boundary()

    def SetupGUI(self):
        c = gui.Container(width = utils.container_width, height = utils.container_height)

        # Dialogs
        self.quit_d = utils.QuitDialog()
        self.quit_d.connect(QUIT, self.quit, None)
        self.help_d = utils.HelpDialog()
        self.about_d = utils.AboutDialog()
        
        # Main menu
        menus = self.SetupMenus()        
        c.add(menus, 0, 0)
        menus.rect.w, menus.rect.h = menus.resize()

        # Toolbox
        ctrls = self.SetupToolbox()
        c.add(ctrls, 0, menus.rect.bottom + utils.spacer)

        ctrls.rect.x, ctrls.rect.y = ctrls.style.x, ctrls.style.y
        ctrls.rect.w, ctrls.rect.h = ctrls.resize()

        self.painter = Painter(width = utils.painter_width, height = utils.painter_height, style={'border': 2})
        self.painter.bound = pygame.Rect(self.bound.l, self.bound.u, self.bound.width, self.bound.height)
        self.x_offset = ctrls.rect.w + utils.spacer
        self.y_offset = menus.rect.h + utils.spacer
        c.add(self.painter, self.x_offset, self.y_offset)
        self.painter.init({'width': utils.painter_width,'height': utils.painter_height})
        self.painter.rect.w, self.painter.rect.h = self.painter.resize()

        self.widget = c
        self.painter.t1.start()
        self.t1 = threading.Thread(target = self.ReadMouse)
        self.t1.setDaemon(True)
        self.t1.start()

    def SetupMenus(self):
        self.menus = menus = gui.Menus([
            ('File/Exit',self.quit_d.open,None),
            ('Help/Help',self.help_d.open,None),
            ('Help/About',self.about_d.open,None),
            ])
        return menus

    def SetupToolbox(self):
        self.ctrls = ctrls = gui.Table(width = 125)

        ctrls.tr()
        ctrls.td(gui.Label(" Car Control: "), align = 0)

        ctrls.tr()
        btn_run = gui.Button("Run", width = 90)
        btn_run.connect(gui.CLICK, self.B_run)
        ctrls.td(btn_run)

        ctrls.tr()
        btn_stop = gui.Button("Stop", width = 90)
        btn_stop.connect(gui.CLICK, self.B_stop)
        ctrls.td(btn_stop)

        ctrls.tr()
        btn_clear = gui.Button("Clear", width = 90)
        btn_clear.connect(gui.CLICK, self.B_clear)
        ctrls.td(btn_clear)

        # add button for test purpose
        ctrls.tr()
        btn_test = gui.Button("Test", width = 90)
        btn_test.connect(gui.CLICK, self.B_test)
        ctrls.td(btn_test)

        # # add button for refresh cars
        # ctrls.tr()
        # btn_refresh = gui.Button("Refresh", width = 90)
        # btn_refresh.connect(gui.CLICK, self.B_refresh)
        # ctrls.td(btn_refresh)

        ctrls.tr()
        self.sli_v = gui.HSlider(value= 100,min=0,max = 100,size=20,width=120)
        ctrls.td(self.sli_v, colspan=3)

        ctrls.tr()
        ctrls.td(gui.Label(""), align = 0)

        ctrls.tr()
        ctrls.td(gui.Label(" Draw Path: "))

        ctrls.tr()
        self.sel_car = sel_car = gui.Select()
        for item in utils.carInfo:
            sel_car.add("#" + str(item[0]) + ", Tag" + str(item[1]), item[1])
        ctrls.td(sel_car)

        ctrls.tr()
        ctrls.td(gui.Label(""), align = 0)

        ctrls.tr()
        ctrls.td(gui.Label(" Patterns: "), align = 0)

        files = [f for f in listdir("patterns/") if isfile(join("patterns/", f))]
        ctrls.tr()
        self.sel_ptn = sel_ptn = gui.Select()
        for f in files:
            if ".py" in f:
                if ".pyc" not in f:
                    sel_ptn.add(f.split(".")[0], f)
        ctrls.td(sel_ptn)

        ctrls.tr()
        btn_pattern = gui.Button("Get Pattern", width = 90)
        btn_pattern.connect(gui.CLICK, self.B_pattern)
        ctrls.td(btn_pattern)

        ctrls.tr()
        ctrls.td(gui.Label(""), align = 0)

        ctrls.tr()
        ctrls.td(gui.Label("Path Planning:"), align = 0)

        files = [f for f in listdir("algorithms/") if isfile(join("algorithms/", f))]
        ctrls.tr()
        self.sel_alg = sel_alg = gui.Select()
        for f in files:
            if ".py" in f:
                if ".pyc" not in f:
                    sel_alg.add(f.split(".")[0], f)
        ctrls.td(sel_alg)

        ctrls.tr()
        btn_plan = gui.Button("Run ALG", width = 90)
        btn_plan.connect(gui.CLICK, self.B_plan)
        ctrls.td(btn_plan)


        ctrls.tr()
        ctrls.td(gui.Label(""), align = 0)
        ctrls.tr()
        btn_speak = gui.Button("Speak", width = 90)
        btn_speak.connect(gui.CLICK, self.speak)
        ctrls.td(btn_speak)

        return ctrls
    
    def speak(self):
        self.record_wav()
        command=self.speech_to_text()
        response=self.ask_prompt(command)
        print(f"\n{response}\n")

        code = self.extract_python_code(response)
        if code is not None:
            print("Please wait while I run the code in MicroMVP...")
            print("code:",code)
            exec(code)
            print("Done!\n")
    

    def B_run(self):
        with lock:
            self.runCar = True

    def B_stop(self):
        with lock:
            self.runCar = False

    def B_clear(self):
        for i in range(3):
            with lock:
                for key in self.cars.keys():
                    self.cars[key].path = []
                if not self.sim:
                    self.CrazyRadio.CrazyRadioFlush7()
            time.sleep(0.1)
        with self.painter.lock2:
                self.painter.showMode = 0
    
    # # refresh sensing vehicles
    # def B_refresh(self):
    #     # Sense the tag
    #     if not self.sim:
    #         with lock:
    #             positionZMQSub._pull_zmq_data_once()

    # function for test
    def B_test(self):
        # not used for sim mode
        if self.sim:
            self.B_clear()
            print("Testing is not for simulation mode\n")
            return
        # terminate Follow thread
        with lock:
            self.testflag = False
        # set flag var
        allGood = True
        # test right turn
        self.B_stop()
        currentlocs = [(0, 0, 0) for x in range(len(self.cars.keys()))]
        #get current location
        with lock:
            for i, j in enumerate(self.cars.keys()):
                currentlocs[i] = (self.cars[j].x, self.cars[j].y, self.cars[j].theta)
        # update speed
        for key in self.cars.keys():
            self.cars[key].path = []
        self.runCar = True
        for info in utils.carInfo:
            self.cars[info[0]].rSpeed = (float) (1 / self.simSpeed)
            self.cars[info[0]].lSpeed = (float) (-1 / self.simSpeed)
        dist = [0 for x in range(len(self.cars.keys()))]
        dir_count = [0 for x in range(len(self.cars.keys()))]
        for k in range(10):
            for i, j in enumerate(self.cars.keys()):
                p_x = currentlocs[i][0]
                p_y = currentlocs[i][1]
                p_theta = currentlocs[i][2]
                if dist[i] < math.sqrt((p_x-self.cars[j].x)**(2) + (p_y-self.cars[j].y)**(2)):
                    dist[i] = math.sqrt((p_x-self.cars[j].x)**(2) + (p_y-self.cars[j].y)**(2))                 
                if (dist[i] > 0.5* utils.wheelBase):
                    allGood = False
                    print(utils.carInfo[i][0], 'wheel has problem!')
                if abs(p_theta - self.cars[j].theta) <= 0.05:
                    dir_count[i] = dir_count[i] + 1
                if k == 9 and dir_count[i] == 10:
                    allGood = False
                    print(utils.carInfo[i][0], 'not moving!')
            time.sleep(0.1)
        # stop cars for next testing
        for info in utils.carInfo:
            self.cars[info[0]].rSpeed = 0
            self.cars[info[0]].lSpeed = 0
        
        time.sleep(1)

        #get current location
        with lock:
            for i, j in enumerate(self.cars.keys()):
                currentlocs[i] = (self.cars[j].x, self.cars[j].y, self.cars[j].theta)
        # update speed
        for key in self.cars.keys():
            self.cars[key].path = []
        self.runCar = True
        for info in utils.carInfo:
            self.cars[info[0]].rSpeed = (float) (-1 / self.simSpeed)
            self.cars[info[0]].lSpeed = (float) (1 / self.simSpeed)
        dist = [0 for x in range(len(self.cars.keys()))]
        dir_count = [0 for x in range(len(self.cars.keys()))]
        for k in range(10):
            for i, j in enumerate(self.cars.keys()):
                p_x = currentlocs[i][0]
                p_y = currentlocs[i][1]
                p_theta = currentlocs[i][2]
                if dist[i] < math.sqrt((p_x-self.cars[j].x)**(2) + (p_y-self.cars[j].y)**(2)):
                    dist[i] = math.sqrt((p_x-self.cars[j].x)**(2) + (p_y-self.cars[j].y)**(2))                 
                if (dist[i] > 0.5* utils.wheelBase):
                    allGood = False
                    print(utils.carInfo[i][0], 'wheel has problem!')
                if abs(p_theta - self.cars[j].theta) <= 0.05:
                    dir_count[i] = dir_count[i] + 1
                if k == 9 and dir_count[i] == 10:
                    allGood = False
                    print(utils.carInfo[i][0], 'not moving!')
            time.sleep(0.1)
        # stop cars for next testing
        for info in utils.carInfo:
            self.cars[info[0]].rSpeed = 0
            self.cars[info[0]].lSpeed = 0
        if(allGood):
            print('All vehicles work well!')
        # restart Follow thread
        with lock:
            self.testflag = True
            self.t2 = threading.Thread(target = self.Follow)
            self.t2.setDaemon(True)
            self.t2.start()

    def set_pattern(self,i):
        print("setting the pattern to",i,"!!!!")
        self.B_stop() 
        if i==0:
            mod = imp.load_source("", "patterns/circle1.py" )
        elif i==1:
            mod=imp.load_source("","patterns/figure8_2.py")
        elif i==2:
            mod=imp.load_source("","patterns/circle2.py")
        else:
            return
        paths = mod.GetPath(len(self.cars.keys()), self.bound)
        locs = [0 for x in range(len(self.cars.keys()))]
        with lock:
            for i, j in enumerate(self.cars.keys()):
                locs[i] = (self.cars[j].x, self.cars[j].y)
        paths2 = self.Shuffle(locs, paths)
        paths2 = self.Refinement(paths2)  

        mod = imp.load_source("", "algorithms/rvo2.py")
        paths1 = mod.GetPath(locs, [p[0] for p in paths2], utils.wheelBase, self.bound)
        paths1 = self.Refinement(paths1)

        pathsm = [[paths1[i][-1], paths2[i][0]] for i in range(len(paths2))]
        pathsm = self.Refinement(pathsm)

        paths = list()
        for i in range(len(paths2)):
            paths.append(paths1[i] + pathsm[i] + paths2[i])
        with self.painter.lock2:
            self.painter.showMode = 0
        with lock:
            self.syn = True
            for i, j in enumerate(self.cars.keys()):
                self.cars[j].path = paths[i]
        print("pattern setup completed!")

    def set_speed(self,speedValue):
        self.simSpeed =speedValue

    def B_pattern(self):
        if self.sel_ptn.value == None:
            return
        self.B_stop() 
        mod = imp.load_source("", "patterns/" + self.sel_ptn.value)
        paths = mod.GetPath(len(self.cars.keys()), self.bound)
        locs = [0 for x in range(len(self.cars.keys()))]
        with lock:
            for i, j in enumerate(self.cars.keys()):
                locs[i] = (self.cars[j].x, self.cars[j].y)
        paths2 = self.Shuffle(locs, paths)
        paths2 = self.Refinement(paths2)  

        mod = imp.load_source("", "algorithms/rvo2.py")
        paths1 = mod.GetPath(locs, [p[0] for p in paths2], utils.wheelBase, self.bound)
        paths1 = self.Refinement(paths1)

        pathsm = [[paths1[i][-1], paths2[i][0]] for i in range(len(paths2))]
        pathsm = self.Refinement(pathsm)

        paths = list()
        for i in range(len(paths2)):
            paths.append(paths1[i] + pathsm[i] + paths2[i])
        with self.painter.lock2:
            self.painter.showMode = 0
        with lock:
            self.syn = True
            for i, j in enumerate(self.cars.keys()):
                self.cars[j].path = paths[i]

    def B_plan(self):
        if self.sel_alg.value == None:
            return
        self.B_stop()
        mod = imp.load_source("", "algorithms/" + self.sel_alg.value)
        locs = [0 for x in range(len(self.cars.keys()))]
        with lock:
            for i, j in enumerate(self.cars.keys()):
                locs[i] = (self.cars[j].x, self.cars[j].y)
        paths = mod.GetPath(locs, self.GetRandomGoals(), utils.wheelBase, self.bound)
        if self.sel_alg.value == "mrpp_b.py":
            paths = paths
        pre_paths = imp.load_source("", "algorithms/rvo2.py").GetPath(locs, [p[0] for p in paths], utils.wheelBase, self.bound)
        for x in range(len(self.cars.keys())):
            paths[x] = pre_paths[x] + paths[x]
        paths = self.Refinement(paths)
        with self.painter.lock2:
            if self.sel_alg.value == "mrpp_b.py":
                self.painter.showMode = 1
            elif self.sel_alg.value == "rvo2.py":
                self.painter.showMode = 2
        with lock:
            self.syn = True
            for i, j in enumerate(self.cars.keys()):
                self.cars[j].path = paths[i]

    def Shuffle(self, locs, paths):
        #connect current location to the start point of desired path
        matrix = list()
        for index, loc in enumerate(locs):
            matrix.append(list())
            for path in paths:
                matrix[-1].append(math.sqrt(math.pow(loc[0] - path[0][0], 2) + math.pow(loc[1] - path[0][1], 2)))
        m = Munkres()
        indexes = m.compute(matrix)
        newPath = list()
        for row, column in indexes:
            newPath.append(paths[column])
        return newPath

    def Refinement(self, paths):
        """ Make the paths more detailed """
        length = 0
        for path in paths:
            if len(path) > length:
                length = len(path)
        for path in paths:
            while len(path) < length:
                path.append(path[-1])
        total = 0.0
        num = 0
        for path in paths:
            for i in range(len(path) - 1):
                if path[i] != path[i + 1]:
                    total += math.sqrt(math.pow(path[i][0] - path[i + 1][0], 2) + math.pow(path[i][1] - path[i + 1][1], 2))
                    num += 1
        if num == 0:
            return paths
        pts = (int(total / num) + 1) / 4
        if pts == 0:
            return paths
        newPath = [list() for path in paths]
        for index, path in enumerate(paths):
            for i in range(len(path) - 1):
                newPath[index].append(path[i])
                stepX = (path[i + 1][0] - path[i][0]) / pts
                stepY = (path[i + 1][1] - path[i][1]) / pts
                for j in range(int(pts)):
                    newPath[index].append((newPath[index][-1][0] + stepX, newPath[index][-1][1] + stepY))
            newPath[index].append(path[-1])
        return newPath

    def GetRandomArrangement(self):
        # Random locations without colliding, only in simulation mode
        starts = list()
        for i in range(len(self.cars.keys())):
            inserted = False
            while not inserted:
                newX = self.bound.width * random() + self.bound.l
                newY = self.bound.height * random() + self.bound.u
                if self.NoCollision(starts, newX, newY):
                    starts.append((newX, newY, random() * math.pi))
                    inserted = True
                else:
                    pass
        for index, item in enumerate(self.cars.keys()):
            (self.cars[item].x, self.cars[item].y, self.cars[item].theta) = starts[index]
            # print(starts[index])

    def GetRandomGoals(self):
        # Random goals without colliding
        goals = list()
        for i in range(len(self.cars.keys())):
            inserted = False
            while not inserted:
                newX = self.bound.width * random() + self.bound.l
                newY = self.bound.height * random() + self.bound.u
                if self.NoCollision(goals, newX, newY):
                    goals.append((newX, newY))
                    inserted = True
                else:
                    pass
        return goals

    def NoCollision(self, l, x, y):
        # Check if collision occurs
        for obj in l:
            if utils.CheckCollosion(2 * utils.wheelBase, x, y, obj[0], obj[1]):
                return False
        return True

    def Synchronize(self, speeds, paths):
        # Make the overall speed equal to each other
        length = 0
        for i, j in enumerate(paths):
            if len(j) > length:
                length = len(j)
        for i, j in enumerate(paths):
            diff = length - len(j)
            diff = float(12 - diff) / 12.0
            if diff < 0.0:
                diff = 0.0
            vL = speeds[i][0] * math.sqrt(diff)
            vR = speeds[i][1] * math.sqrt(diff)
            speeds[i] = (vL, vR)

    # def setGoal(self,)

    def ReadMouse(self):
        # Get the mouse trajectory
        pt = (0.0, 0.0)
        prev = None
        while True:
            if self.sel_car.value == None:
                pass
            elif self.sel_car.value != prev:
                prev = self.sel_car.value
            else:
                try:
                    pt = self.painter.pointPool.get_nowait()
                    with lock:
                        self.cars[self.sel_car.value].path.append((pt[0] - self.x_offset, pt[1] - self.y_offset))
                        self.syn = False
                        with self.painter.lock2:
                        	self.painter.showMode = 0
                except:
                    pass
            time.sleep(0.01)

    def Draw(self):
        #draw cars' location and paths
        locs = [0 for x in range(len(self.cars.keys()))]
        paths = [0 for x in range(len(self.cars.keys()))]
        while True:            
            with lock:
                for i, j in enumerate(self.cars.keys()):
                    locs[i] = (self.cars[j].x, self.cars[j].y, self.cars[j].theta, self.cars[j].ID)
                    paths[i] = list(self.cars[j].path)
            self.painter.draw(locs, paths)
            time.sleep(0.02)

    def Follow(self):
        locs = [0 for x in range(len(self.cars.keys()))]
        paths = [0 for x in range(len(self.cars.keys()))]
        speeds = [(0.0, 0.0) for x in range(len(self.cars.keys()))]
        vM = 1.0
        flag = True
        self.syn=True
        while flag:            
            with lock:
                syn = self.syn
                
                for i, j in enumerate(self.cars.keys()):
                    locs[i] = (self.cars[j].x, self.cars[j].y, self.cars[j].theta)
                    paths[i] = list(self.cars[j].path)
                    vM = self.sli_v.value / 100.0 * self.vMax
            for i, j in enumerate(locs):
                # j= (x,y,theta)
                speeds[i] = DDR.Calculate(j[0], j[1], j[2], paths[i], vM, utils.wheelBase)
            if syn:
                self.Synchronize(speeds, paths)
            with lock:
                for i, j in enumerate(self.cars.keys()):
                    self.cars[j].lSpeed = speeds[i][0]
                    self.cars[j].rSpeed = speeds[i][1]
                    self.cars[j].path = paths[i]
            time.sleep(0.001)
            with lock:
                flag = self.testflag
                if flag==False:
                    print("Followed!")

    def GetLocation(self):
        with lock:
            KEY = self.cars.keys()
        if self.sim:
            locs = [0 for x in range(len(self.cars.keys()))]
            speeds = [(0.0, 0.0) for x in range(len(self.cars.keys()))]
            run = True
            while True:
                with lock:
                    run = self.runCar
                    for i, j in enumerate(self.cars.keys()):
                        locs[i] = (self.cars[j].x, self.cars[j].y, self.cars[j].theta)
                        speeds[i] = (self.cars[j].lSpeed * self.simSpeed, self.cars[j].rSpeed * self.simSpeed)
                if run:
                    for i, j in enumerate(locs):
                        locs[i] = DDR.Simulate(j[0], j[1], j[2], speeds[i][0], speeds[i][1], utils.wheelBase)
                    with lock:
                        for i, j in enumerate(self.cars.keys()):
                            (self.cars[j].x, self.cars[j].y, self.cars[j].theta) = locs[i]
                else:
                    time.sleep(0.001)        
                time.sleep(0.001)
        else:
            locs = [(0, 0, 0) for x in range(len(self.cars.keys()))]
            while True:
                data = positionZMQSub._get_all_car_position_data()
                # print '_get_all_car_position_data result:'
                # print data
                for index, key in enumerate(KEY):
                    if key not in data:
                        continue
                    if len(data[key]) == 0:
                        continue
                    x0, y0, x1, y1, x2, y2, x3, y3 = data[key].split()
                    x0 = float(x0)
                    x1 = float(x1)
                    x2 = float(x2)
                    x3 = float(x3)
                    y0 = float(y0)
                    y1 = float(y1)
                    y2 = float(y2)
                    y3 = float(y3)
                    # Middle
                    x = (x0 + x1 + x2 + x3) / 4.0
                    y = (y0 + y1 + y2 + y3) / 4.0
                    # Front
                    frontMid_x = (x0 + x1) / 2.0
                    frontMid_y = (y0 + y1) / 2.0
                    # Rare
                    rareMid_x = (x2 + x3) / 2.0
                    rareMid_y = (y2 + y3) / 2.0 
                    theta = DDR.calculateATan(frontMid_x - rareMid_x, frontMid_y - rareMid_y)
                    locs[index] = (x, y, theta)
                with lock:
                    for i, j in enumerate(self.cars.keys()):
                        self.cars[j].x, self.cars[j].y, self.cars[j].theta = locs[i]
                        # print(locs[i])
                time.sleep(0.001)          

    def SendSpeed(self):
        counter =0
        print("send speed")
        sentZeroSpeedOnce=False
        if self.sim:
            return
        else: 
            thrustDict = {}
            with lock:
                for carID,garbage in utils.carInfo:
                    thrustDict[carID]=(0,0)
            run = True

            while True:
                # print thrustDict
                with lock:
                    run = self.runCar
                    for i, (carID, tagID) in enumerate(utils.carInfo):
                        # print carID,tagID
                        # print self.cars
                        idlist = [info[0] for info in utils.carInfo]
                        rights = [self.cars[info[0]].rSpeed * self.simSpeed for info in utils.carInfo]
                        lefts = [self.cars[info[0]].lSpeed * self.simSpeed for info in utils.carInfo]
                        # thrustDict[carID] = (self.cars[tagID].rSpeed * self.simSpeed, self.cars[tagID].lSpeed * self.simSpeed)
                if run:
                    # self.CrazyRadio.CrazyRadioSend(thrustDict)
                    if counter == 50:
                        self.CrazyRadio.CrazyRadioFlush7()
                        counter = 0
                    counter += 1
                    self.CrazyRadio.CrazyRadioSendId(idlist, lefts, rights)
                else:
                    # print("stop all vehicles")
                    if counter == 50:
                        self.CrazyRadio.CrazyRadioFlush7()
                        for i, (carID, tagID) in enumerate(utils.carInfo):
                        # print carID,tagID
                        # print self.cars
                            idlist = [info[0] for info in utils.carInfo]
                            rights = [0 * self.simSpeed for info in utils.carInfo]
                            lefts = [0 * self.simSpeed for info in utils.carInfo]
                        self.CrazyRadio.CrazyRadioSendId(idlist, lefts, rights)
                        counter = 0
                    counter += 1
          
                    self.CrazyRadio.CrazyRadioFlush7()
                time.sleep(0.001)

if __name__ == "__main__":
    app = App()

    app.startApp()
    app.run()