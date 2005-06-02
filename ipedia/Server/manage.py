# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Implement remote management interface to ipedia so that it's easy to
# control the server without the need to restart it

import sys, string, re, socket, random, arsutils

# server string must be of form "name:port"
g_serverList = ["localhost:9303", "ipedia.arslexis.com:9303"]

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

g_dbList = {}

class DbInfo:
    def __init__(self,name,lang,articlesCount,fCurrent):
        self.name = name
        self.lang = lang
        self.articlesCount = articlesCount
        self.fCurrent = fCurrent
        self.num = -1

def dbListSortFunc(db1,db2):
    if db1.name == db2.name:
        return 0
    if db1.name > db2.name:
        return 1
    return -1

def displayListOfDatabases():
    global g_dbList
    if 0 == len(g_dbList):
        print "there are no databases"
        return

    print "list of databases:"
    num = 1
    for lang in g_dbList.keys():
        print lang
        dbList = g_dbList[lang]
        dbList.sort(dbListSortFunc)
        for dbInfo in dbList:
            dbInfo.num = num
            num += 1
            if dbInfo.fCurrent:
                print "--> %d) %s having %d articles" % (dbInfo.num, dbInfo.name, dbInfo.articlesCount)
            else:
                print "%d) %s having %d articles" % (dbInfo.num, dbInfo.name, dbInfo.articlesCount)
        print

def readAndDisplayListOfDatabases():
    global g_dbList
    resp = getReqResponse("list\n")
    print resp
    currLang = None
    for line in resp.split("\n"):
        if 0==len(line):
            continue
        if 3==len(line) and ':'==line[2]:
            # this is a language line
            currLang = line[:2]
            continue
        fCurrentDb = False
        if '*' == line[0]:
            fCurrentDb = True
            line = line[1:]
        (dbName,articlesCount) = string.split(line," ")
        articlesCount = int(articlesCount)
        dbInfo = DbInfo(dbName, currLang, articlesCount, fCurrentDb)
        if g_dbList.has_key(currLang):
            g_dbList[currLang].append(dbInfo)
        else:
            g_dbList[currLang] = [dbInfo]
    displayListOfDatabases()

def findDbByNum(num):
    for dbList in g_dbList.values():
        for dbInfo in dbList:
            if dbInfo.num == num:
                return dbInfo
    return None

if __name__=="__main__":
    print "using server %s" % g_serverList[g_defaultServerNo]
    readAndDisplayListOfDatabases()
    while True:
        input = raw_input("Enter db number to use or q to exit: ")
        num = None
        if 'q' == input:
            break
        try:
            num = int(input)
        except:
            print "Invalid input: must be a number"
        if None == num:
            continue

        dbInfo = findDbByNum(num)
        if None == dbInfo:
            print "invalid input: no database with number %d exists" % num
            continue
        if dbInfo.fCurrent:
            print "this is the same database as currently used"
            continue
        dbName = dbInfo.name
        print "chosen db: %s" % dbName
        resp = getReqResponse("use %s\n" % dbName)
        print resp
        #displayListOfDatabases()
        #print
