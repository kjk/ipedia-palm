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

# tests for functions in arsutils module
class ArsUtils(unittest.TestCase):

    def assertFieldExists(self,response,field):
        if not response.hasField(field):
            print "field '%s' doesn't exist in response" % field
            print "all fields: %s" % string.join(response.getFields(),",")
        self.assertEqual(response.hasField(field),True)

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
        # Get-Random-Definition doesn't require an argument, but we're sending it
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

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
