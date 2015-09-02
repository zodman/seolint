from  websocket import create_connection
import json
import sys
URL = 'ws://localhost:8888/ws'

d = sys.argv[1]
conn = create_connection(URL)
conn.send(d)
while True:
    try:
        result = conn.recv()
        print "Received '%s'" % result
    except:
        conn.close()
        break
