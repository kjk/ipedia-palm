# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Emulates client (Palm) application by issuing requests to the server.
# For testing the server.
#
# Usage:
#   -perfrandom N : do a performance test for Get-Random-Definitions by issuing N requests
#   -get term : get and display a definition of term
#   -getrandom
#   -articlecount
import sys, re, socket, random, pickle, time, arsutils

# server string must be of form "name:port"
g_serverList = ["localhost:9000", "ipedia.arslexis.com:9000"]

g_defaultServerNo = 0 # index within g_serverList

g_cookie = None
g_exampleDeviceInfo = "HS50616C6D204F5320456D756C61746F72:OC70616C6D:OD00000000"

TRANSACTION_ID    = "Transaction-ID:"
GET_COOKIE        = "Get-Cookie:"
COOKIE            = "Cookie:"
FORMAT_VER        = "Format-Version:"
RESULTS_FOR       = "Results-For:"
DEFINITION        = "Definition:"
PROTOCOL_VER      = "Protocol-Version:"
CLIENT_VER        = "Client-Version:"
GET_DEF           = "Get-Definition:"
GET_RANDOM        = "Get-Random-Definition:"
GET_ARTICLE_COUNT = "Get-Article-Count:"
ARTICLE_COUNT     = "Article-Count:"
GET_DATABASE_TIME = "Get-Database-Time:"
DATABASE_TIME     = "Database-Time:"
PING              = "Ping:"

g_fShowTiming = None

g_pickleFileName = "client_pickled_data.dat"
def pickleState():
    global g_pickleFileName,g_cookie
    # save all the variables that we want to persist across session on disk
    fo = open(g_pickleFileName, "wb")
    pickle.dump(g_cookie,fo)
    fo.close()

def unpickleState():
    global g_cookie
    # restores all the variables that we want to persist across session from
    # the disk
    try:
        fo = open(g_pickleFileName, "rb")
    except IOError:
        # it's ok to not have the file
        return
    g_cookie = pickle.load(fo)
    fo.close()

def getGlobalCookie():
    global g_cookie
    return g_cookie

def getServerNamePort():
    srv = g_serverList[g_defaultServerNo]
    print "using server %s" % srv
    (name,port) = srv.split(":")
    port = int(port)
    return (name,port)

def socket_readAll(sock):
    result = ""
    while True:
        data = sock.recv(10)
        if 0 == len(data):
            break
        result += data
    return result

def buildLine( field, value):
    return "%s %s\n" % (field,value)

def buildCommonRequestPart():
    protocolVer = "1"
    clientVer = "0.5"
    transactionId = "%x" % random.randint( 0, 2**16-1)

    req  = buildLine(PROTOCOL_VER, protocolVer)
    req += buildLine(CLIENT_VER, clientVer)
    req += buildLine(TRANSACTION_ID, transactionId)
    return req

def buildGetRandomDefinitionRequest():
    req = buildCommonRequestPart()
    if getGlobalCookie():
        req += buildLine(COOKIE, getGlobalCookie())
    else:
        req += buildLine(GET_COOKIE, g_exampleDeviceInfo)
    req += GET_RANDOM + "\n"
    req += "\n"
    return req

def buildGetDefinitionRequest(term):
    req = buildCommonRequestPart()
    if getGlobalCookie():
        req += buildLine(COOKIE, getGlobalCookie())
    else:
        req += buildLine(GET_COOKIE, g_exampleDeviceInfo)
    req += buildLine(GET_DEF, term)
    req += "\n"
    return req
    
def buildGetArticleCountRequest():
    req = buildCommonRequestPart()
    if getGlobalCookie():
        req += buildLine(COOKIE, getGlobalCookie())
    else:
        req += buildLine(GET_COOKIE, g_exampleDeviceInfo)
    req += GET_ARTICLE_COUNT
    req += "\n\n"
    return req

def buildGetDatabaseTimeRequest():
    req = buildCommonRequestPart()
    if getGlobalCookie():
        req += buildLine(COOKIE, getGlobalCookie())
    else:
        req += buildLine(GET_COOKIE, g_exampleDeviceInfo)
    req += GET_DATABASE_TIME
    req += "\n\n"
    return req

# parser server response. Returns a dictionary where keys are the
# names of fields e.g. like FORMAT_VER, COOKIE and values their values
# returns None if there was an error parsing (the response didn't follow
# the format we expect)
def parseServerResponse(response):
    result = {}
    defTxt = ""
    defLenLeft = 0
    fWasEmptyLine = False
    for fld in response.split("\n"):
        if 0==len(fld) and 0==defLenLeft:
            #assert not fWasEmptyLine
            fWasEmptyLine = True
            continue
        #print "line: _%s_" % fld
        if defLenLeft > 0:
            # this is a part of DEFINITION part of the response
            defTxt += fld + "\n"
            defLenLeft -= (len(fld) + 1)
            if 0 == defLenLeft:
                result[DEFINITION] = defTxt
            #print "*** defLenLeft=%d" % defLenLeft
            continue
        keyPos = fld.find(":")
        if keyPos == -1:
            print "*** didn't find ':' in " + fld
            return None
        key = fld[:keyPos+1]
        if fld[keyPos+1] != ' ':
            print "'%s' and not ' ' is at pos %d in '%s'" % (fld[keyPos+1], keyPos+1, fld)
            return None
        value = fld[keyPos+2:]
        #print "key: _%s_" % key
        #print "val: _%s_" % value
        if key == DEFINITION:
            defLenLeft = int(value)
            #print "*** defLenLeft=%d" % defLenLeft
        else:
            result[key] = value
    return result

def getReqResponse(req):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    (serverName, serverPort) = getServerNamePort()
    sock.connect((serverName,serverPort))
    #print "Connected to server"
    #print "Sending:", req
    sock.sendall(req)
    #print "Sent all"
    response = socket_readAll(sock)    
    #print "Received:", response
    sock.close()
    return response

def getDef(term):
    req = buildGetDefinitionRequest(term)
    return getReqResponse(req)

def getRandomDef():
    req = buildGetRandomDefinitionRequest()
    return getReqResponse(req)
    
def getArticleCount():
    req = buildGetArticleCountRequest()
    return getReqResponse(req)

def getDatabaseTime():
    req = buildGetDatabaseTimeRequest()
    return getReqResponse(req)

def doGetDef(term):
    global g_cookie
    defResponse = getDef(term)
    print "term: %s" % term
    print "##### response:"
    print defResponse
    parsedResponse = parseServerResponse(defResponse)
    if not parsedResponse:
        print "FAILURE in parseServerResponse"
        sys.exit(0)
    if not getGlobalCookie() and parsedResponse.has_key(COOKIE):
        print "Found cookie: %s" % parsedResponse[COOKIE]
        g_cookie = parsedResponse[COOKIE]

def doGetRandomDef(fSilent=False,fDoTiming=False):
    global g_cookie, g_fShowTiming
    timer = arsutils.Timer(fStart=True)
    defResponse = getRandomDef()
    timer.stop()
    if not fSilent:
        print "# response:"
        print defResponse
    parsedResponse = parseServerResponse(defResponse)
    if not parsedResponse:
        print "FAILURE in parseServerResponse"
        sys.exit(0)
    if not getGlobalCookie() and parsedResponse.has_key(COOKIE):
        print "Found cookie: %s" % parsedResponse[COOKIE]
        g_cookie = parsedResponse[COOKIE]
    if g_fShowTiming:
        timer.dumpInfo()

def doGetRandomDefNoTiming():
    global g_cookie
    defResponse = getRandomDef()
    parsedResponse = parseServerResponse(defResponse)
    if not parsedResponse:
        print "FAILURE in parseServerResponse"
        sys.exit(0)
    if not getGlobalCookie() and parsedResponse.has_key(COOKIE):
        print "Found cookie: %s" % parsedResponse[COOKIE]
        g_cookie = parsedResponse[COOKIE]

def doGetArticleCount():
    global g_cookie
    defResponse = getArticleCount()
    parsedResponse = parseServerResponse(defResponse)
    if not parsedResponse:
        print "FAILURE in parseServerResponse"
        sys.exit(0)
    if not getGlobalCookie() and parsedResponse.has_key(COOKIE):
        print "Found cookie: %s" % parsedResponse[COOKIE]
        g_cookie = parsedResponse[COOKIE]
    if not parsedResponse.has_key(ARTICLE_COUNT):
        print "FAILURE: no Article-Count field"
        sys.exit(0)
    else:
        print "Article count: ", parsedResponse[ARTICLE_COUNT]

def doGetDatabaseTime():
    global g_cookie
    defResponse = getDatabaseTime()
    parsedResponse = parseServerResponse(defResponse)
    if not parsedResponse:
        print "FAILURE in parseServerResponse"
        sys.exit(0)
    if not getGlobalCookie() and parsedResponse.has_key(COOKIE):
        print "Found cookie: %s" % parsedResponse[COOKIE]
        g_cookie = parsedResponse[COOKIE]
    if not parsedResponse.has_key(DATABASE_TIME):
        print "FAILURE: no %s field" % DATABASE_TIME
        sys.exit(0)
    else:
        print "Database time: ", parsedResponse[DATABASE_TIME]

def doRandomPerf(count):
    timer = arsutils.Timer(fStart=True)
    for i in range(count):
        doGetRandomDefNoTiming()
    timer.stop()
    timer.dumpInfo()
    print "Number of runs: %d" % count

def doPing():
    print "sending PING to the server"
    pingResponse = getReqResponse("%s\n" % PING)
    print "got '%s' from the server" % pingResponse.strip()
    assert pingResponse.strip() == "PONG"

def usageAndExit():
    print "client.py [-showtiming] [-perfrandom N] [-getrandom] [-get term] [-articlecount] [-dbtime] [-ping]"

if __name__=="__main__":
    g_fShowTiming = arsutils.fDetectRemoveCmdFlag("-showtiming")
    try:
        unpickleState()
        if arsutils.fDetectRemoveCmdFlag("-ping"):
            doPing()
            sys.exit(0)
        randomCount = arsutils.getRemoveCmdArgInt("-perfrandom")
        if randomCount != None:
            doRandomPerf(randomCount)
            sys.exit(0)
        if arsutils.fDetectRemoveCmdFlag("-getrandom"):
            doGetRandomDef(False,True)
            sys.exit(0)
        term = arsutils.getRemoveCmdArg("-get")
        if term:
            doGetDef(term)
            sys.exit(0)
        if arsutils.fDetectRemoveCmdFlag("-articlecount"):
            doGetArticleCount()
            sys.exit(0)
        if arsutils.fDetectRemoveCmdFlag("-dbtime"):
            doGetDatabaseTime()
            sys.exit(0)
        usageAndExit()
    finally:
        # make sure that we pickle the state even if we crash
        pickleState()
 
