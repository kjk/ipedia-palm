# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose:
#  Unit testing for server
#  see http://diveintopython.org/unit_testing/index.html for more info on unittest

import unittest
import client
from client import getRequestHandleCookie, Response

# tests for functions in arsutils module
class ArsUtils(unittest.TestCase):

    def test_Ping(self):
        req = getRequestHandleCookie()
        rsp = Response(req)
        self.assertEqual(rsp.hasField(client.TRANSACTION_ID), True)
        self.assertEqual(rsp.hasField(client.COOKIE), True)
        self.assertEqual(rsp.getField(client.TRANSACTION_ID), req.transactionId)

    def test_UnrecognizedField(self):
        req = getRequestHandleCookie("Foo", "")
        rsp = Response(req)
        self.assertEqual(rsp.hasField(client.ERROR), True)
        self.assertEqual(rsp.hasField(client.TRANSACTION_ID), True)
        self.assertEqual(rsp.hasField(client.COOKIE), True)
        self.assertEqual(rsp.getField(client.TRANSACTION_ID), req.transactionId)

if __name__ == "__main__":
    client.printUsedServer()
    unittest.main()
