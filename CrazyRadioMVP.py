# links to documentation
# need to install this backend crazyradio code
# https://github.com/bitcraze/crazyradio-firmware/blob/master/lib/crazyradio.py

# how to flash firmware to new Crazyradio dongle
# linux/mac
# https://github.com/bitcraze/crazyradio-firmware#bitcraze-crazyradio-dongle-
# windows
# first install driver - https://wiki.bitcraze.io/misc:usbwindows
# then flash firmware - https://wiki.bitcraze.io/projects:crazyradio:programming

# Radio/USB Configuration that states defaults
# https://wiki.bitcraze.io/doc:crazyradio:usb:index

# more detailed communication protocls
# https://wiki.bitcraze.io/projects:crazyflie:firmware:comm_protocol

# troubleshooting when the receiver reads a carrier signal on the channel
#   but doesn't pick up the actual packet
# https://github.com/nRF24/RF24/wiki/How-to-diagnose-the-connection%3F
# things to try: 
# check that payload sizes/Car ID's/Channel/Data Rate are matching
# detach chip for flashing from Arduino, upload Arduino sketch again
# in Arduino sketch: set PA level at a higher level
#   ex. radio.setPALevel(RF24_PA_MAX);
# check the battery
# unplug battery from Arduino and reconnect battery to Arduino multiple times
# check connections on motor board/Arduino

import sys
from time import sleep
# copied crazyradio file to same directory
from crazyradio import Crazyradio
from copy import deepcopy
import CrazyRadioGlobals

class CrazyRadioTransmitter(Crazyradio):
    def __init__(self):
        # use the class already written by Crazyradio
        Crazyradio.__init__(self)

        # address that signals are sent to
        self.address = CrazyRadioGlobals.address

        # channel that cars are using
        self.set_channel(CrazyRadioGlobals.channel)

        # different options available, see Crazyradio documentation
        self.set_data_rate(Crazyradio.DR_2MPS)

        # dongle is set to transmit
        self.set_mode(Crazyradio.MODE_PTX)

        # set address that signal is sent to
        self.set_address(self.address)

        # set the number of retries without ack to 0, ignores ack packets
        self.set_arc(0)

        # initialize command variable
        # self.cmd = self._get_empty_cmd()
        self.cmd = self._get_empty_cmd_table()

    # override Crazyradio transmit method with addition of print statement
    def send_cmd(self, level):
        # option to send signal multiple times
        for i in range(CrazyRadioGlobals.num_cmd_repeats):
            Crazyradio.send_packet(self,self.cmd[level])

        # setting to print command that was sent or not
        if CrazyRadioGlobals.print_cmds:
            self._print_sending()

    # stops every car
    def CrazyRadioFlush7(self):
        self.cmd = self._get_empty_cmd_table()
        for i in range(CrazyRadioGlobals.payload_level):    
            self.send_cmd(i)
    
    # stops single level of cars
    def CrazyRadioFlushLevel(self, level):
        for i in range(CrazyRadioGlobals.min_car_id, CrazyRadioGlobals.payload_size-2):    
            if (i % 3 == 1):
                self.cmd[level][i] = level
            else:
                self.cmd[level][i] = 0
        self.send_cmd(level)
    
    # modifies the command for a single vehicle without affecting the 
    # commands of the other vehicles
    # New command sending rules modified by Yu: "Beginning letter, Alevel, Arc, Alc, Blevel, Brc, Blc, ... , Ending letter"
    # The max carIndex for each level is 10; each car contains 3 bytes - first is the level number, second is right speed and third is left speed
    # When meeting any situation that the cars in different level, sending multiple cmds 
    def CrazyRadioSendSingle(self, id, left, right):
        # only allow car ids in the allowed range
        if id < CrazyRadioGlobals.min_car_id or id > CrazyRadioGlobals.max_car_id:
            print( "Car ID must be between", CrazyRadioGlobals.min_car_id, "and ", \
                CrazyRadioGlobals.max_car_id)
            return
        carID = int(id)

        #Configure car level and car index
        carLevel = int((carID-1)/10)
        carIndex = carID - carLevel * 10

        # 0x7F = 011111111
        # 0x80 = 100000000
        self.cmd[carLevel][3*carIndex-2] = int(carLevel) & 0x7F
        self.cmd[carLevel][3*carIndex-1] = int(abs(right*127)) & 0x7F
        self.cmd[carLevel][3*carIndex] = int(abs(left*127)) & 0x7F
        if right < 0:
            self.cmd[carLevel][3*carIndex-1] = self.cmd[3*carIndex-1] | 0x80;
        if left < 0:
            self.cmd[carLevel][3*carIndex] = self.cmd[3*carIndex] | 0x80;
        
        print(self.cmd[carLevel])
        self.send_cmd(carLevel)

    # New function added by Han
    # Send speed control to multiple cars according to their ID
    def CrazyRadioSendId(self, idList, rights, lefts):
        # print rights, lefts
        for index, carID in enumerate(idList):
            # car level, car index
            carLevel = int((carID-1)/10)
            carIndex = carID - carLevel * 10
            # right
            self.cmd[carLevel][3*carIndex] = int(abs(rights[index]*127))&0x7F
            # left
            self.cmd[carLevel][3*carIndex-1] = int(abs(lefts[index]*127))&0x7F
            # right
            if rights[index] < 0:
                self.cmd[carLevel][3*carIndex] = self.cmd[carLevel][3*carIndex] | 0x80;
            # left
            if lefts[index] < 0:
                self.cmd[carLevel][3*carIndex-1] = self.cmd[carLevel][3*carIndex-1] | 0x80;
        # print self.cmd
        for i in range(CrazyRadioGlobals.payload_level):
            self.send_cmd(i)


    # Sending the same wheel thrusts to all vehicles 
    def CrazyRadioSendAll(self, left, right):
        width = int(CrazyRadioGlobals.payload_size)
        for carLevel in range(CrazyRadioGlobals.payload_level):
            for carIndex in range(CrazyRadioGlobals.min_car_id, width-1):
                if ((carIndex % 3) == 1):
                    self.cmd[carLevel][carIndex] = carLevel
                    continue
                self.cmd[carLevel][carIndex] = int(abs(right*127))&0x7F
                self.cmd[carLevel][carIndex] = int(abs(left*127))&0x7F

                if right < 0:
                    self.cmd[carLevel][carIndex] = self.cmd[carLevel][carIndex] | 0x80
                if left < 0:
                    self.cmd[carLevel][carIndex] = self.cmd[carLevel][carIndex] | 0x80

            self.send_cmd(carLevel)
        print(self.cmd)

    # helper methods
    def _get_empty_cmd_table(self):
        width = int(CrazyRadioGlobals.payload_size)
        height = int(CrazyRadioGlobals.payload_level)
        table = [[0 for x in range(width)] for y in range(height)]
        for i in range(height):
            table[i][0] = ord(CrazyRadioGlobals.beginning_check)
            table[i][width-1] = ord(CrazyRadioGlobals.end_check)
            for carIndex in range(1, width-1):
                if ((carIndex % 3) == 1):
                    table[i][carIndex] = i
        # print table
        return table

    def _get_empty_cmd_line(self, level):
        empty_cmd = [ord(CrazyRadioGlobals.beginning_check)]
        for i in range(CrazyRadioGlobals.payload_size-2):
            if (i % 3 == 0):
                empty_cmd.append(level)
            else:
                empty_cmd.append(0)
        empty_cmd.append(ord(CrazyRadioGlobals.end_check))

        print(empty_cmd)
        return empty_cmd

    def _send_car_id_cmd(self):
        car_id_cmd = []
        for i in range(CrazyRadioGlobals.payload_size):
            car_id_cmd.append(ord('Z'))
        print(car_id_cmd)
        Crazyradio.send_packet(self,car_id_cmd)

    def _print_sending(self):
        print("sending", self.cmd, "to", self._return_address_as_str(self.address), \
            "("+str(CrazyRadioGlobals.num_cmd_repeats),"time(s))")


    def _return_address_as_str(self,address):
        add_str = "0x"
        # address list has the least significant byte first
        for digit in list(reversed(address)):
            add_str += str(hex(digit)).replace("0x","").upper()
        return add_str

if __name__ == "__main__":
    # thrusts should be any value between -1 and 1 inclusive 
    # The value between -.2 to .2 is not recommended due to the limitation of motors
    left_thrust = .5
    right_thrust = .5

    radio = CrazyRadioTransmitter()
    # radio._get_empty_cmd_line(10)

    # radio.CrazyRadioSendAll(left_thrust,right_thrust)
    # radio.CrazyRadioSendSingle(2,left_thrust,right_thrust)
    # radio.CrazyRadioSendSingle(3,left_thrust,right_thrust)
    # radio.CrazyRadioSendSingle(4,left_thrust,right_thrust)
    # radio.CrazyRadioSendSingle(5,left_thrust,right_thrust)
    # radio.CrazyRadioSendSingle(15,left_thrust,right_thrust)
    # sleep(1)
    # radio.CrazyRadioSendSingle(1,left_thrust,right_thrust)
    
    # idlist = [5]
    # rights = [-0.5]
    # lefts = [0.5]
    # # rights = [0.5]
    # # lefts = [0]
    # radio.CrazyRadioSendId(idlist, rights, lefts)
    
    # sleep(5)

    idlist = [3]
    rights = [0.5]
    lefts = [0.5]
    # rights = [0.5]
    # lefts = [0]
    radio.CrazyRadioSendId(idlist, rights, lefts)

    sleep(3)
    
    radio.CrazyRadioFlush7()

    radio.close()