# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Emulates client (Palm) application by issuing requests to the server.
# For testing the server.
#
# Usage:
#   -perfrandom $n : do a performance test for Get-Random-Definitions by issuing $n requests
#   -get term : get and display a definition of term
#   -getrandom
#   -articlecount
#   -ping : does a ping request (to test if the server is alive)
#   -verifyregcode $regCode : verify registration code
import sys, string, re, socket, random, pickle, time, arsutils

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
VERIFY_REG_CODE   = "Verify-Registration-Code:"
REG_CODE_VALID    = "Registration-Code-Valid:"

# current version of the definition format returned by the client
CUR_FORMAT_VER = "1"

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

class Request:
    def __init__(self):
        self.fields = []

        self.protocolVer   = "1"
        self.clientVer     = "0.5"
        self.transactionId = "%x" % random.randint(0, 2**16-1)

        self.addField(PROTOCOL_VER,   self.protocolVer)
        self.addField(CLIENT_VER,     self.clientVer)
        self.addField(TRANSACTION_ID, self.transactionId)

    def addField(self,fieldName,value):
        self.fields.append( (fieldName, value) )

    def getString(self):
        lines = ["%s %s\n" % (field,value) for (field,value) in self.fields]
        txt = string.join(lines , "" )
        txt += "\n"
        return txt

def getRequestHandleCookie(field=None,value=None):
    r = Request()
    if getGlobalCookie():
        r.addField(COOKIE, getGlobalCookie())
    else:
        r.addField(GET_COOKIE, g_exampleDeviceInfo)
    if field!=None:
        r.addField(field,value)
    return r

def getResponseFromServer(req):
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

class Response:
    def __init__(self,request):
        # request can be either a string or class Request
        assert request
        if isinstance(request, Request):
            self.txt = request.getString()
        else:
            self.txt = request
        self.responseTxt = getResponseFromServer(self.txt)
        self.responseDict = parseServerResponse(self.responseTxt)
        if None == self.responseDict:
            # TODO: throw an exception
            print "FAILURE in parseServerResponse"
            sys.exit(0)

    def hasField(self,field):
        return self.responseDict.has_key(field)

    def getField(self,field):
        return self.responseDict[field]

    def getText(self):
        return self.responseTxt

def handleCookie(rsp):
    global g_cookie
    if not getGlobalCookie() and rsp.hasField(COOKIE):
        print "Found cookie: %s" % rsp.getField(COOKIE)
        g_cookie = rsp.getField(COOKIE)

def doGetRandomDef(fSilent=False,fDoTiming=False):
    req = getRequestHandleCookie(GET_RANDOM, "")
    timer = arsutils.Timer(fStart=True)
    rsp = Response(req.getString())
    timer.stop()
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(RESULTS_FOR)
    assert rsp.hasField(FORMAT_VER)
    assert rsp.getField(FORMAT_VER) == CUR_FORMAT_VER
    assert rsp.hasField(DEFINITION)
    if not fSilent:
        print "# response:"
        print rsp.getText()
    if g_fShowTiming:
        timer.dumpInfo()

def doGetRandomDefNoTiming():
    req = getRequestHandleCookie(GET_RANDOM, "")
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(RESULTS_FOR)
    assert rsp.hasField(FORMAT_VER)
    assert rsp.getField(FORMAT_VER) == CUR_FORMAT_VER
    assert rsp.hasField(DEFINITION)

def doGetDef(term):
    print "term: %s" % term
    req = getRequestHandleCookie(GET_DEF, term)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(RESULTS_FOR)
    assert rsp.hasField(FORMAT_VER)
    assert rsp.getField(FORMAT_VER) == CUR_FORMAT_VER
    assert rsp.hasField(DEFINITION)
    #print "Definition: %s" % rsp.getField(DEFINITION)

def doGetArticleCount():
    req = getRequestHandleCookie(GET_ARTICLE_COUNT, "")
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(ARTICLE_COUNT)
    print "Article count: %s" % rsp.getField(ARTICLE_COUNT)

def doGetDatabaseTime():
    req = getRequestHandleCookie(GET_DATABASE_TIME, "")
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(DATABASE_TIME)
    print "Database time: %s" % rsp.getField(DATABASE_TIME)

def doVerifyRegCode(regCode):
    req = getRequestHandleCookie(VERIFY_REG_CODE, regCode)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(REG_CODE_VALID)
    print "Reg code valid: %s" % rsp.getField(REG_CODE_VALID)

def doRandomPerf(count):
    timer = arsutils.Timer(fStart=True)
    for i in range(count):
        doGetRandomDefNoTiming()
    timer.stop()
    timer.dumpInfo()
    print "Number of runs: %d" % count

def doPing():
    req = getRequestHandleCookie()
    rsp = Response(req)
    assert rsp.hasField(TRANSACTION_ID)
    assert rsp.hasField(COOKIE)
    assert rsp.getField(TRANSACTION_ID) == req.transactionId

def usageAndExit():
    print "client.py [-showtiming] [-perfrandom N] [-getrandom] [-get term] [-articlecount] [-dbtime] [-ping] [-verifyregcode $regCode]"

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
        regCode = arsutils.getRemoveCmdArg("-verifyregcode")
        if regCode:
            doVerifyRegCode(regCode)
            sys.exit(0)
        usageAndExit()
    finally:
        # make sure that we pickle the state even if we crash
        pickleState()
