# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Emulates client (Palm) application by issuing requests to the server.
# For testing the server.
#
# Usage:
#   -perfrandom $n : do a performance test for Get-Random-Article by issuing $n requests
#   -get tittle : get article for a given title
#   -search titel : do a full-text search
#   -getrandom
#   -articlecount
#   -ping : does a ping request (to test if the server is alive)
#   -verifyregcode $regCode : verify registration code
#   -invalidcookie : send a request with invalid cookie
#   -malformed : send malformed request
#   -tcnc : test get cookie no cookie
import sys, string, re, socket, random, pickle, time
import arsutils
import Fields
from iPediaServer import *

# server string must be of form "name:port"
g_serverList = ["localhost:9000", "ipedia.arslexis.com:9000"]

g_defaultServerNo = 0 # index within g_serverList

g_cookie = None
g_exampleDeviceInfo     = "HS50616C6D204F5320456D756C61746F72:OC70616C6D:OD00000000:PL3030"
g_uniqueDeviceInfo      = "PN50616C6D204F5320456D756C61746F72:PL3030"
g_nonUniqueDeviceInfo   = "OC70616C6D:OD00000000:PL3030"

# current version of the article body format returned by the client
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

def printUsedServer():
    srv = g_serverList[g_defaultServerNo]
    print "using server %s" % srv

def getServerNamePort():
    srv = g_serverList[g_defaultServerNo]
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
    def __init__(self, protocolVer="1", clientVer="Python testing client 1.0"):
        self.fields = []
        self.lines = []

        self.addField(Fields.protocolVersion, protocolVer)
        self.addField(Fields.clientInfo,      clientVer)
        self.addTransactionId()

    def addTransactionId(self):
        self.transactionId = "%x" % random.randint(0, 2**16-1)
        self.addField(Fields.transactionId,   self.transactionId)

    # we expose addLine() so that clients can also create malformed requests
    def addLine(self,line):
        self.lines.append(line)

    # we expose clearFields() so that clients can create malformed requests
    # (missing protocol version or transaction id or client info)
    def clearFields(self):
        self.fields = []
        self.lines = []

    def addField(self,fieldName,value):
        assert ':' != fieldName[-1]
        self.fields.append( (fieldName, value) )
        if None==value:
            self.addLine( "%s:\n" % fieldName)
        else:
            self.addLine( "%s: %s\n" % (fieldName,value))

    def getString(self):
        txt = string.join(self.lines , "" )
        txt += "\n"
        return txt

    def addCookie(self):
        if getGlobalCookie():
            self.addField(Fields.cookie, getGlobalCookie())
        else:
            self.addField(Fields.getCookie, g_exampleDeviceInfo)

def getRequestHandleCookie(field=None,value=None):
    r = Request()
    r.addCookie()
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
# names of fields e.g. like Fields.formatVersion, Fields.cookie and values their values
# returns None if there was an error parsing (the response didn't follow
# the format we expect)
def parseServerResponse2(response):
    result = {}
    payloadTxt = ""
    payloadLenLeft = 0
    payloadField = None
    fWasEmptyLine = False
    for fld in response.split("\n"):
        if 0==len(fld) and 0==payloadLenLeft:
            #assert not fWasEmptyLine
            fWasEmptyLine = True
            continue
        #print "line: _%s_" % fld
        if payloadLenLeft > 0:
            # this is a part of payload part of the response
            payloadTxt += fld + "\n"
            payloadLenLeft -= (len(fld) + 1)
            if 0 == payloadLenLeft:
                result[payloadField] = payloadTxt
            #print "*** payloadLenLeft=%d" % payloadLenLeft
            continue
        (field,value) = parseRequestLine(fld)
        if None == field:
            print "'%s' is not a valid request line" % fld
            print "*** payloadLenLeft=%d" % payloadLenLeft
            return None
        if Fields.fPayloadField(field):
            payloadLenLeft = int(value)
            payloadField = field
            #print "*** payloadLenLeft=%d" % payloadLenLeft
        else:
            result[field] = value
    return result

def parseServerResponse(response):
    result = {}
    rest = response
    while True:
        # print "rest: '%s'" % rest
        if 0==len(rest):
            return result
        parts = rest.split("\n",1)
        fld = parts[0]
        rest = None
        if len(parts)>1:
            rest = parts[1]
        if 0==len(fld):
            return result
        (field,value) = parseRequestLine(fld)
        if None == field:
            print "'%s' is not a valid request line" % fld
            return None
        if Fields.fPayloadField(field):
            payloadLen = int(value)
            payload = rest[:payloadLen]
            result[field] = payload
            # print "! found field '%s'" % field
            rest = rest[payloadLen:]
            assert '\n'==rest[0]
            rest = rest[1:]
            if 0==len(rest):
                return result
        else:
            result[field] = value
            # print "! found field '%s'" % field

        if None == rest:
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

    def getFields(self):
        return self.responseDict.keys()

    def hasField(self,field):
        assert ':' != field[-1]
        return self.responseDict.has_key(field)

    def getField(self,field):
        assert ':' != field[-1]
        return self.responseDict[field]

    def getText(self):
        return self.responseTxt

def handleCookie(rsp):
    global g_cookie
    if not getGlobalCookie() and rsp.hasField(Fields.cookie):
        print "Found cookie: %s" % rsp.getField(Fields.cookie)
        g_cookie = rsp.getField(Fields.cookie)

def test_NoCookieAndGetCookie():
    # verify that server rejects a query with both Fields.cookie and Fields.getCookie
    req = Request()
    req.addField(Fields.getCookie,g_exampleDeviceInfo)
    rsp = Response(req.getString())
    print rsp.getText()
    return
    assert rsp.hasField(Fields.transactionId)
    assert rsp.hasField(Fields.cookie)
    cookie = self.rsp.getField(Fields.cookie)
    self.req = Request()
    self.req.addField(Fields.cookie,cookie)
    self.req.addField(Fields.getCookie,g_exampleDeviceInfo)
    self.getResponse([Fields.transactionId,Fields.error])
    self.assertError(iPediaServerError.malformedRequest)

def doGetRandom(fSilent=False,fDoTiming=False):
    req = getRequestHandleCookie(Fields.getRandom, None)
    timer = arsutils.Timer(fStart=True)
    rsp = Response(req.getString())
    timer.stop()
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    assert rsp.hasField(Fields.articleTitle)
    assert rsp.hasField(Fields.articleBody)
    assert rsp.hasField(Fields.reverseLinks)
    assert rsp.hasField(Fields.formatVersion)
    assert rsp.getField(Fields.formatVersion) == CUR_FORMAT_VER
    if not fSilent:
        print "# response:"
        print rsp.getText()
    if g_fShowTiming:
        timer.dumpInfo()

def doGetRandomNoTiming():
    req = getRequestHandleCookie(Fields.getRandom, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    assert rsp.hasField(Fields.articleTitle)
    assert rsp.hasField(Fields.formatVersion)
    assert rsp.getField(Fields.formatVersion) == CUR_FORMAT_VER
    assert rsp.hasField(Fields.articleBody)
    assert rsp.hasField(Fields.reverseLinks)

def doGetDefU(term,fSilent=True):
    print "term: %s" % term
    req = getRequestHandleCookie(Fields.getArticleU, term)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    if not fSilent:
        print "# response:"
        print rsp.getText()
    if rsp.hasField(Fields.articleTitle):        
        assert rsp.hasField(Fields.formatVersion)
        assert rsp.getField(Fields.formatVersion) == CUR_FORMAT_VER
        assert rsp.hasField(Fields.articleBody)
        #assert rsp.hasField(Fields.reverseLinks)
    else:
        assert rsp.hasField(Fields.notFound)
    #print "Definition: %s" % rsp.getField(Fields.articleBody)

def doGetDef(term,fSilent=True):
    print "term: %s" % term
    req = getRequestHandleCookie(Fields.getArticle, term)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    if not fSilent:
        print "# response:"
        print rsp.getText()
    if rsp.hasField(Fields.articleTitle):        
        assert rsp.hasField(Fields.formatVersion)
        assert rsp.getField(Fields.formatVersion) == CUR_FORMAT_VER
        assert rsp.hasField(Fields.articleBody)
        #assert rsp.hasField(Fields.reverseLinks)
    else:
        assert rsp.hasField(Fields.notFound)
    #print "Definition: %s" % rsp.getField(Fields.articleBody)

def doSearch(term):
    print "full-text search for: %s" % term
    req = getRequestHandleCookie(Fields.search, term)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    if rsp.hasField(Fields.articleTitle):        
        assert rsp.hasField(Fields.searchResults)
    else:
        assert rsp.hasField(Fields.notFound)
    #print "Definition: %s" % rsp.getField(Fields.articleBody)

def doGetArticleCount():
    req = getRequestHandleCookie(Fields.getArticleCount, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId
    assert rsp.hasField(Fields.articleCount)
    print "Article count: %s" % rsp.getField(Fields.articleCount)

def doAvailableLangs():
    req = getRequestHandleCookie(Fields.getAvailableLangs, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.hasField(Fields.availableLangs)
    print "Available langs: %s" % rsp.getField(Fields.availableLangs)

def doGetDatabaseTime():
    req = getRequestHandleCookie(Fields.getDatabaseTime, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.hasField(Fields.databaseTime)
    print "Database time: %s" % rsp.getField(Fields.databaseTime)

def doVerifyRegCode(regCode):
    req = getRequestHandleCookie(Fields.verifyRegCode, regCode)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.hasField(Fields.regCodeValid)
    print "Reg code valid: %s" % rsp.getField(Fields.regCodeValid)

def doRandomPerf(count):
    timer = arsutils.Timer(fStart=True)
    for i in range(count):
        doGetRandomNoTiming()
    timer.stop()
    timer.dumpInfo()
    print "Number of runs: %d" % count

def doMalformed():
    req = getRequestHandleCookie()
    # malformed, because there is no ":"
    req.addLine("malformed\n")
    print req.getString()
    rsp = Response(req)
    print rsp.getText()

def doPing():
    req = getRequestHandleCookie()
    rsp = Response(req)
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId

def doInvalidCookie():
    req = Request()
    req.addField(Fields.cookie, "blah")
    print req.getString()
    rsp = Response(req)
    print rsp.getText()
    assert rsp.hasField(Fields.transactionId)
    assert rsp.getField(Fields.transactionId) == req.transactionId

def usageAndExit():
    print "client.py [-showtiming] [-perfrandom N] [-getrandom] [-get term] [-articlecount] [-dbtime] [-ping] [-verifyregcode $regCode] [-malformed]"


argsInfo = {
    "ping" : (0, doPing),
    "perfrandom" : (0, doRandomPerf),
    "getrandom" : (0, doGetRandom),
    "get" : (1, doGetDef),
    "getu" : (1, doGetDefU),
    "search" : (1, doSearch),
    "articlecount" : (0, doGetArticleCount),
    "dbtime" : (0, doGetDatabaseTime),
    "verifyregcode" : (1, doVerifyRegCode),
    "invalidcookie" : (0, doInvalidCookie),
    "malformed" : (0, doMalformed),
    "tcnc" : (0, test_NoCookieAndGetCookie),
    "availablelangs" : (0, doAvailableLangs),
}

def buildUsage():
    global argsInfo
    allArgs = argsInfo.keys()
    allArgs.sort()
    txt = ""
    for arg in allArgs:
        numArgs = argsInfo[arg][0]
        if numArgs > 0:
            txt = "%s [%s $%d]" % (txt, arg, numArgs)
        else:
            txt = "%s [%s]" % (txt, arg)
    return txt

def getIndexSafe(arr, obj):
    pos = None
    try:
        pos = arr.index(obj)
    except:
        pass
    return pos

def usageAndExit():
    print "client.py%s" % buildUsage()

def main():
    pos = None
    for argName in argsInfo.keys():
        pos = getIndexSafe(sys.argv, argName)
        if None != pos:
            break

    if None == pos:
        usageAndExit()
        sys.exit(0)

    numArgs = argsInfo[argName][0]
    func = argsInfo[argName][1]
    if 0 == numArgs:
        func()
    elif 1 == numArgs:
        argOne = sys.argv[pos+1]
        func(argOne)
    elif 2 == numArgs:
        argOne = sys.argv[pos+1]
        argTwo = sys.argv[pos+2]
        func(argOne, argTwo)
    else:
        # not handled yet
        assert(False)

if __name__=="__main__":
    g_fShowTiming = arsutils.fDetectRemoveCmdFlag("-showtiming")
    printUsedServer()
    try:
        unpickleState()
        main()
    finally:
        # make sure that we pickle the state even if we crash
        pickleState()
