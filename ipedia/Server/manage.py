# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Implement remote management interface to ipedia so that it's easy to
# control the server without the need to restart it

import sys, re, socket, random, arsutils

# server string must be of form "name:port"
g_serverList = ["localhost:9001", "ipedia.arslexis.com:9001"]

g_defaultServerNo = 1 # index within g_serverList

def usageAndExit():
    print "manage.py [-listdbs] [-use dbName]"
    sys.exit(0)

def getServerNamePort():
    srv = g_serverList[g_defaultServerNo]
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

g_dbList = []
g_curDbNum = None

def readAndDisplayListOfDatabases():
    global g_dbList, g_curDbNum
    resp = getReqResponse("list\n")
    dbNames = {}
    g_dbList = []
    dbNum = 1
    for db in resp.split("\n"):
        db = db.strip()
        if 0 == len(db):
            continue
        if 0 == db.find("ipedia_"):
            # this is a database name
            (dbName, articleCount, txt) = db.split()
            # print dbName
            articleCount = int(articleCount[1:])
            dbNames[dbName] = (dbNum, articleCount)
            g_dbList.append(dbName)
            dbNum += 1
        else:
            (tmp1, tmp2, curDbName) = db.split()
            assert( tmp1 == "currently" )
            assert( tmp2 == "using:")

    print "list of databases:"
    g_curDbNum = dbNames[curDbName][0]
    for dbName in g_dbList:
        #print db
        (dbNum,articleCount) = dbNames[dbName]
        if g_curDbNum == dbNum:
            print "--> %d) %s having %d articles" % (dbNum, dbName, articleCount)
        else:
            print "%d) %s having %d articles" % (dbNum, dbName, articleCount)


if __name__=="__main__":
    print "using server %s" % g_serverList[g_defaultServerNo]
    readAndDisplayListOfDatabases()
    print
    while True:
        input = raw_input("Enter db number to use or 0 to exit: ")
        num = None
        try:
            num = int(input)
        except:
            print "Invalid input: must be a number"
        if None == num:
            continue
        if 0 == num:
            break
        if num == g_curDbNum:
            print "this is the same database as currently used"
            continue
        if num > len(g_dbList):
            print "invalid input: no database with number %d exists" % num
            continue
        dbName = g_dbList[num-1]
        print "chosen db: %s" % dbName
        resp = getReqResponse("use %s\n" % dbName)
        print resp
        # readAndDisplayListOfDatabases()