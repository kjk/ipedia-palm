# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose:
#  Unit testing for server
#  see http://diveintopython.org/unit_testing/index.html for more info on unittest

import string,unittest
import client
from client import getRequestHandleCookie, Response, Request
from iPediaServer import *

invalidRegCode = "0000"

def searchResultsCount(resultTxt):
    parts = resultTxt.split("\n")
    return len(parts)

# tests for functions in arsutils module
class ArsUtils(unittest.TestCase):

    def assertFieldExists(self,response,field):
        if not response.hasField(field):
            print "field '%s' doesn't exist in response" % field
            print "all fields: %s" % string.join(response.getFields(),",")
        self.assertEqual(response.hasField(field),True)

    def assertFieldDoesntExist(self,response,field):
        if response.hasField(field):
            print "field '%s' exist in response" % field
            print "all fields: %s" % string.join(response.getFields(),",")
        self.assertEqual(response.hasField(field),False)

    def assertFieldsDontExist(self,response,fields):
        for field in fields:
            self.assertFieldDoesntExist(response,field)

    def assertFieldsExist(self,response,fields):
        for field in fields:
            self.assertFieldExists(response,field)

    def assertFieldEqual(self,response,field,value):
        # all values returned by server are strings. If value to compare with
        # is int, change it to string. This makes it easier to e.g. compare
        # server errors
        if isinstance(value,int):
            value = "%d" % value
        self.assertEqual(response.getField(field),value)

    def test_Ping(self):
        # this is the simplest valid requests - only sends transaction id
        # in response server sends the same transaction id
        req = getRequestHandleCookie()
        rsp = Response(req)
        self.assertFieldsExist(rsp,[cookieField,transactionIdField])
        self.assertEqual(rsp.getField(transactionIdField), req.transactionId)

    # a format of a request accepted by a server is very strict:
    # validClientRequest = validClientField ":" fieldValue? "\n"
    # fieldValue = " " string
    # validClientField = "Get-Cookie" | "Protocol-Version" etc.
    # In other words:
    #  - if request has no parameters, then it must be a requestField immediately
    #    followed by a colon and a newline
    #  - if request has parameters, then it must be a requestField immediately
    #    followed by a colon, space, arbitrary string which is an argument and newline
    # Tests below test if the server correctly detects and rejects malformed requests
    def test_MalformedRequestOne(self):
        req = getRequestHandleCookie()
        # malformed, because there should be no space
        req.addLine("Get-Cookie: \n")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp,errorField,iPediaServerError.malformedRequest)

    def test_MalformedRequestTwo(self):
        req = getRequestHandleCookie()
        # malformed, because there is no ":"
        req.addLine("malformed\n")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp,errorField,iPediaServerError.malformedRequest)

    def test_MissingArgument(self):
        req = getRequestHandleCookie()
        # Get-Cookie requires an argument but we're not sending it
        req.addField(getCookieField, None)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp,errorField,iPediaServerError.requestArgumentMissing)

    def test_ExtraArgument(self):
        req = getRequestHandleCookie()
        # Get-Random-Article doesn't require an argument, but we're sending it
        req.addField(getRandomField, "not needed")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp,errorField,iPediaServerError.unexpectedRequestArgument)

    def test_ArgumentCorrectness(self):
        # check if server correctly detects missing arguments/extra arguments
        # for all possible client requests
        # Note: since server uses validClientFields as well to check for this,
        # we might not always detect a bug here
        for (field,fRequiresArguments) in validClientFields.items():
            req = getRequestHandleCookie()
            # do the exact opposite of what's expected
            if fRequiresArguments:
                req.addField(field, None)
            else:
                req.addField(field, "not needed argument")
            rsp = Response(req)
            self.assertFieldsExist(rsp,[errorField,transactionIdField])
            if fRequiresArguments:
                self.assertFieldEqual(rsp,errorField,iPediaServerError.requestArgumentMissing)
            else:
                self.assertFieldEqual(rsp,errorField,iPediaServerError.unexpectedRequestArgument)

    def test_UnrecognizedField(self):
        req = getRequestHandleCookie("Foo", "blast")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,cookieField,transactionIdField])
        self.assertFieldEqual(rsp,transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.invalidRequest)

    def test_RegistrationValidRegCode(self):
        req = getRequestHandleCookie(verifyRegCodeField, testValidRegCode)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(rsp,transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,regCodeValidField,1)

    def test_RegistrationInvalidRegCode(self):
        req = getRequestHandleCookie(verifyRegCodeField, invalidRegCode)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(rsp,transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,regCodeValidField,0)

    def test_InvalidProtocolVer(self):
        req = Request(protocolVer="2")
        req.addCookie()
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[errorField,transactionIdField,cookieField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.invalidProtocolVersion)

    def test_InvalidCookie(self):
        # this is guaranteed to be an invalid cookie
        req = Request()
        req.addField(cookieField,"baraba")
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.invalidCookie)

    def test_Random(self):
        req = getRequestHandleCookie(getRandomField, None)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,resultsForField,formatVersionField])
        self.assertFieldsDontExist(rsp,[errorField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)

    def test_GetSeattle(self):
        title = "seattle"
        req = getRequestHandleCookie(getDefinitionField, title)
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,resultsForField,formatVersionField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    # TODO: this one doesn't work
    def disable_test_GetSeattleWithValidRegcode(self):
        title = "seattle"
        req = getRequestHandleCookie(getDefinitionField, title)
        req.addField(regCodeField,testValidRegCode)
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,resultsForField,formatVersionField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    def test_NotFound(self):
        # Ok, so I can't really guarantee that a given field doesn't exist
        # but this is a really good guess
        req = getRequestHandleCookie(getDefinitionField, "asdfasdflkj324;l1kjasd13214aasdf341l324")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,notFoundField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)

    def test_SearchSeattle(self):
        searchTerm = "seattle"
        req = getRequestHandleCookie(searchField, searchTerm)
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,resultsForField,searchResultsField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,resultsForField,searchTerm)
        count = searchResultsCount(rsp.getField(searchResultsField))
        #print "search result count: '%d'" % count
        # hard to establish the exact number but 100 should be good (when checked
        # for 7-7-2004 database, it was 201
        self.assertEqual(count > 100,True)

    def test_SearchNotFound(self):
        searchTerm = "asdfasdflkj324;l1kjasd13214aasdf341l324"
        req = getRequestHandleCookie(searchField, searchTerm)
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,notFoundField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)

    def test_GetArticleCount(self):
        req = getRequestHandleCookie(getArticleCountField, None)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,articleCountField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        count = int(rsp.getField(articleCountField))
        # hard to guarantee to always have 100.000 but should be true given that
        # on 7-7-2004 it was 300.000+
        self.assertEqual(count>100000,True)

    def test_GetDatabaseTime(self):
        req = getRequestHandleCookie(getDatabaseTimeField, None)
        rsp = Response(req)
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,databaseTimeField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        # date is in format YYYYMMDD
        date = rsp.getField(databaseTimeField)
        assert 8==len(date)

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
