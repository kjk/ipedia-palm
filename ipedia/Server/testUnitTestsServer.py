# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose:
#  Unit testing for server
#  see http://diveintopython.org/unit_testing/index.html for more info on unittest

import string,unittest
import client
from client import getRequestHandleCookie, Response, Request, g_exampleDeviceInfo, g_uniqueDeviceInfo, g_nonUniqueDeviceInfo
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

    # check if server correctly detects missing arguments/extra arguments
    # for all possible client requests
    # Note: since server uses validClientFields as well to check for this,
    # we might not always detect a bug here
    def test_ArgumentCorrectness(self):
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
        self.req = getRequestHandleCookie("Foo", "blast")
        self.getResponse([errorField,transactionIdField,cookieField])
        self.assertError(iPediaServerError.invalidRequest)

    def test_VerifyValidRegCode(self):
        self.req = getRequestHandleCookie(verifyRegCodeField, testValidRegCode)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,1)

    def test_VerifyInvalidRegCode(self):
        self.req = getRequestHandleCookie(verifyRegCodeField, invalidRegCodeNumber)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,0)

    def test_InvalidProtocolVer(self):
        self.req = Request(protocolVer="2")
        self.req.addCookie()
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.invalidProtocolVersion)

    def test_ClientInfoMalformed(self):
        self.req = Request("1", None)
        self.getResponse([errorField])
        self.assertError(iPediaServerError.requestArgumentMissing)

    def test_ClientInfoMissing(self):
        self.req = Request()
        self.req.clearFields()
        self.req.addTransactionId()
        self.req.addField(protocolVersionField,"1")
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_ProtocolMissing(self):
        self.req = Request()
        self.req.clearFields()
        self.req.addTransactionId()
        self.req.addField(clientInfoField,"Python test client 1.0")
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_InvalidCookie(self):
        # this is guaranteed to be an invalid cookie
        self.req = Request()
        self.req.addField(cookieField,"baraba")
        self.getResponse([errorField,transactionIdField])
        self.assertError(iPediaServerError.invalidCookie)

    def test_Random(self):
        self.req = getRequestHandleCookie(getRandomField, None)
        self.getResponse([transactionIdField,cookieField,articleTitleField,formatVersionField])

    def test_GetSeattle(self):
        title = "seattle"
        self.req = getRequestHandleCookie(getArticleField, title)
        self.getResponse([transactionIdField,cookieField,formatVersionField,articleBodyField,articleTitleField,reverseLinksField])
        self.assertFieldEqual(self.rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    # TODO: doesn't work yet since we need to have a user with this reg_code
    # we either have to pre-create a test user or register a user from here
    def disable_test_GetSeattleWithValidRegcode(self):
        title = "seattle"
        self.req = Request()
        self.req.addField(getArticleField,title)
        self.req.addField(regCodeField,testValidRegCode)
        self.getResponse([transactionIdField,articleBodyField,articleTitleField,reverseLinksField,formatVersionField])
        self.assertFieldEqual(self.rsp, formatVersionField, DEFINITION_FORMAT_VERSION)

    def test_NotFound(self):
        # Ok, so I can't really guarantee that a given field doesn't exist
        # but this is a really good guess
        self.req = getRequestHandleCookie(getArticleField, "asdfasdflkj324;l1kjasd13214aasdf341l324")
        self.getResponse([transactionIdField,cookieField,notFoundField])

    def test_SearchSeattle(self):
        searchTerm = "seattle"
        self.req = getRequestHandleCookie(searchField, searchTerm)
        self.getResponse([transactionIdField,cookieField,articleTitleField,searchResultsField])
        self.assertFieldEqual(self.rsp,articleTitleField,searchTerm)
        count = searchResultsCount(self.rsp.getField(searchResultsField))
        #print "search result count: '%d'" % count
        # hard to establish the exact number but 100 should be good (when checked
        # for 7-7-2004 database, it was 201
        self.assertEqual(count > 100,True)

    def test_SearchNotFound(self):
        searchTerm = "asdfasdflkj324;l1kjasd13214aasdf341l324"
        self.req = getRequestHandleCookie(searchField, searchTerm)
        self.getResponse([transactionIdField,cookieField,notFoundField])

    def test_GetArticleCount(self):
        self.req = getRequestHandleCookie(getArticleCountField, None)
        self.getResponse([transactionIdField,cookieField,articleCountField])
        count = int(self.rsp.getField(articleCountField))
        # hard to guarantee to always have 100.000 but should be true given that
        # on 7-7-2004 it was 300.000+
        self.assertEqual(count>100000,True)

    def test_GetDatabaseTime(self):
        self.req = getRequestHandleCookie(getDatabaseTimeField, None)
        self.getResponse([transactionIdField,cookieField,databaseTimeField])
        # date is in format YYYYMMDD
        date = self.rsp.getField(databaseTimeField)
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
        self.req = getRequestHandleCookie(getArticleCountField, None)
        self.req.addField(getArticleCountField, None)
        self.getResponse([transactionIdField])
        self.assertError(iPediaServerError.malformedRequest)

    def test_VerifyRegCodeAsFirstRequest(self):
        # this is what client sends when it sends Verify-Register-Code
        # as the first request ever
        self.req = getRequestHandleCookie(verifyRegCodeField, testValidRegCode)
        self.req.addField(getCookieField, g_exampleDeviceInfo)
        self.req.addField(getArticleCountField, None)
        self.req.addField(getDatabaseTimeField, None)
        self.getResponse([cookieField,transactionIdField,regCodeValidField])
        self.assertFieldEqual(self.rsp,regCodeValidField,1)

    # verify that server rejects a query with both cookieField and getCookieField
    def test_GetCookieAndCookie(self):
        self.req = Request()
        self.req.addField(getCookieField,g_exampleDeviceInfo)
        self.getResponse([cookieField,transactionIdField])
        cookie = self.rsp.getField(cookieField)
        self.req = Request()
        self.req.addField(cookieField,cookie)
        self.req.addField(getCookieField,g_exampleDeviceInfo)
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.malformedRequest)

    # verify that server rejects a query with both cookieField and getCookieField
    def test_GetCookieAndRegCode(self):
        self.req = Request()
        self.req.addField(getCookieField,g_exampleDeviceInfo)
        self.req.addField(regCodeField,testValidRegCode)
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.malformedRequest)

    # test that server re-assigns the same cookie if we have a unique device info
    def test_DoubleRegistrationUniqueDeviceInfo(self):
        self.req = Request()
        self.req.addField(getCookieField,g_uniqueDeviceInfo)
        self.getResponse([transactionIdField,cookieField])
        cookie = self.rsp.getField(cookieField)
        self.req = Request()
        self.req.addField(getCookieField,g_uniqueDeviceInfo)
        self.getResponse([transactionIdField,cookieField])
        cookie2 = self.rsp.getField(cookieField)
        self.assertEqual(cookie,cookie2)

    # test that unregistered user reaches lookup limits
    def test_LookupLimit(self):
        searchTerms = ["brazil","seattle","poland","comedy"]
        # make sure to get a unique cookie, to start over
        self.req = Request()
        self.req.addField(getCookieField,g_nonUniqueDeviceInfo)
        self.getResponse([transactionIdField,cookieField])
        cookie = self.rsp.getField(cookieField)
        lookupsToDo = g_unregisteredLookupsLimit+10
        for t in range(lookupsToDo):
            searchTerm = searchTerms[t%len(searchTerms)]
            self.req = Request()
            self.req.addField(cookieField,cookie)
            self.req.addField(getArticleField, searchTerm)
            self.getResponse([transactionIdField])
            if self.rsp.hasField(errorField):
                self.assertError(iPediaServerError.lookupLimitReached)
                self.assertEqual(t,g_unregisteredLookupsLimit)
                return
            else:
                self.assertEqual(True,self.rsp.hasField(articleTitleField))
                self.assertEqual(True,self.rsp.hasField(articleBodyField))
                self.assertEqual(True,self.rsp.hasField(formatVersionField))
                self.assertFieldEqual(self.rsp, formatVersionField, DEFINITION_FORMAT_VERSION)
        # didn't find response with an error so far, so there's a bug in the server
        self.assertEqual(True,False)

    def test_InvalidDeviceInfo(self):
        self.req = Request()
        self.req.addField(getCookieField,"PL:blaha")
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.unsupportedDevice)

    def test_InvalidDeviceInfo2(self):
        self.req = Request()
        self.req.addField(getCookieField,"PL:blaha")
        self.req.addField(getArticleField, "seattle")
        self.getResponse([transactionIdField,errorField])
        self.assertError(iPediaServerError.unsupportedDevice)

    # verify that a registered user doesn't trigger lookup limits
    def test_RegisteredNoLookupLimits(self):
        # TODO:
        pass

    def test_GetCookieInvalidDeviceInfo(self):
        # TODO:
        pass

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
