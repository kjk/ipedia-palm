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
#   -invalidcookie : send a request with invalid cookie
#   -malformed : send malformed request
import sys, string, re, socket, random, pickle, time
import arsutils
from iPediaServer import *

# server string must be of form "name:port"
g_serverList = ["localhost:9000", "ipedia.arslexis.com:9000"]

g_defaultServerNo = 0 # index within g_serverList

g_cookie = None
g_exampleDeviceInfo = "HS50616C6D204F5320456D756C61746F72:OC70616C6D:OD00000000"

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
    def __init__(self, protocolVer="1", clientVer="0.5"):
        self.fields = []
        self.lines = []

        self.protocolVer   = protocolVer
        self.clientVer     = clientVer
        self.transactionId = "%x" % random.randint(0, 2**16-1)

        self.addField(protocolVersionField, self.protocolVer)
        self.addField(clientInfoField,      self.clientVer)
        self.addField(transactionIdField,   self.transactionId)

    # we expose addLine() so that clients can also create malformed requests
    def addLine(self,line):
        self.lines.append(line)

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
            self.addField(cookieField, getGlobalCookie())
        else:
            self.addField(getCookieField, g_exampleDeviceInfo)

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
# names of fields e.g. like formatVersionField, cookieField and values their values
# returns None if there was an error parsing (the response didn't follow
# the format we expect)
def parseServerResponse(response):
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
            # this is a part of definitionField part of the response
            payloadTxt += fld + "\n"
            payloadLenLeft -= (len(fld) + 1)
            if 0 == payloadLenLeft:
                result[payloadField] = payloadTxt
            #print "*** payloadLenLeft=%d" % payloadLenLeft
            continue
        (field,value) = parseRequestLine(fld)
        if None == field:
            print "'%s' is not a valid request line" % fld
            return None
        if definitionField==field or searchResultsField==field:
            payloadLenLeft = int(value)
            payloadField = field
            #print "*** payloadLenLeft=%d" % payloadLenLeft
        else:
            result[field] = value
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
    if not getGlobalCookie() and rsp.hasField(cookieField):
        print "Found cookie: %s" % rsp.getField(cookieField)
        g_cookie = rsp.getField(cookieField)

def doGetRandomDef(fSilent=False,fDoTiming=False):
    req = getRequestHandleCookie(getRandomField, None)
    timer = arsutils.Timer(fStart=True)
    rsp = Response(req.getString())
    timer.stop()
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId
    assert rsp.hasField(resultsForField)
    assert rsp.hasField(formatVersionField)
    assert rsp.getField(formatVersionField) == CUR_FORMAT_VER
    assert rsp.hasField(definitionField)
    if not fSilent:
        print "# response:"
        print rsp.getText()
    if g_fShowTiming:
        timer.dumpInfo()

def doGetRandomDefNoTiming():
    req = getRequestHandleCookie(getRandomField, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId
    assert rsp.hasField(resultsForField)
    assert rsp.hasField(formatVersionField)
    assert rsp.getField(formatVersionField) == CUR_FORMAT_VER
    assert rsp.hasField(definitionField)

def doGetDef(term):
    print "term: %s" % term
    req = getRequestHandleCookie(getDefinitionField, term)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId
    if rsp.hasField(resultsForField):        
        assert rsp.hasField(formatVersionField)
        assert rsp.getField(formatVersionField) == CUR_FORMAT_VER
        assert rsp.hasField(definitionField)
    else:
        assert rsp.hasField(notFoundField)
    #print "Definition: %s" % rsp.getField(definitionField)

def doGetArticleCount():
    req = getRequestHandleCookie(getArticleCountField, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId
    assert rsp.hasField(articleCountField)
    print "Article count: %s" % rsp.getField(articleCountField)

def doGetDatabaseTime():
    req = getRequestHandleCookie(getDatabaseTimeField, None)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.hasField(databaseTimeField)
    print "Database time: %s" % rsp.getField(databaseTimeField)

def doVerifyRegCode(regCode):
    req = getRequestHandleCookie(verifyRegCodeField, regCode)
    rsp = Response(req.getString())
    handleCookie(rsp)
    assert rsp.hasField(transactionIdField)
    assert rsp.hasField(regCodeValidField)
    print "Reg code valid: %s" % rsp.getField(regCodeValidField)

def doRandomPerf(count):
    timer = arsutils.Timer(fStart=True)
    for i in range(count):
        doGetRandomDefNoTiming()
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
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId

def doInvalidCookie():
    req = Request()
    req.addField(cookieField, "blah")
    print req.getString()
    rsp = Response(req)
    print rsp.getText()
    assert rsp.hasField(transactionIdField)
    assert rsp.getField(transactionIdField) == req.transactionId

def usageAndExit():
    print "client.py [-showtiming] [-perfrandom N] [-getrandom] [-get term] [-articlecount] [-dbtime] [-ping] [-verifyregcode $regCode] [-malformed]"

if __name__=="__main__":
    g_fShowTiming = arsutils.fDetectRemoveCmdFlag("-showtiming")
    printUsedServer()
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
        if arsutils.fDetectRemoveCmdFlag("-invalidcookie"):
            doInvalidCookie()
            sys.exit(0)
        if arsutils.fDetectRemoveCmdFlag("-malformed"):
            doMalformed()
            sys.exit(0)
        usageAndExit()
    finally:
        # make sure that we pickle the state even if we crash
        pickleState()
