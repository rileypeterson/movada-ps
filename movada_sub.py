#
#   Weather update client
#   Connects SUB socket to tcp://localhost:5556
#   Collects weather updates and finds avg temp in zipcode
#

import sys
import zmq
import json


#  Socket to talk to server
context = zmq.Context()
socket = context.socket(zmq.SUB)

socket.connect("tcp://localhost:5556")

# Subscribe to zipcode, default is NYC, 10001
root = "https://www.bovada.lv/sports/baseball/"
topics = [""]

for topic in topics:
    socket.subscribe(root + topic)


for update_nbr in range(10000):
    url, data = socket.recv_multipart()
    url = url.decode()
    data = json.loads(data.decode())
    print(url, data)
