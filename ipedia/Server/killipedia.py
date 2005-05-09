import os, string, arsutils

if __name__ == '__main__':
    pidOwnerList = arsutils.pids("python2.4", "iPediaServer.py")
    user = os.environ["USER"] # who am i
    userId = os.getuid()
    for [pid,owner] in pidOwnerList:
        if str(owner) == str(user) or str(owner) == str(userId):
            cmd = 'kill -9 %s' % pid
            r = os.popen(cmd, 'r')
            
    # TODO: for now also kill those started with older python
    pidOwnerList = arsutils.pids("python", "iPediaServer.py")
    for [pid,owner] in pidOwnerList:
        if str(owner) == str(user) or str(owner) == str(userId):
            cmd = 'kill -9 %s' % pid
            r = os.popen(cmd, 'r')

