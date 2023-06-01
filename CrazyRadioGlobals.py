# can use channels 0 through 125
channel = 100

# 0xE7E7E7E7E7 is the default
# first byte of address here is the least significant 
address = [0xE7,0xE7,0xE7,0xE7,0xE7]

# payload length can be from 1-32 bytes
# 32 allows for beginning and end confirmation + 10 vehicles
# We can send seperate cmds to control more than 10 vehicles, but note that the fewer the number of levels, the smaller delay would occur
payload_size = 32
payload_level = 2
min_car_id = 1
max_car_id = int((payload_size-2)*payload_level//3)

# packet defaults
beginning_check = "C"
end_check = "M"

# number of times the command should be repeatedly sent
num_cmd_repeats = 1

# if cmd should be printed also when sending out packet
print_cmds = False