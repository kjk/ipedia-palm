# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Implement remote management interface to ipedia so that it's easy to
# control the server without the need to restart it
#
# Usage:
#  -listdbs : list databases on the server
#  -use $dbName : switch to using $dbName on the server

import sys, re, socket, random, arsutils

# server string must be of form "name:port"
g_serverList = ["localhost:9001", "ipedia.arslexis.com:9001"]

g_defaultServerNo = 0 # index within g_serverList

def usageAndExit():
    print "manage.py [-listdbs] [-use dbName]"
    sys.exit(0)

def getServerNamePort():
    srv = g_serverList[g_defaultServerNo]
    print "using server %s" % srv
    (name,port) = srv.split(":")
    port = int(port)
    return (name,port)

def getReqResponse(req):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    (serverName, serverPort) = getServerNamePort()
    sock.connect((serverName,serverPort))
    #print "Connected to server"
    #print "Sending: '%s'" % req
    sock.sendall(req)
    sock.shutdown(1)
    #print "Sent all"
    response = socket_readAll(sock)    
    #print "Received:", response
    sock.close()
    return response

def socket_readAll(sock):
    result = ""
    while True:
        data = sock.recv(10)
        if 0 == len(data):
            break
        #sys.stdout.write(data)
        result += data
    return result

if __name__=="__main__":

    if 1 == len(sys.argv):   # no arguments given
        usageAndExit()        

    if arsutils.fDetectRemoveCmdFlag("-listdbs"):
        resp = getReqResponse("list\n")
        print resp

    dbName = arsutils.getRemoveCmdArg("-use")
    if dbName:
        resp = getReqResponse("use %s\n" % dbName)
        print resp

    if 1 != len(sys.argv):  # unknown arguments given
        usageAndExit()
