from __future__ import print_function
import zmq
import sys
import time


LA = '0'
LB = '1'
RA = '2'
RB = '3'

outhost = str(sys.argv[1])
pubhz = float(str(sys.argv[2]))
pubperiod = 1/pubhz
localhosts = list(sys.argv[3:])

context = zmq.Context()
outsocket = context.socket(zmq.PUB)
outsocket.bind("tcp://127.0.0.1:" + outhost)

insockets = []
for i in range(len(localhosts)):
    insockets.append(context.socket(zmq.SUB))
    insockets[i].setsockopt(zmq.SUBSCRIBE, '')
    insockets[i].setsockopt(zmq.RCVHWM, 1)
    insockets[i].setsockopt(zmq.LINGER, 0)
    insockets[i].connect("tcp://127.0.0.1:" + localhosts[i])

poller = zmq.Poller()
for i in insockets:
    poller.register(i, zmq.POLLIN)

#########################################################
datatypes = ['arm roll', 'arm pitch', 'theta left a', 'ddt theta left a',
            'theta left b', 'ddt theta left b','theta right a', 'ddt theta right a',
            'theta right b', 'ddt theta right b'] # necessary data type
def control(): # control algorithm (return as all strings)
    global t
    kp = 40.0 # set PD gains (10 works)
    kd = 10.0 #(2 works
    arefleft = float(data['arm roll'])
    brefleft = -float(data['arm pitch'])
    arefright = -arefleft
    brefright = -brefleft
    thetalefta = float(data['theta left a']) # Not sure if these orientations are right...
    thetaleftb = float(data['theta left b'])
    thetarighta = float(data['theta right a'])
    thetarightb = float(data['theta right b'])
    omegalefta = float(data['ddt theta left a'])
    omegaleftb = float(data['ddt theta left b'])
    omegarighta = float(data['ddt theta right a'])
    omegarightb = float(data['ddt theta right b'])

    thetaleftaERROR = arefleft - thetalefta
    thetaleftbERROR = brefleft - thetaleftb
    thetarightaERROR = arefright - thetarighta
    thetarightbERROR = brefright - thetarightb
    omegaleftaERROR = 0 - omegalefta
    omegaleftbERROR = 0 - omegaleftb
    omegarightaERROR = 0 - omegarighta
    omegarightbERROR = 0 - omegarightb

    LAcommand = kp*thetaleftaERROR + kd*omegaleftaERROR
    LBcommand = kp*thetaleftbERROR + kd*omegaleftbERROR
    RAcommand = kp*thetarightaERROR + kd*omegarightaERROR
    RBcommand = kp*thetarightbERROR + kd*omegarightbERROR

    com = {LA:str(LAcommand), LB:str(LBcommand), RA:str(RAcommand), RB:str(RBcommand), 'control time': str(time.time() - t0)}
    return com
#########################################################

data = {}
receivedsocks = []
fulldata = False
t0 = time.time()
t = time.time()
command = {LA:'0', LB:'0', RA:'0', RB:'0', 'control time': str(t0)}
print("Controller Initiated")
while True:
    try:
        socks = dict(poller.poll(0)) # poll incoming connections
        receivedsocks = receivedsocks + socks.keys() # make list of subs that have new messages

        for i in insockets: # read in and store any new messages
            if i in socks:
                try:
                    msg = i.recv_json(flags=zmq.NOBLOCK)
                    data.update(msg)
                except zmq.ZMQError as e:
                    pass

        if set(insockets) - set(receivedsocks) == set([]):
            fulldata = True

        if ((fulldata == True) and  # if we've received data on all subs
                    (list(set(datatypes) - set(data.keys())) == []) and
                    (time.time() - t > pubperiod)):
            print (time.time() - t)
            t = time.time()
            command = control() #calculate commands
            data.update(command)
            outsocket.send_json(data) # send 'em
            data = {}
            receivedsocks = []

    except KeyboardInterrupt:
        command = {LA:'0', LB:'0', RA:'0', RB:'0'}# send dead commands, exit
        outsocket.send_json(command)
        sys.exit(0)
