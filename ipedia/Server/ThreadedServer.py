#from socket import *
import socket
from thread import *
import Queue

requestsQueue = None

REQUEST_TIMEOUT = 120.0

class PeerInfo:
    def __init__(self, addr=None):
        if None == addr:
            self.host = "127.0.0.1"
        else:
            # addr is a tuple (ipAddr, port)
            self.host = str(addr[0])

class _Transport:

    def __init__(self, conn, receiver):
        self.socket, self.address = conn
        self.peer = PeerInfo(self.address)
        self.closed = False
        self.receiver = receiver
        try:
            self.socket.settimeout(REQUEST_TIMEOUT)
        except:
            # not available in python2.2, but that's ok
            pass

    def write(self, data):
        if self.closed:
            return
        try:
            self.socket.sendall(data)
        except Exception, ex:
            self.closed = True
            self.receiver.logException(ex)

    def getPeer(self):
        return self.peer

    def loseConnection(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.socket.shutdown(2)
            self.socket.close()
        except Exception, ex:
            self.receiver.logException(ex)

class LineReceiver:

    def __init__(self):
        self.delimiter = '\n'

    def logException(self, ex):
        print ex

    def lineReceived(self, request):
        pass

    def processConnection(self):
        try:
            request = ""
            start = 0
            while True:
                chunk = self.transport.socket.recv(4096)
                if not chunk:
                    break
                request += chunk

                while True:
                    pos = request.find(self.delimiter, start)
                    if -1 == pos:
                        break
                    line = request[start:pos]
                    start = pos + 1
                    self.lineReceived(line)
                    if self.transport.closed:
                        return
                    if start == len(request):
                        break

            if (not self.transport.closed) and (start != len(request)):
                line = request[start:]
                self.lineReceived(line)
        except Exception, ex:
            self.logException(ex)

def runClientThread(plugClass):
    global requestsQueue
    threadId = get_ident()
    # print "Thread %d started" % threadId
    while True:
        clientSocketAddress = requestsQueue.get()
        plug = plugClass()
        plug.transport = _Transport(clientSocketAddress, plug)
        plug.processConnection()
        if not plug.transport.closed:
            plug.transport.loseConnection()


MAX_WORKER_THREADS_COUNT = 50

def runServer(port, plugClass):
    global requestsQueue
    requestsQueue = Queue.Queue(MAX_WORKER_THREADS_COUNT)
    print ""
    print "Starting %d worker threads..." % MAX_WORKER_THREADS_COUNT
    for i in range(MAX_WORKER_THREADS_COUNT):
        start_new_thread(runClientThread, tuple([plugClass]))

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set timeout so that we can use ctrl-c to stop the server
    try:
        serverSocket.settimeout(2.0)
    except:
        # not available in python2.2, but that's ok
        pass
    try:
        serverSocket.bind(('', port))
        serverSocket.listen(socket.SOMAXCONN)

        while True:
            try:
                clientSocketAddress = serverSocket.accept()
                requestsQueue.put(clientSocketAddress)
            except socket.timeout:
                # it's ok, we just want this so that we can check for
                # keyboard interruption (Ctrl-C)
                pass
    finally:
        serverSocket.close()

def processTelnetConnection(clientSocketAddress, plugClass):
    #print "started processing telnet connection"
    plug = plugClass()
    plug.transport = _Transport(clientSocketAddress, plug)
    plug.processConnection()
    if not plug.transport.closed:
        plug.transport.loseConnection()
    #print "finished processing telnet connection"

def telnetServerThread(port, plugClass):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set timeout so that we can use ctrl-c to stop the server
    try:
        serverSocket.settimeout(2.0)
    except:
        # not available in python2.2, but that's ok
        pass
    try:
        serverSocket.bind(('', port))
        serverSocket.listen(socket.SOMAXCONN)
        print "started telnet server on port %d" % port

        while True:
            try:
                clientSocketAddress = serverSocket.accept()
                processTelnetConnection(clientSocketAddress, plugClass)
            except socket.timeout:
                # it's ok, we just want this so that we can check for
                # keyboard interruption (Ctrl-C)
                pass
    finally:
        serverSocket.close()


# this spawns a separate thread to list for telnet interface/commands
def runTelnetServer(port, plugClass):
    start_new_thread(telnetServerThread, tuple([port, plugClass]))

