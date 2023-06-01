import sys
import zmq
import time
import threading
from threading import Thread
import copy

import utils

# Dictionary
carPosiDict = dict()

# Create a threading lock for safe access to dictionary
lock = threading.Lock()

def _pull_zmq_data():
    #Connect to zmq publisher 
    context = zmq.Context()
    socket = context.socket(zmq.SUB)


    print("Collecting update from server: tcp://%s:%s" \
        %(utils.zmqPublisherIP, utils.zmqPublisherPort))
    socket.connect ("tcp://%s:%s" %(utils.zmqPublisherIP,
        utils.zmqPublisherPort))
    print("Connected...")

    socket.setsockopt(zmq.SUBSCRIBE, b"")

    #Continuous update of car position, if available
    while True:
        string = socket.recv()
        string=string.decode('utf-8')
        firstSpaceAt = 1
        while string[firstSpaceAt] != " ":
            firstSpaceAt += 1
        carID, rest = string[:firstSpaceAt], string[(firstSpaceAt + 1):]
        with lock:
            carPosiDict[int(carID)] = rest 

# function to sense the tag of all cars at very beginning
def _pull_zmq_data_once():
    #Connect to zmq publisher 
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
  

    print("Collecting update from server: tcp://%s:%s" \
        %(utils.zmqPublisherIP, utils.zmqPublisherPort))
    socket.connect ("tcp://%s:%s" %(utils.zmqPublisherIP,
        utils.zmqPublisherPort))
    print("Connected...")

    socket.setsockopt(zmq.SUBSCRIBE, b"")

    #Continuous update of car position, if available
    flag = True
    count = 0
    while flag:
        string = socket.recv()
        string=string.decode("utf-8") 
        # print("debug string ",string)
        firstSpaceAt = 1
        while string[firstSpaceAt] != " ":
            firstSpaceAt += 1
            #print(string[firstSpaceAt])
        carID, rest = string[:firstSpaceAt], string[(firstSpaceAt + 1):]
        with lock:
            carIDI = (int)(carID) 
            if (carIDI, carIDI) not in utils.carInfo:
                utils.carInfo.append((carIDI, carIDI))
            else:
                count += 1
        if count == 10:
            flag = False
    # print utils.carInfo
    socket.close()
        
def _get_all_car_position_data():
    with lock:
        tempData = copy.deepcopy(carPosiDict)
    return tempData
        
def _get_car_position_data(carID):
    tempData = ""
    with lock:
        if carPosiDict.has_key(carID):
            tempData = carPosiDict[carID]
    return tempData

t = Thread(target = _pull_zmq_data)
t.setDaemon(True)

def _initialize_zmq():
    t.start()
    time.sleep(0.3)

def _stop_zmq():
    return
