#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Copyright: Krzysztof Kowalczyk
# Owner: Andrzej Ciarkowski
#
# Purpose: server component for iPedia
#
# Usage:
#   -silent : will supress most of the messages logged to stdout. TODO: in the
#             future will be replaced with -verbose flag (i.e. we'll be silent
#             by default)
#   -usepsyco : will use psyco, if available
#   -db name  : use database name
#   -listdbs  : list all available ipedia databases
#   -demon    : start in deamon mode

import sys, os, re, random, time, MySQLdb, _mysql_exceptions
import arsutils, iPediaDatabase

from twisted.internet import protocol, reactor
from twisted.protocols import basic

from arsutils import dumpException

try:
    import psyco
    g_fPsycoAvailable = True
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"
    g_fPsycoAvailable = False

g_fDisableRegistrationCheck = True
g_unregisteredLookupsLimit=30
g_unregisteredLookupsDailyLimit=2    

# if True we'll print debugging info
g_fVerbose = None

# Protocol-Version is sent by a client with every request. It future-proofs our
# design (we can change the client-server protocol in newer versions but still
# support older clients using older protocols
# Value: a number representing a protocol version. By convetion we'll start at 1
#   and increase by 1 every time protocol changes
# Response: none
# Currently we only have one protocol of version 1.
protocolVersionField =  "Protocol-Version"
# Client-Info is sent by a client with every request. It's purely informational
# field that enables us to track what kinds of clients/devices are used most.
# Value: version of the client e.g. "Palm 1.0", "Smartphone 0.5" etc.
# Response: none
clientInfoField    =    "Client-Info"
# Transaction-ID is sent by the client and echoed by the server.
# Value: transaction id (arbitrary string)
# Client uses it to match server response with requests
# Response: Transaction-ID with the same value as sent by the client
transactionIdField =    "Transaction-ID"
# We use cookies to tie requests to a given client. Get-Cookie is sent by a
# client if it doesn't have a cookie assigned yet (which should only happen
# right after fresh install/re-install of the client).
# Value: (hopefully unique) device id in our encoded format
# Response: "Cookie" field with value being a string (cookie). TODO: If we know for
#   sure that device id was unique, we issue previously assigned cookie. This
#   prevents using program indefinitely by just reinstalling it after a limit
#   for unregistered version has been reached.
getCookieField =        "Get-Cookie"
# Client sends cookie assigned by the server so that we can tie requests to
# a given client (so that we can do stats). Cookie is generated by the server
# and sent as a result of Get-Cookie.
# Server checks if a cookie has been generated on the server and returns
# Error invalidAuthorization if it wasn't
# Value: cookie
# Response: none
cookieField =           "Cookie"
# Client uses Get-Article to request an article for a given title
# Value: term for which we want the article (e.g. "seattle")
# Response: Results-For or Not-Found or Search-Results
#  With Results-For server also returns Definition and Format-Version
getArticleField =       "Get-Article"
# Client uses Get-Random-Article to get a random article
# Value: none
# Response: Results-For
getRandomField =        "Get-Random-Article"
# Sent by server along with Definition. Describes the format of Definition.
# Allows us to future-proof the design.
# Value: a number representing the format of definition. By convetion, starts
#   with 1 and will be increased by one every time we change the format.
#   Currently we only have one format (Format-Version is 1)
formatVersionField =    "Format-Version"
# Sent by server in response to Get-Article, Get-Random-Article. It's the
# article body text.
# Value: size of definition followed by text of definition itself.
# TODO: change to Article-Body to improve terminology
definitionField =       "Definition"
# Sent by server in response to Get-Article, Get-Random-Article. It's the
# title of the article we're sending. Note: it might be different than title
# requested by Get-Article due to redirects.
# Value: title of the article
# TODO: change to Article-Title to improve termionology
resultsForField =       "Results-For"
# Retruned by the server in response to Get-Article, if the article hasn't been
# found.
notFoundField =         "Not-Found"
# Error is returned by the server if there was an error.
# Value: error number
errorField =            "Error"
# Client sends Registration-Code if registration code has been entered by the
# user and confirmed as valid by Register request.
# Value: registration code
# Response: none
# TODO: use registration code instead of cookie
regCodeField =          "Registration-Code"
searchField =           "Search"
searchResultsField =    "Search-Results"
# Client sends Get-Article-Count to retrieve the number of articles in the database.
# Value: none
# Server response: Article-Count
getArticleCountField =  "Get-Article-Count"
# Server sends Article-Count as a response to Get-Article-Count
# Value: number of articles
articleCountField =     "Article-Count"
# Client sends Get-Database-Time to get the time when the database was last synced
# Value: none
# Response: Database-Time
getDatabaseTimeField =  "Get-Database-Time"
# Server sends Database-Time in response to Get-Database-Time
# Value: date when database was synced, in the format YYYY-MM-DD
databaseTimeField =     "Database-Time"
# Client sends Verify-Registration-Code when it wants to check if a given
# registration code is valid.
# Value: registration code
# Response: Registration-Code-Valid
# Note: this is only to allow us to implement a good registration process on
# the client and doesn't influence our authentication mechanizm. Client sends
# this after user enters reg code on registration code. If server says "reg code
# valid" then client saves it in preferences and sends with all future requests.
# If server says "reg code invalid" then client ask the user to re-enter the code
# or forgets all about it.
# Risk: an attacker can sniff the protocol, figure out the purpose of this request
#   and use it to do a brute-force attack to discover reg codes. A way to fix
#   that would be to encrypt reg code with assymetric cryptography.
#   Cryptographic hash isn't enough because attacker can dissamble the code to
#   figure out the hash function used and do the hashing himself)
verifyRegCodeField =    "Verify-Registration-Code"
# Server sends Registration-Code-Valid in response to Verify-Registration-Code
# Value: 1 - reg code was valid, 0 - reg code was not valid
regCodeValidField =     "Registration-Code-Valid"

# a dict of valid client requests. The value is a boolean saying if a given
# request has arguments (True if has, False if doesn't). We use it to verify
# validity of the request
validClientFields = {
  protocolVersionField   : True,
  clientInfoField        : True,
  transactionIdField     : True,
  cookieField            : True,
  getCookieField         : True,
  getArticleField        : True,
  getRandomField         : False,
  regCodeField           : True,
  searchField            : True,
  getArticleCountField   : False,
  getDatabaseTimeField   : False,
  verifyRegCodeField     : True
 }

DEFINITION_FORMAT_VERSION = "1"
PROTOCOL_VERSION = "1"

requestLinesCountLimit = 20

# this is a special reg code used for testing. Clients should never sent
# such reg code (a reg code format we use for real clients is a 12-digit number)
testValidRegCode = "7432"

class iPediaServerError:
    # return serverFailure if we encountered a problem in code execution
    # (e.g. exception has been thrown that shouldn't have). Usually it means
    # there's a bug in our code
    serverFailure=1
    # unsupportedDevice - not used
    unsupportedDevice=2
    # return invalidAuthorization if the reg code is invalid (?)
    # TODO: change this to invalidRegCode to better reflect what it means
    invalidAuthorization=3
    # request from the client has been malformed. This applies to cases when
    # the request doesn't fit our strict format of request
    malformedRequest=4
    # user has reached lookup limit for unregistered version 
    lookupLimitReached=5
    # returned if request field is not known by the server as something that
    # client might send
    invalidRequest=6
    # return unexpectedRequestArgument if a given request doesn't use arguments
    # but client has sent it
    unexpectedRequestArgument=7
    # return requestArgumentMissing if a given request requres an argument
    # but client didn't send one
    requestArgumentMissing=8
    # return invalidProtocolVersion if the value of protocolVersionField is
    # not something we handle
    invalidProtocolVersion=9
    # return invalidCookie if users sends cookie that hasn't been generated
    # by the server
    invalidCookie=10

lineSeparator =     "\n"

# A format of a request accepted by a server is very strict:
# validClientRequest = validClientField ":" fieldValue? "\n"
# fieldValue = " " string
# validClientField = "Get-Cookie" | "Protocol-Version" etc.
# In other words:
#  - if request has no parameters, then it must be a requestField immediately
#    followed by a colon (":") and a newline ("\n")
#  - if request has parameters, then it must be a requestField immediately
#    followed by a colon (":"), space (" "), arbitrary string which is an argument and newline ("\n")
#
# This function parses the request line from the server and returns a tuple
# (field,value). If request has no parameters, value is None
# If there was an error parsing the line (it doesn't correspond to our strict
# format), field is None
def parseRequestLine(line):
    parts = line.split(":", 1)
    if 1==len(parts):
        # there was no ":" so this is invalid request
        return (None,None)
    field = parts[0]
    value = parts[1]
    if ""==value:
        # the second part is an empty line which means that this is a request
        # without an argument
        return (field, None)
    # this is a request with an argument, so it should begin with a space
    if ' '!=value[0]:
        # it doesn't begin with a space, so invalid
        return (None,None)
    value = value[1:]
    return (field,value)

class iPediaProtocol(basic.LineReceiver):

    def __init__(self):
        self.delimiter='\n'
        self.transactionId=None
        self.deviceInfoToken=None
        self.dbManagement=None
        self.dbArticles=None
        self.error=0
        self.clientVersion=None
        self.protocolVersion=None
        self.requestedTerm=None
        self.term=None
        self.cookie=None
        self.cookieId=None
        self.userId=None
        self.regCode=None
        self.definitionId=None
        self.getRandom=None
        self.linesCount=0
        self.getArticleCount=False
        self.getDatabaseTime=False
        self.searchExpression=None
        self.regCodeToVerify=None

    def getManagementDatabase(self):
        if not self.dbManagement:
            self.dbManagement=self.factory.createManagementConnection()
        return self.dbManagement

    def getArticlesDatabase(self):
        if not self.dbArticles:
            self.dbArticles=self.factory.createArticlesConnection()
        return self.dbArticles

    def outputField(self, name, value=None):
        global g_fVerbose
        if value:
            field = "%s: %s%s" % (name, value, lineSeparator)
        else:
            field = "%s:%s" % (name, lineSeparator)
        self.transport.write(field)
        if g_fVerbose:
            sys.stdout.write(field)

    def outputPayloadField(self, name, payload):
        global g_fVerbose
        self.outputField(name, str(len(payload)))
        self.transport.write(payload)
        self.transport.write(lineSeparator)
        if g_fVerbose:
            print payload
        
    def logRequest(self):
        cursor=None
        try:
            db=self.getManagementDatabase()
            trIdStr='0'
            if self.transactionId:
                trIdStr=str(long(self.transactionId, 16))
            hasGetCookie=0
            if self.deviceInfoToken:
                hasGetCookie=1
            cookieIdStr='NULL'
            if self.cookieId:
                cookieIdStr=str(self.cookieId)
            hasRegister=0
            if self.regCode:
                hasRegister=1
            reqTerm='NULL'
            if self.requestedTerm:
                reqTerm='\''+db.escape_string(self.requestedTerm)+'\''
            defFor='NULL'
            if self.term:
                defFor='\''+db.escape_string(self.term)+'\''
            cursor=db.cursor()
            clientIp=0
            query=("""INSERT INTO requests (client_ip, transaction_id, has_get_cookie_field, cookie_id, has_register_field, requested_term, error, definition_for, request_date) """
                                        """VALUES (%d, %s, %d, %s, %d, %s, %d, %s, now())""" % (clientIp, trIdStr, hasGetCookie, cookieIdStr, hasRegister, reqTerm, self.error, defFor))
            cursor.execute(query)
            cursor.close()
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()

    def finish(self):
        global g_fVerbose
        if self.error:
            self.outputField(errorField, str(self.error))
        self.transport.loseConnection()
        
        if self.dbManagement:
            self.logRequest()
            self.dbManagement.close()
            self.dbManagement=None

        if self.dbArticles:
            self.dbArticles.close()
            self.dbArticles=None

        if g_fVerbose:
            print "--------------------------------------------------------------------------------"
            
    def validateDeviceInfo(self):
        return True

    def createCookie(self, cursor):
        randMax=2**16-1
        while True:
            result=""
            for i in range(8):
                val=random.randint(0, randMax)
                hexVal=hex(val)[2:]
                result+=hexVal
            cursor.execute("""SELECT id FROM cookies WHERE cookie='%s'""" % result)
            row=cursor.fetchone()
            if not row:
                break
        self.cookie=result

    def handleGetCookieRequest(self):
        if not self.validateDeviceInfo():
            self.error=iPediaServerError.unsupportedDevice
            return False

        cursor=None
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()
            cursor.execute("""SELECT id, cookie FROM cookies WHERE device_info_token='%s'""" % db.escape_string(self.deviceInfoToken))
            row=cursor.fetchone()
            if row:
                self.cookieId=row[0]
                self.cookie=row[1]
                cursor.execute("""SELECT id FROM registered_users WHERE cookie_id=%d""" % self.cookieId)
                row=cursor.fetchone()
                if row:
                    self.userId=row[0]
            else:
                self.createCookie(cursor)
                cursor.execute("""INSERT INTO cookies (cookie, device_info_token, issue_date) VALUES ('%s', '%s', now())""" % (self.cookie, db.escape_string(self.deviceInfoToken)))
                self.cookieId=cursor.lastrowid
            cursor.close()                                      
            self.outputField(cookieField, str(self.cookie))
            return True
            
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False;

    def fRegCodeExists(self,regCode):
        if testValidRegCode == regCode:
            return True
        cursor=None
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()
            cursor.execute("""SELECT reg_code FROM reg_codes WHERE reg_code='%s' AND disabled_p='f'""" % db.escape_string(regCode))
            row=cursor.fetchone()
            cursor.close()
            if row:
                return True
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()        
            dumpException(ex)
            self.error=iPediaServerError.serverFailure
        return False;

    def handleVerifyRegistrationCodeRequest(self):
        if not self.cookieId:
            self.error=iPediaServerError.malformedRequest
            return False
        fRegCodeExists = self.fRegCodeExists(self.regCodeToVerify)
        if fRegCodeExists:
            self.outputField(regCodeValidField, "1")
        else:
            self.outputField(regCodeValidField, "0")
        return True

    def handleRegistrationCodeRequest(self):
        # TODO: we should accept *either* cookie or reg code
        if not self.cookieId:
            self.error=iPediaServerError.malformedRequest
            return False

        fRegCodeExists = self.fRegCodeExists(self.regCode)
        if not fRegCodeExists:
            self.error=iPediaServerError.invalidAuthorization
            return False

        return True

        # TODO: figure out what was this supposed to do and do sth. similar
        cursor=None
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()

            if not self.deviceInfoToken:
                cursor.execute("""SELECT device_info_token FROM cookies WHERE id=%d""" % self.cookieId)
                row=cursor.fetchone()
                assert row!=None
                self.deviceInfoToken=row[0]
    
            userName=arsutils.extractHotSyncName(self.deviceInfoToken)
            if not userName:
                userName="[no hotsync name]"

            cursor.execute("""SELECT id, cookie_id FROM registered_users WHERE reg_code='%s'""" % db.escape_string(self.regCode))
            row=cursor.fetchone()
            if row:
                currentCookieId=row[1]
                if currentCookieId==None:
                    self.userId=row[0]
                    cursor.execute("""UPDATE registered_users SET cookie_id=%d, user_name='%s' WHERE id=%d""" % (self.cookieId, db.escape_string(userName), self.userId))
                elif currentCookieId!=self.cookieId:
                    self.error=iPediaServerError.invalidAuthorization
                    cursor.close()
                    return False
                else:
                    self.userId=row[0]
            else:
                self.error=iPediaServerError.invalidAuthorization
                cursor.close()
                return False
            cursor.close()
            return True
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False;
    
    def handleCookieRequest(self):
        if self.cookieId:
            # TODO: (kjk) don't understand the scenario
            return True

        assert not self.cookieId
        cursor=None
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()
            cursor.execute("""SELECT cookies.id AS cookieId, registered_users.id AS userId FROM cookies LEFT JOIN registered_users ON cookies.id=registered_users.cookie_id WHERE cookie='%s'""" % db.escape_string(self.cookie))
            row=cursor.fetchone()
            if row:
                self.cookieId=row[0]
                self.userId=row[1]
                cursor.close()
                return True
            else:
                self.error=iPediaServerError.invalidCookie
                cursor.close()
                return False
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False;
            
    def outputDefinition(self, definition):
        self.outputField(formatVersionField, DEFINITION_FORMAT_VERSION)
        self.outputField(resultsForField, self.term)
        self.outputPayloadField(definitionField, definition)
        
    def preprocessDefinition(self, db, cursor, definition):
#        definition=iPediaDatabase.validateInternalLinks(db, cursor, definition)
        # TODO: move this code somewhere else
        # TODO: perf: we could improve this by marking articles that need this conversion
        # in the database and only do this if it's marked as such. but maybe
        # the overhead of storing/retrieving this info will be bigger than code

        # TODO: maybe we should ignore {{NUMBEROFARTICLES}} or replace it during
        # conversion
        definition=definition.replace("{{NUMBEROFARTICLES}}", str(self.factory.articleCount))
        # speed up trick: don't do the conversion if there can't possibly anything to convert
        if -1 == definition.find("{{CURRENT"):
            return definition
        definition=definition.replace("{{CURRENTMONTH}}", str(int(time.strftime('%m'))));
        definition=definition.replace("{{CURRENTMONTHNAME}}", time.strftime('%B'))
        definition=definition.replace("{{CURRENTMONTHNAMEGEN}}", time.strftime("%B"))
        definition=definition.replace("{{CURRENTDAY}}", str(int(time.strftime("%d"))))
        definition=definition.replace("{{CURRENTDAYNAME}}", time.strftime("%A"))
        definition=definition.replace("{{CURRENTYEAR}}", time.strftime("%Y"))
        definition=definition.replace("{{CURRENTTIME}}", time.strftime("%X"))
        return definition

    def handleDefinitionRequest(self):
        # sys.stderr.write( "'%s' returned from handleDefinitionRequest()\n" % self.requestedTerm )
        cursor=None
        definition=None
        try:
            db=self.getArticlesDatabase()
            cursor=db.cursor()
            idTermDef=iPediaDatabase.findArticle(db, cursor, self.requestedTerm)
            if idTermDef:
                self.definitionId, self.term, definition=idTermDef
            if definition:
                self.outputDefinition(self.preprocessDefinition(db, cursor, definition))
            else:
                self.termList=iPediaDatabase.findFullTextMatches(db, cursor, self.requestedTerm)
                if self.termList:
                    self.outputField(resultsForField, self.requestedTerm)
                    joinedList=""
                    for term in self.termList:
                        joinedList+=(term+'\n')
                    self.outputPayloadField(searchResultsField, joinedList)
                else:
                    self.outputField(notFoundField)
            cursor.close()
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False
        return True
        
    def handleSearchRequest(self):
        cursor=None
        try:
            db=self.getArticlesDatabase()
            cursor=db.cursor()
            self.termList=iPediaDatabase.findFullTextMatches(db, cursor, self.searchExpression)
            if self.termList:
                self.outputField(resultsForField, self.searchExpression)
                joinedList=""
                for term in self.termList:
                    joinedList+=(term+'\n')
                self.outputPayloadField(searchResultsField, joinedList)
            else:
                self.outputField(notFoundField)
            cursor.close()
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False
        return True

    def handleGetRandomRequest(self):
        cursor=None
        definition=None
        try:
            db=self.getArticlesDatabase()
            cursor=db.cursor()
            idTermDef=None
            while not idTermDef:
                idTermDef=iPediaDatabase.findRandomDefinition(db, cursor)
            self.definitionId, self.term, definition=idTermDef
            # sys.stderr.write( "'%s' returned from handleGetRandomRequest()\n" % self.term )

            self.outputDefinition(self.preprocessDefinition(db, cursor, definition))
            cursor.close()
            
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            return False
        return True
        
    def fOverUnregisteredLookupsLimit(self):
        global g_unregisteredLookupsDailyLimit, g_unregisteredLookupsLimit, g_fDisableRegistrationCheck
        if g_fDisableRegistrationCheck:
            return False
        cursor=None
        fOverLimit=False
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()
            assert None==self.userId
            assert None!=self.cookieId
            query="SELECT COUNT(*) FROM requests WHERE NOT (requested_term is NULL) AND cookie_id=%d" % self.cookieId
            cursor.execute(query)
            row=cursor.fetchone()
            assert None!=row
            print "lookups by this cookie: %s" % row[0]
            if row[0]>=g_unregisteredLookupsLimit:
                query="SELECT COUNT(*) FROM requests WHERE NOT (requested_term is NULL) AND cookie_id=%d AND request_date>DATE_SUB(CURDATE(), INTERVAL 1 DAY)" % self.cookieId
                cursor.execute(query)
                row=cursor.fetchone()
                assert None!=row
                if row[0]>=g_unregisteredLookupsDailyLimit:
                    self.error=iPediaServerError.lookupLimitReached
                    fOverLimit=True
            cursor.close()
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            if cursor:
                cursor.close()
            self.error=iPediaServerError.serverFailure
            fOverLimit=True
        return fOverLimit
        
    def answer(self):
        global g_fVerbose
        try:
            if g_fVerbose:
                print "--------------------------------------------------------------------------------"

            if self.transactionId:
                self.outputField(transactionIdField, self.transactionId)
            else:
                return self.finish()

            if self.deviceInfoToken and not self.handleGetCookieRequest():
                return self.finish()
 
            if self.cookie:
                if not self.handleCookieRequest():
                    return self.finish()
            else:
                self.error=iPediaServerError.malformedRequest
                return self.finish()

            if self.error:
                return self.finish()

            assert self.protocolVersion            
            if PROTOCOL_VERSION != self.protocolVersion:
                self.error = iPediaServerError.invalidProtocolVersion
                return self.finish()

            if self.regCode and not self.handleRegistrationCodeRequest():
                # TODO: should I disable the check for Get-Random? We don't want
                # to block Get-Random. On the other hand, reg code, if sent,
                # shouldn't be invalid
                return self.finish()

            if None!=self.regCodeToVerify and not self.handleVerifyRegistrationCodeRequest():
                return self.finish()

            if self.requestedTerm and not self.userId and self.fOverUnregisteredLookupsLimit():
                return self.finish()

            if self.requestedTerm and not self.handleDefinitionRequest():
                return self.finish()

            if self.searchExpression and not self.handleSearchRequest():
                return self.finish();
    
            if self.getRandom and not self.handleGetRandomRequest():
                return self.finish()

            if self.getArticleCount:
                self.outputField(articleCountField, str(self.factory.articleCount))

            if self.getDatabaseTime:
                self.outputField(databaseTimeField, self.factory.dbTime)

        except Exception, ex:
            dumpException(ex)
            self.error=iPediaServerError.serverFailure
 
        self.finish()

    def lineReceived(self, request):
        try:
            ++self.linesCount

            if requestLinesCountLimit==self.linesCount:
                self.error=iPediaServerError.malformedRequest
                return self.answer()

            if request == "":
                # empty line marks end of request
                return self.answer()

            if self.error:
                return self.answer()

            if g_fVerbose:
                print request

            (field,value) = parseRequestLine(request)
            if None == field:
                self.error = iPediaServerError.malformedRequest
                return self.answer()

            if not validClientFields.has_key(field):
                self.error = iPediaServerError.invalidRequest
                return self.answer()                

            fHasArguments = validClientFields[field]
            if fHasArguments:
                if None == value:
                    # expected arguments for this request, but didn't get it
                    self.error = iPediaServerError.requestArgumentMissing
                    return self.answer()
            else:
                if None != value:
                    # got arguments even though the function doesn't expect it
                    self.error = iPediaServerError.unexpectedRequestArgument
                    return self.answer()

            if transactionIdField == field:
                self.transactionId = value
            elif protocolVersionField == field:
                self.protocolVersion = value
            elif clientInfoField == field:
                self.clientVersion = value
            elif getCookieField == field:
                self.deviceInfoToken = value
            elif cookieField == field:
                self.cookie = value
            elif getArticleField == field:
                self.requestedTerm = value
            elif regCodeField == field:
                self.regCode = value
            elif getRandomField == field:
                self.getRandom = True
            elif searchField == field:
                self.searchExpression = value
            elif getArticleCountField == field:
                self.getArticleCount = True
            elif getDatabaseTimeField == field:
                self.getDatabaseTime=True
            elif verifyRegCodeField == field:
                self.regCodeToVerify = value
            else:
                # this shouldn't happend because we've already checked for that
                assert 0
        except Exception, ex:
            dumpException(ex)
            self.error=iPediaServerError.serverFailure
            self.answer()

class iPediaFactory(protocol.ServerFactory):

    def createArticlesConnection(self):
        #print "creating articles connection"
        return MySQLdb.Connect(host=iPediaDatabase.DB_HOST, user=iPediaDatabase.DB_USER, passwd=iPediaDatabase.DB_PWD, db=self.dbName)

    def createManagementConnection(self):
        #print "creating management connection"
        return MySQLdb.Connect(host=iPediaDatabase.DB_HOST, user=iPediaDatabase.DB_USER, passwd=iPediaDatabase.DB_PWD, db=iPediaDatabase.MANAGEMENT_DB)

    def __init__(self, dbName):
        self.changeDatabase(dbName)

    def changeDatabase(self, dbName):
        print "Switching to database %s" % dbName
        self.dbName=dbName
        self.dbTime = dbName[7:]
        db=self.createArticlesConnection()
        cursor=db.cursor()
        cursor.execute("""SELECT COUNT(*), min(id), max(id) FROM articles""")
        row=cursor.fetchone()
        self.articleCount=row[0]
        self.minDefinitionId=row[1]
        self.maxDefinitionId=row[2]
        cursor.execute("""SELECT COUNT(*) FROM redirects""")
        row=cursor.fetchone()
        self.redirectsCount=row[0]
        print "Number of Wikipedia articles: ", self.articleCount
        print "Number of redirects: ", self.redirectsCount
        cursor.close()
        db.close()

    protocol = iPediaProtocol

ipediaRe = re.compile("ipedia_[0-9]{8}", re.I)
def fIpediaDb(dbName):
    """Return True if a given database name is a name of the database with Wikipedia
    articles"""
    if ipediaRe.match(dbName):
        return True
    return False

# returns a dictionary describing all iPedia databases
# dictionary key is database name, the value is number of articles in that database
def getIpediaDbs():
    conn = MySQLdb.Connect(host=iPediaDatabase.DB_HOST, user=iPediaDatabase.DB_USER, passwd=iPediaDatabase.DB_PWD, db='')
    cur = conn.cursor()
    cur.execute("SHOW DATABASES;")
    dbsInfo = {}
    for row in cur.fetchall():
        dbName = row[0]
        if fIpediaDb(dbName):
            cur.execute("""SELECT COUNT(*) FROM %s.articles""" % dbName)
            row=cur.fetchone()
            articleCount=row[0]
            dbsInfo[dbName] = articleCount
    cur.close()
    conn.close()
    return dbsInfo

class iPediaTelnetProtocol(basic.LineReceiver):

    listRe=re.compile(r'\s*list\s*', re.I)
    useDbRe=re.compile(r'\s*use\s+(\w+)\s*', re.I)
    
    def __init__(self):
        self.delimiter='\n'
    
    def listDatabases(self):
        dbsInfo = None
        try:
            dbsInfo = getIpediaDbs()
            dbNames = dbsInfo.keys()
            dbNames.sort()
            for name in dbNames:
                articleCount = dbsInfo[name]
                self.transport.write( "%s (%d articles)\r\n" % (name,articleCount))
            self.transport.write("currently using: %s\r\n" % self.factory.iPediaFactory.dbName)
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            txt = arsutils.exceptionAsStr(ex)
            self.transport.write("exception: %s \r\n" % txt)

    def useDatabase(self, dbName):
        if dbName == self.factory.iPediaFactory.dbName:
            self.transport.write("already using %s database\r\n" % dbName)
            return
        self.transport.write("currently using: %s\r\n" % self.factory.iPediaFactory.dbName)
        dbsInfo = None
        try:
            dbsInfo = getIpediaDbs()
        except _mysql_exceptions.Error, ex:
            dumpException(ex)
            txt = arsutils.exceptionAsStr(ex)
            self.transport.write("exception: %s \r\n" % txt)
            return
        if not dbsInfo.has_key(dbName):
            self.transport.write("Database '%s' doesn't exist\r\n" % dbName)
            self.transport.write("Available databases:\r\n")
            dbNames = dbsInfo.keys()
            dbNames.sort()
            for name in dbNames:
                articleCount = dbsInfo[name]
                self.transport.write( "%s (%d articles)\r\n" % (name,articleCount))
            return
        articleCount = dbsInfo[dbName]
        # don't switch if articleCount is smaller than 100.000 - such database
        # can't be good
        if articleCount < 100000:
            self.transport.write("Database '%s' doesn't have enough articles ('%d', at least 100.000 required)\r\n" % (dbName, articleCount))
            return
        self.factory.iPediaFactory.changeDatabase(dbName)
        self.transport.write("Switched to database '%s'\r\n" % dbName)

    def lineReceived(self, request):
        # print "telnet: '%s'" % request
        if iPediaTelnetProtocol.listRe.match(request):
            self.listDatabases()
            return

        match=iPediaTelnetProtocol.useDbRe.match(request)
        if match:
            self.useDatabase(match.group(1))
            return

        self.transport.loseConnection()
                
    
class iPediaTelnetFactory(protocol.ServerFactory):

    def __init__(self, otherFactory):
        self.iPediaFactory=otherFactory 
    
    protocol=iPediaTelnetProtocol

def usageAndExit():
    print "iPediaServer.py [-demon] [-silent] [-usepsyco] [-listdbs] [-db name]"
    sys.exit(0)        

def main():
    global g_fVerbose, g_fPsycoAvailable
    g_fVerbose=iPediaDatabase.g_fVerbose = True

    fDemon = arsutils.fDetectRemoveCmdFlag("-demon")
    if not fDemon:
        fDemon = arsutils.fDetectRemoveCmdFlag("-daemon")

    if arsutils.fDetectRemoveCmdFlag( "-silent" ):
        g_fVerbose, iPediaDatabase.g_fVerbose = False, False

    fUsePsyco = arsutils.fDetectRemoveCmdFlag("-usepsyco")
    if g_fPsycoAvailable and fUsePsyco:
        print "using psyco"
        psyco.full()

    dbsInfo = getIpediaDbs()
    dbNames = dbsInfo.keys()
    if 0==len(dbNames):
        print "No databases available"
        sys.exit(0)

    dbNames.sort()

    fListDbs = arsutils.fDetectRemoveCmdFlag("-listdbs")
    if fListDbs:
        for name in dbNames:
            print name
        sys.exit(0)

    dbName=arsutils.getRemoveCmdArg("-db")

    if len(sys.argv) != 1:
        usageAndExit()

    if dbName:
        if dbName in dbNames:
            print "Using database '%s'" % dbName
        else:
            print "Database '%s' doesn't exist" % dbName
            print "Available databases:"
            for name in dbNames:
                print "  %s" % name
            sys.exit(0)
    else: 
        dbName=dbNames[-1] # use the latest database
        print "Using database '%s'" % dbName

    if fDemon:
        arsutils.daemonize('/dev/null','/tmp/ipedia.log','/tmp/ipedia.log')

    factory=iPediaFactory(dbName)
    reactor.listenTCP(9000, factory)
    reactor.listenTCP(9001, iPediaTelnetFactory(factory))
    reactor.run()

if __name__ == "__main__":
    main()

