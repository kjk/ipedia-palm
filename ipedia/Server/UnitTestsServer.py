# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose:
#  Unit testing for server
#  see http://diveintopython.org/unit_testing/index.html for more info on unittest

import string,unittest
import client
from client import getRequestHandleCookie, Response, Request, g_exampleDeviceInfo, g_uniqueDeviceInfo, g_nonUniqueDeviceInfo
import Fields
from iPediaServer import *

invalidRegCodeNumber = "0000"

def searchResultsCount(resultTxt):
    parts = resultTxt.split("\n")
    return len(parts)

class ServerTests(unittest.TestCase):

    def assertFieldExists(self,response,field):
        if not response.hasField(field):
            print "\nfield '%s' doesn't exist in response" % field
            print "all fields: %s" % string.join(response.getFields(),",")
            if response.hasField(Fields.error):
                print "Error: %s" % response.getField(Fields.error)
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
        if self.rsp.hasField(Fields.transactionId):
            self.assertEqual(self.rsp.getField(Fields.transactionId), self.req.transactionId)

    def assertError(self,expectedError):
        self.assertFieldEqual(self.rsp, Fields.error, expectedError)

    def test_Ping(self):
        # this is the simplest valid requests - only sends transaction id
        # in response server sends the same transaction id
        self.req = getRequestHandleCookie()
        self.getResponse([Fields.cookie,Fields.transactionId])

    def test_MalformedRequest(self):
        self.req = getRequestHandleCookie()
        # malformed, because there is no ":"
        self.req.addLine("malformed\n")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.malformedRequest)

    def test_MissingArgument(self):
        self.req = getRequestHandleCookie()
        # Get-Cookie requires an argument but we're not sending it
        self.req.addField(Fields.getCookie, None)
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.requestArgumentMissing)

    def test_ExtraArgument(self):
        self.req = getRequestHandleCookie()
        # Get-Random-Article doesn't require an argument, but we're sending it
        self.req.addField(Fields.getRandom, "not needed")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.unexpectedRequestArgument)

    def verifyArgument(self, field, fRequiresArguments):
        self.req = getRequestHandleCookie()
        # do the exact opposite of what's expected
        if fRequiresArguments:
            self.req.addField(field, None)
        else:
            self.req.addField(field, "not needed argument")
        self.getResponse([Fields.error,Fields.transactionId])
        if fRequiresArguments:
            self.assertError(ServerErrors.requestArgumentMissing)
        else:
            self.assertError(ServerErrors.unexpectedRequestArgument)
        
    # check if server correctly detects missing extra arguments
    def test_ArgumentsWithoutValue(self):
        fieldsWithoutValue = [Fields.getRandom, Fields.getArticleCount, Fields.getDatabaseTime]
        for field in fieldsWithoutValue:
            self.verifyArgument(field,False)

    # check if server correctly detects missing arguments
    def test_ArgumentsWithValue(self):
        fieldsWithValue = [Fields.protocolVersion, Fields.clientInfo, Fields.transactionId, Fields.cookie, Fields.getCookie, Fields.getArticle, Fields.regCode, Fields.search, Fields.verifyRegCode]
        for field in fieldsWithValue:
            self.verifyArgument(field,True)

    def test_UnrecognizedField(self):
        self.req = getRequestHandleCookie("Foo", "blast")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.invalidRequest)

    def test_VerifyValidRegCode(self):
        self.req = getRequestHandleCookie(Fields.verifyRegCode, testValidRegCode)
        self.getResponse([Fields.cookie,Fields.transactionId,Fields.regCodeValid])
        self.assertFieldEqual(self.rsp,Fields.regCodeValid,1)

    def test_VerifyInvalidRegCode(self):
        self.req = getRequestHandleCookie(Fields.verifyRegCode, invalidRegCodeNumber)
        self.getResponse([Fields.cookie,Fields.transactionId,Fields.regCodeValid])
        self.assertFieldEqual(self.rsp,Fields.regCodeValid,0)

    def test_InvalidProtocolVer(self):
        self.req = Request(protocolVer="2")
        self.req.addCookie()
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.invalidProtocolVersion)

    def test_ClientInfoMalformed(self):
        self.req = Request("1", None)
        self.getResponse([Fields.error])
        self.assertError(ServerErrors.requestArgumentMissing)

    def test_ClientInfoMissing(self):
        self.req = Request()
        self.req.clearFields()
        self.req.addTransactionId()
        self.req.addField(Fields.protocolVersion,"1")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.malformedRequest)

    def test_ProtocolMissing(self):
        self.req = Request()
        self.req.clearFields()
        self.req.addTransactionId()
        self.req.addField(Fields.clientInfo,"Python test client 1.0")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.malformedRequest)

    def test_InvalidCookie(self):
        # this is guaranteed to be an invalid cookie
        self.req = Request()
        self.req.addField(Fields.cookie,"baraba")
        self.getResponse([Fields.error,Fields.transactionId])
        self.assertError(ServerErrors.invalidCookie)

    def test_Random(self):
        self.req = getRequestHandleCookie(Fields.getRandom, None)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.articleTitle,Fields.formatVersion])

    def test_GetSeattle(self):
        title = "seattle"
        self.req = getRequestHandleCookie(Fields.getArticle, title)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.formatVersion,Fields.articleBody,Fields.articleTitle,Fields.reverseLinks])
        self.assertFieldEqual(self.rsp, Fields.formatVersion, DEFINITION_FORMAT_VERSION)

    # TODO: doesn't work yet since we need to have a user with this reg_code
    # we either have to pre-create a test user or register a user from here
    def disable_test_GetSeattleWithValidRegcode(self):
        title = "seattle"
        self.req = Request()
        self.req.addField(Fields.getArticle,title)
        self.req.addField(Fields.regCode,testValidRegCode)
        self.getResponse([Fields.transactionId,Fields.articleBody,Fields.articleTitle,Fields.reverseLinks,Fields.formatVersion])
        self.assertFieldEqual(self.rsp, Fields.formatVersion, DEFINITION_FORMAT_VERSION)

    def test_NotFound(self):
        # Ok, so I can't really guarantee that a article with this title doesn't exist
        # but this is a really good guess
        self.req = getRequestHandleCookie(Fields.getArticle, "asdfasdflkj324;l1kjasd13214aasdf341l324")
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.notFound])

    def test_SearchSeattle(self):
        searchTerm = "seattle"
        self.req = getRequestHandleCookie(Fields.search, searchTerm)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.articleTitle,Fields.searchResults])
        self.assertFieldEqual(self.rsp,Fields.articleTitle,searchTerm)
        count = searchResultsCount(self.rsp.getField(Fields.searchResults))
        #print "search result count: '%d'" % count
        # hard to establish the exact number but 100 should be good (when checked
        # for 7-7-2004 database, it was 201
        self.assertEqual(count > 100,True)

    def test_SearchNotFound(self):
        searchTerm = "asdfasdflkj324;l1kjasd13214aasdf341l324"
        self.req = getRequestHandleCookie(Fields.search, searchTerm)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.notFound])

    def test_GetArticleCount(self):
        self.req = getRequestHandleCookie(Fields.getArticleCount, None)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.articleCount])
        count = int(self.rsp.getField(Fields.articleCount))
        # hard to guarantee to always have 100.000 but should be true given that
        # on 7-7-2004 it was 300.000+
        self.assertEqual(count>100000,True)

    def test_GetDatabaseTime(self):
        self.req = getRequestHandleCookie(Fields.getDatabaseTime, None)
        self.getResponse([Fields.transactionId,Fields.cookie,Fields.databaseTime])
        # date is in format YYYYMMDD
        date = self.rsp.getField(Fields.databaseTime)
        assert 8==len(date)

    def test_GetCookieGivesCookie(self):
        self.req = getRequestHandleCookie(Fields.cookie, "I'm a cookie")
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.malformedRequest)

    def test_GetCookieGivesRegCode(self):
        self.req = getRequestHandleCookie(Fields.regCode, testValidRegCode)
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.malformedRequest)

    def reqWithCookie(self,fieldName,fieldValue):
        self.req = getRequestHandleCookie(fieldName,fieldValue)

    def test_DuplicateField(self):
        self.req = getRequestHandleCookie(Fields.getArticleCount, None)
        self.req.addField(Fields.getArticleCount, None)
        self.getResponse([Fields.transactionId])
        self.assertError(ServerErrors.malformedRequest)

    def test_VerifyRegCodeAsFirstRequest(self):
        # this is what client sends when it sends Verify-Register-Code
        # as the first request ever
        self.req = Request()
        self.req.addField(Fields.getArticleCount, None)
        self.req.addField(Fields.getDatabaseTime, None)
        self.req.addField(Fields.verifyRegCode, testValidRegCode)
        self.req.addField(Fields.getCookie, g_exampleDeviceInfo)
        self.getResponse([Fields.cookie,Fields.transactionId,Fields.regCodeValid])
        self.assertFieldEqual(self.rsp,Fields.regCodeValid,1)

    # verify that server rejects a query with both Fields.cookie and Fields.getCookie
    def test_GetCookieAndCookie(self):
        self.req = Request()
        self.req.addField(Fields.getCookie,g_exampleDeviceInfo)
        self.getResponse([Fields.cookie,Fields.transactionId])
        cookie = self.rsp.getField(Fields.cookie)
        self.req = Request()
        self.req.addField(Fields.cookie,cookie)
        self.req.addField(Fields.getCookie,g_exampleDeviceInfo)
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.malformedRequest)

    # verify that server rejects a query with both Fields.regCode and Fields.getCookie
    def test_GetCookieAndRegCode(self):
        self.req = Request()
        self.req.addField(Fields.getCookie,g_exampleDeviceInfo)
        self.req.addField(Fields.regCode,testValidRegCode)
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.malformedRequest)

    # test that server re-assigns the same cookie if we have a unique device info
    def test_DoubleRegistrationUniqueDeviceInfo(self):
        self.req = Request()
        self.req.addField(Fields.getCookie,g_uniqueDeviceInfo)
        self.getResponse([Fields.transactionId,Fields.cookie])
        cookie = self.rsp.getField(Fields.cookie)
        self.req = Request()
        self.req.addField(Fields.getCookie,g_uniqueDeviceInfo)
        self.getResponse([Fields.transactionId,Fields.cookie])
        cookie2 = self.rsp.getField(Fields.cookie)
        self.assertEqual(cookie,cookie2)

    # test that unregistered user reaches lookup limits
    def test_LookupLimit(self):
        searchTerms = ["brazil","seattle","poland","comedy"]
        # make sure to get a unique cookie, to start over
        self.req = Request()
        self.req.addField(Fields.getCookie,g_nonUniqueDeviceInfo)
        self.getResponse([Fields.transactionId,Fields.cookie])
        cookie = self.rsp.getField(Fields.cookie)
        lookupsToDo = g_unregisteredLookupsLimit+10
        for t in range(lookupsToDo):
            searchTerm = searchTerms[t%len(searchTerms)]
            self.req = Request()
            self.req.addField(Fields.cookie,cookie)
            self.req.addField(Fields.getArticle, searchTerm)
            self.getResponse([Fields.transactionId])
            if self.rsp.hasField(Fields.error):
                self.assertError(ServerErrors.lookupLimitReached)
                self.assertEqual(t,g_unregisteredLookupsLimit)
                return
            else:
                self.assertEqual(True,self.rsp.hasField(Fields.articleTitle))
                self.assertEqual(True,self.rsp.hasField(Fields.articleBody))
                self.assertEqual(True,self.rsp.hasField(Fields.formatVersion))
                self.assertFieldEqual(self.rsp, Fields.formatVersion, DEFINITION_FORMAT_VERSION)
        # didn't find response with an error so far, so there's a bug in the server
        self.assertEqual(True,False)

    def test_InvalidDeviceInfo(self):
        self.req = Request()
        self.req.addField(Fields.getCookie,"PL:blaha")
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.unsupportedDevice)

    def test_InvalidDeviceInfo2(self):
        self.req = Request()
        self.req.addField(Fields.getCookie,"PL:blaha")
        self.req.addField(Fields.getArticle, "seattle")
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.unsupportedDevice)

    def test_InvalidLang(self):
        self.reqWithCookie(Fields.useLang, "invalidLang")
        self.req.addField(Fields.getArticleCount, None)
        self.getResponse([Fields.transactionId,Fields.error])
        self.assertError(ServerErrors.langNotAvailable)

    def test_availableLangs(self):
        self.reqWithCookie(Fields.getAvailableLangs, None)
        self.getResponse([Fields.transactionId, Fields.availableLangs])
        self.assertEqual("en de fr", self.rsp.getField(Fields.availableLangs))

    # verify that a registered user doesn't trigger lookup limits
    def test_RegisteredNoLookupLimits(self):
        # TODO:
        pass

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
