# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose:
#  Unit testing for server
#  see http://diveintopython.org/unit_testing/index.html for more info on unittest

import string,unittest
import client
from client import getRequestHandleCookie, Response, Request, g_exampleDeviceInfo
from iPediaServer import *

invalidRegCodeNumber = "0000"

def searchResultsCount(resultTxt):
    parts = resultTxt.split("\n")
    return len(parts)

# tests for functions in arsutils module
class ArsUtils(unittest.TestCase):

    def assertFieldExists(self,response,field):
        if not response.hasField(field):
            print "\nfield '%s' doesn't exist in response" % field
            print "all fields: %s" % string.join(response.getFields(),",")
            if response.hasField(errorField):
                print "Error: %s" % response.getField(errorField)
        self.assertEqual(response.hasField(field),True)

    def assertFieldDoesntExist(self,response,field):
        if response.hasField(field):
            print "\nfield '%s' exist in response" % field
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

    def getResponse(self,requiredFields=[]):
        self.rsp = Response(self.req)
        self.assertFieldsExist(self.rsp,requiredFields)
        if self.rsp.hasField(transactionIdField):
            self.assertEqual(self.rsp.getField(transactionIdField), self.req.transactionId)

    def assertError(self,expectedError):
        self.assertFieldEqual(self.rsp, errorField, expectedError)

    def test_Ping(self):
        # this is the simplest valid requests - only sends transaction id
        # in response server sends the same transaction id
        self.req = getRequestHandleCookie()
        self.getResponse([cookieField,transactionIdField])

    def test_MalformedRequest(self):
        self.req = getRequestHandleCookie()
        # malformed, because there is no ":"
        self.req.addLine("malformed\n")
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_MissingArgument(self):
        self.req = getRequestHandleCookie()
        # Get-Cookie requires an argument but we're not sending it
        self.req.addField(getCookieField, None)
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.requestArgumentMissing)

    def test_ExtraArgument(self):
        self.req = getRequestHandleCookie()
        # Get-Random-Article doesn't require an argument, but we're sending it
        self.req.addField(getRandomField, "not needed")
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.unexpectedRequestArgument)

    def test_ArgumentCorrectness(self):
        # check if server correctly detects missing arguments/extra arguments
        # for all possible client requests
        # Note: since server uses validClientFields as well to check for this,
        # we might not always detect a bug here
        for (field,fRequiresArguments) in validClientFields.items():
            self.req = getRequestHandleCookie()
            # do the exact opposite of what's expected
            if fRequiresArguments:
                self.req.addField(field, None)
            else:
                self.req.addField(field, "not needed argument")
            self.getResponse([errorField,transactionIdField])
            if fRequiresArguments:
                self.assertError(iPediaServerError.requestArgumentMissing)
            else:
                self.assertError(iPediaServerError.unexpectedRequestArgument)

    def test_UnrecognizedField(self):
        req = getRequestHandleCookie("Foo", "blast")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,cookieField,transactionIdField])
        self.assertFieldEqual(rsp,transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.invalidRequest)

    def test_VerifyValidRegCode(self):
        self.req = getRequestHandleCookie(verifyRegCodeField, testValidRegCode)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,1)

    def test_VerifyInvalidRegCode(self):
        self.req = getRequestHandleCookie(verifyRegCodeField, invalidRegCodeNumber)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,0)

    def test_InvalidProtocolVer(self):
        req = Request(protocolVer="2")
        req.addCookie()
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.invalidProtocolVersion)

    def test_ClientInfoMalformed(self):
        req = Request("1", None)
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[errorField])
        self.assertFieldEqual(rsp,errorField,iPediaServerError.requestArgumentMissing)

    def test_ClientInfoMissing(self):
        req = Request()
        req.clearFields()
        req.addTransactionId()
        req.addField(protocolVersionField,"1")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.malformedRequest)

    def test_ProtocolMissing(self):
        req = Request()
        req.clearFields()
        req.addTransactionId()
        req.addField(clientInfoField,"Python test client 1.0")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[errorField,transactionIdField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,errorField,iPediaServerError.malformedRequest)

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
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,articleTitleField,formatVersionField])
        self.assertFieldsDontExist(rsp,[errorField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)

    def test_GetSeattle(self):
        title = "seattle"
        req = getRequestHandleCookie(getArticleField, title)
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,articleTitleField,formatVersionField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    def test_GetSeattleWithValidRegcode(self):
        title = "seattle"
        req = Request()
        req.addField(getArticleField,title)
        req.addField(regCodeField,testValidRegCode)
        #print req.getString()
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,articleTitleField,formatVersionField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    def test_NotFound(self):
        # Ok, so I can't really guarantee that a given field doesn't exist
        # but this is a really good guess
        req = getRequestHandleCookie(getArticleField, "asdfasdflkj324;l1kjasd13214aasdf341l324")
        rsp = Response(req)
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,notFoundField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)

    def test_SearchSeattle(self):
        searchTerm = "seattle"
        req = getRequestHandleCookie(searchField, searchTerm)
        rsp = Response(req)
        #print rsp.getText()
        self.assertFieldsExist(rsp,[transactionIdField,cookieField,articleTitleField,searchResultsField])
        self.assertFieldEqual(rsp, transactionIdField, req.transactionId)
        self.assertFieldEqual(rsp,articleTitleField,searchTerm)
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

    def test_GetCookieGivesCookie(self):
        self.req = getRequestHandleCookie(cookieField, "I'm a cookie")
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_GetCookieGivesRegCode(self):
        self.req = getRequestHandleCookie(regCodeField, testValidRegCode)
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_DuplicateField(self):
        # TODO: doesn't work
        self.req = getRequestHandleCookie(getArticleCountField, None)
        #self.req.addField(getArticleCountField, None)
        self.getResponse([transactionIdField])
        #self.assertError(iPediaServerError.malformedRequest)

    def test_VerifyRegCodeAsFirstRequest(self):
        # this is what client sends when it sends Verify-Register-Code
        # as the first request ever
        self.req = getRequestHandleCookie(verifyRegCodeField, testValidRegCode)
        self.req.addField(getCookieField, g_exampleDeviceInfo)
        self.req.addField(getArticleCountField, None)
        self.req.addField(getDatabaseTimeField, None)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,1)

    def test_NoCookieAndGetCookie(self):
        # verify that server rejects a query with both cookieField and getCookieField
        self.req = Request()
        self.req.addField(getCookieField,g_exampleDeviceInfo)
        self.getResponse([cookieField,transactionIdField])
        cookie = self.rsp.getField(cookieField)
        self.req = Request()
        self.req.addField(cookieField,cookie)
        self.req.addField(getCookieField,g_exampleDeviceInfo)
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_GetCookieNoDeviceInfo(self):
        # TODO:
        pass

    def test_GetCookieInvalidDeviceInfo(self):
        # TODO:
        pass

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
