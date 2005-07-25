# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Collect routines frequently used in other places

import os,sys,time,string,binascii,traceback

# which diff tool to use. AraxisMerge is the best, imo (shows character-level
# diffs, not only line-level)
(DIFF_WINDIFF,DIFF_ARAXIS, DIFF_WINMERGE) = range(3)

g_DiffTool = DIFF_WINDIFF
#g_DiffTool = DIFF_ARAXIS
#g_DiffTool = DIFF_WINMERGE

# windiff doesn't do that well with long lines so I break long lines into
# a paragraph. It does make the text uglier but for our purpose we don't
# really care
# if using a better diff (e.g. Araxis Merge) program, this could be set to False
# in which case we don't reformat the text
g_reformatLongLines = True

if g_DiffTool == DIFF_ARAXIS:
    g_reformatLongLines = False

def fIsBzipFile(inFileName):
    if len(inFileName)>4 and ".bz2" == inFileName[-4:]:
        return True
    return False

def fIsGzipFile(inFileName):
    if len(inFileName)>3 and ".gz" == inFileName[-3:]:
        return True
    return False

def fDetectRemoveCmdFlag(flag):
    fFlagPresent = False
    try:
        pos = sys.argv.index(flag)
        fFlagPresent = True
        sys.argv[pos:pos+1] = []
    except:
        pass
    return fFlagPresent

# given argument name in argName, tries to return argument value
# in command line args and removes those entries from sys.argv
# return None if not found
def getRemoveCmdArg(argName):
    argVal = None
    try:
        pos = sys.argv.index(argName)
        argVal = sys.argv[pos+1]
        sys.argv[pos:pos+2] = []
    except:
        pass
    return argVal

def getRemoveCmdArgInt(argName):
    argVal = getRemoveCmdArg(argName)
    if argVal:
        argVal = int(argVal)
    return argVal

def normalizeNewlines(txt):
    txt = txt.strip()  
    crlf = chr(13)+chr(10)
    lf = chr(10)
    return txt.replace(crlf, lf)

# given time as a floating point number of seconds, return a text formatted
# time that shows time in minutes/seconds
def timeInSecsToTxt(seconds):
    minutes = int(seconds / 60.0)
    seconds = seconds - (float(minutes) * 60.0)
    assert seconds <= 60.0 # TODO: is it safe due to 

    if minutes > 0:
        txt = "%d min %.2f secs" % (minutes, seconds)
    else:
        txt = "%.2f secs" % seconds
    return txt

# Timer measures time between start() and stop() calls
# it uses both time.clock() and time.time() calls
# time.clock() are more accurate (precision is in 1/1000 sec. on Windows)
# but I suspect it might overflow, so it's not good for timing long-running
# processes (I was getting negative values when using just time.clock())
# So I use time.time() if I suspect that time.clock() overflew
class Timer:

    def __init__(self,fStart=False):
        self.startTime = None
        self.endTime = None
        self.startLowResTime = None
        self.endLowResTime = None
        if fStart:
            self.start()

    def start(self):
        self.startTime = time.clock()
        self.startLowResTime = time.time()

    def stop(self):
        self.endTime = time.clock()
        self.endLowResTime = time.time()

    def getDurationInSecs(self):
        dur = self.endTime - self.startTime
        durLowRes = self.endLowResTime - self.startLowResTime
        if dur < 0:
            return durLowRes
        if durLowRes > dur:
            return durLowRes
        return dur

    def dumpInfo(self,txt=None):
        dur = self.getDurationInSecs()
        if None == txt:
            durTxt = timeInSecsToTxt(dur)
        else:
            durTxt = "%s%s" % (txt, timeInSecsToTxt(dur))
        sys.stderr.write(durTxt)

def fFileExists(filePath):
    try:
        st = os.stat(filePath)
    except OSError:
        # TODO: should check that Errno is 2
        return False
    return True

def fExecutedCorrectly(stderrTxt):
    if -1 == stderrTxt.find("is not recognized"):
        return True
    else:
        return False

def fFinishProcess(proc,fPrintStdout=False):
    res_stdout = proc.stdout.read()
    res_stderr = proc.stderr.read()
    status = proc.wait()
    if fPrintStdout:
        print res_stdout
        print res_stderr
    return fExecutedCorrectly(res_stderr)

def diffWithWindiff(orig,converted):
    try:
        import process
    except:
        print "requires process module (http://starship.python.net/crew/tmick/)"
        sys.exit(0)
    p = process.ProcessOpen(["windiff.exe", orig, converted])
    fFinishProcess(p,True)

def diffWithAraxis(orig,converted):
    try:
        import process
    except:
        print "requires process module (http://starship.python.net/crew/tmick/)"
        sys.exit(0)
    p = process.ProcessOpen(["C:\Program Files\Araxis Merge 2001\compare.exe", orig, converted])
    fFinishProcess(p,True)

def diffWithWinMerge(orig,converted):
    try:
        import process
    except:
        print "requires process module (http://starship.python.net/crew/tmick/)"
        sys.exit(0)
    p = process.ProcessOpen(["c:\Program Files\WinMerge\WinMergeU.exe", orig, converted])
    fFinishProcess(p,True)

def fStringPrintable(txt):
    for c in txt:
        if -1 == string.printable.find(c):
            return False
    return True

def toHexIfNeeded(txt):
    if fStringPrintable(txt):
        return txt
    else:
        return "0x" + binascii.hexlify(txt)

# code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/134571
def justify_line(line, width):
    """Stretch a line to width by filling in spaces at word gaps.

    The gaps are picked randomly one-after-another, before it starts
    over again.

    """
    i = []
    while 1:
        # line not long enough already?
        if len(' '.join(line)) < width:
            if not i:
                # index list is exhausted
                # get list if indices excluding last word
                i = range(max(1, len(line)-1))
                # and shuffle it
                random.shuffle(i)
            # append space to a random word and remove its index
            line[i.pop(0)] += ' '
        else:
            # line has reached specified width or wider
            return ' '.join(line)

def fill_paragraphs(text, width=80, justify=0):
    """Split a text into paragraphs and wrap them to width linelength.

    Optionally justify the paragraphs (i.e. stretch lines to fill width).

    Inter-word space is reduced to one space character and paragraphs are
    always separated by two newlines. Indention is currently also lost.

    """
    # split taxt into paragraphs at occurences of two or more newlines
    paragraphs = re.split(r'\n\n+', text)
    for i in range(len(paragraphs)):
        # split paragraphs into a list of words
        words = paragraphs[i].strip().split()
        line = []; new_par = []
        while 1:
           if words:
               if len(' '.join(line + [words[0]])) > width and line:
                   # the line is already long enough -> add it to paragraph
                   if justify:
                       # stretch line to fill width
                       new_par.append(justify_line(line, width))
                   else:
                       new_par.append(' '.join(line))
                   line = []
               else:
                   # append next word
                   line.append(words.pop(0))
           else:
               # last line in paragraph
               new_par.append(' '.join(line))
               line = []
               break
        # replace paragraph with formatted version
        paragraphs[i] = '\n'.join(new_par)
    # return paragraphs separated by two newlines
    return '\n\n'.join(paragraphs)

def showTxtDiff(txtOne, txtTwo, fReformatLongLines=False):
    txtOneName = "c:\\txtOne.txt"
    txtTwoName = "c:\\txtTwo.txt"

    if fReformatLongLines:
        txtOne = fill_paragraphs(txtOne,80)
        txtTwo = fill_paragraphs(txtTwo,80)

    fo = open(txtOneName,"wb")
    #fo.write(title)
    fo.write(txtOne)
    fo.close()
    fo = open(txtTwoName,"wb")
    #fo.write(title)
    fo.write(txtTwo)
    fo.close()
    if g_DiffTool == DIFF_WINDIFF:
        diffWithWindiff(txtOneName,txtTwoName)
    if g_DiffTool == DIFF_ARAXIS:
        diffWithAraxis(txtOneName,txtTwoName)
    if g_DiffTool == DIFF_WINMERGE:
        diffWithWinMerge(txtOneName,txtTwoName)

def showTxtDiffArray(txtOneArray, txtTwoArray, fReformatLongLines=False):
    txtOneName = "c:\\txtOne.txt"
    txtTwoName = "c:\\txtTwo.txt"

    assert len(txtOneArray)==len(txtTwoArray)

    foOne = open(txtOneName,"wb")
    foTwo = open(txtTwoName,"wb")

    for (txtOne,txtTwo) in zip(txtOneArray,txtTwoArray):
        if fReformatLongLines:
            txtOne = fill_paragraphs(txtOne,80)
            txtTwo = fill_paragraphs(txtTwo,80)
        foOne.write(txtOne)
        foTwo.write(txtTwo)

    foOne.close()
    foTwo.close()

    if g_DiffTool == DIFF_WINDIFF:
        diffWithWindiff(origTmpName,convertedTmpName)
    if g_DiffTool == DIFF_ARAXIS:
        diffWithAraxis(origTmpName,convertedTmpName)
    if g_DiffTool == DIFF_WINMERGE:
        diffWithWinMerge(origTmpName,convertedTmpName)

def decodeDiTagValue(tagValue):
    strLen=len(tagValue)
    # string of uneven lenght cannot possibly be right
    if (strLen % 2) != 0:
        return None
    hexDigits = "0123456789ABCDEF"
    outStr = ""
    posInStr = 0
    while posInStr<strLen:
        try:
            outStr=outStr+chr(int(tagValue[posInStr:posInStr+2], 16))
            posInStr=posInStr+2
        except:
            return None
    return outStr

# each di tag consists of tag name and tag value
# known tag names are:
#  HS - hex-bin-encoded hotsync name
#  SN - hex-bin-encoded device serial number (if exists)
#  HN - hex-bin-encoded handspring device serial number (if exists)
#  PN - hex-bin-encoded phone number (if exists)
#  OC - hex-bin-encoded OEM company ID
#  OD - hex-bin-encoded OEM device ID
#  PL - hex-bin-encoded platform e.g. "Palm", "Smartphone", "Pocket PC", "SideKick"
#  DN - hex-bin-encoded SideKick's device number
def isValidDiTag(tag):
    if len(tag)<2:
        return False
    tagName=tag[:2]
    validTagNames={'HS':"HotSync Name", 'SN':"Serial Number", 'HN':"Handspring Serial Number", 'PN':"Phone Number", 'OC':"OEM Company ID", 'OD':"OEM Device ID", 'DN':"SideKick device number", 'PL':"Platform"}
    if not validTagNames.has_key(tagName):
        return False
    tagValue=decodeDiTagValue(tag[2:])
    if tagValue:
        return True
    return False

# given OEM Company ID (oc) and OEM Device id (od)
# return a name of Palm device.
# Based on data from http://homepage.mac.com/alvinmok/palm/codenames.html
# and http://www.mobilegeographics.com/dev/devices.php
def getDeviceNameByOcOd(oc, od):
    name = "Unknown (%s/%s)" % (toHexIfNeeded(oc), toHexIfNeeded(od))
    if "hspr"==oc:
        # HANDSPRING devices
        if od==decodeDiTagValue("0000000B"):
            name = "Treo 180"
        elif od==decodeDiTagValue("0000000D"):
            name = "Treo 270"
        elif od==decodeDiTagValue("0000000E"):
            name = "Treo 300"
        elif od=='H101':
            name = "Treo 600"
        elif od=='H201':
            name = "Treo 600 Simulator"
        elif od=='H102':
            name = "Treo 650"
        elif od=='H202':
            name = "Treo 650 Simulator"
    elif "sony"==oc:
    # SONY devices
        if od=='mdna':
            name = "PEG-T615C"
        elif od=='prmr':
            name = "PEG-UX50"
        elif od=='atom':
            name = "PEG-TH55"
        elif od=='mdrd':
            name = "PEG-NX80V"
        elif od=='tldo':
            name = "PEG-NX73V"
        elif od=='vrna':
            name = "PEG-TG50"
        elif od=='crdb':
            name = "PEG-NX60, NX70V"
        elif od=='mcnd':
            name = "PEG-SJ33"
        elif od=='glps':
            name = "PEG-SJ22"
        elif od=='goku':
            name = "PEG-TJ35"
        elif od=='luke':
            name = "PEG-TJ37"
        elif od=='ystn':
            name = "PEG-N610C"
        elif od=='rdwd':
            name = "PEG-NR70, NR70V";
        elif od=='leia':
            name = "PEG-TJ27"
    # MISC devices
    elif oc=='psys':
        name = "simulator"
    elif oc=='trgp' and od=='trg1':
        name = "TRG Pro"
    elif oc=='trgp' and od=='trg2':
        name = "HandEra 330"
    elif oc=='smsn' and od=='phix':
        name = "SPH-i300"
    elif oc=='smsn' and od=='Phx2':
        name = "SPH-I330"
    elif oc=='smsn' and od=='blch':
        name = "SPH-i500"
    elif oc=='qcom' and od=='qc20':
        name = "QCP 6035"
    elif oc=='kwc.' and od=='7135':
        name = "QCP 7135"
    elif oc=='Tpwv' and od=='Rdog':
        name = "Tapwave Zodiac 1/2"
    elif oc=='gsRl' and od=='zicn':
        name = "Xplore G18"        
    elif oc=="palm" or oc=="Palm":
    # PALM devices 
        if od=='hbbs':
            name = "Palm m130"
        elif od=='ecty':
            name = "Palm m505"
        elif od=='lith':
            name = "Palm m515"
        elif od=='Zpth':
            name = "Zire 71"
        elif od=='Zi72':
            name = "Zire 72"
        elif od=='Zi21':
            name = "Zire 21"
        elif od=='Zi22':
            name = "Zire 31"
        elif od=='MT64':
            name = "Tungsten C"
        elif od=='atc1':
            name = "Tungsten W"
        elif od=='Cct1':
            name = "Tungsten E"
        elif od=='Frg1':
            name = "Tungsten T"
        elif od=='Frg2':
            name = "Tungsten T2"
        elif od=='Arz1':
            name = "Tungsten T3"
        elif od=='TnT5':
            name = "Tungsten T5"
        elif od=='TunX':
            name = "LifeDrive"
    return name
    
def decodeDi(devInfo):
    tags=devInfo.split(":")
    retDict=dict()
    for tag in tags:
        if not isValidDiTag(tag):
            retDict['device_name'] = "INVALID because not isValidDiTag(%s)" % tag
            return retDict
        tagName = tag[:2]
        tagValueEnc=tag[2:]
        tagValue=decodeDiTagValue(tagValueEnc)
        if not tagValue:
            retDict['device_name'] = "INVALID because not decodeDiTagValue(%s, %s)" % (tagName, tagValueEnc)
            return retDict
        retDict[tagName] = tagValue
    deviceName = "*unavailable*"
    if retDict.has_key('OC') and retDict.has_key('OD'):
        deviceName = getDeviceNameByOcOd(retDict['OC'], retDict['OD'])
    retDict['device_name'] = deviceName
    return retDict

def extractHotSyncName(deviceInfo):
    di=decodeDi(deviceInfo)
    if di.has_key("HS"):
        return di["HS"]
    return None
    
def exceptionAsStr(e):
    tbList = traceback.format_tb(sys.exc_info()[2])
    tbStr = string.join(tbList,"")
    res = "%s\n%s\n%s\n%s" % (str(e), str(sys.exc_info()[0]), str(sys.exc_info()[1]), tbStr)
    return res
    
from httplib import HTTPConnection, HTTPException

# @note assumption that url is not encoded is unrealistic; url must be encoded
# @exception httplib.HTTPException is thrown in case of connection errors
# @return tuple (status, reason, responseText)
def retrieveHttpResponse(address, url, host=None):    
    status, reason, responseText=None, None, None
    conn=HTTPConnection(address)
    conn.connect()
    try:
        conn.putrequest("GET", url)
        conn.putheader("Accept", "image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, */*")
        if None!=host:
            conn.putheader("Host", host)
        else:
            conn.putheader("Host", address)
        conn.putheader("User-Agent", "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)")
        conn.putheader("Connection", "Keep-Alive")
        conn.endheaders()
        resp=conn.getresponse()
        status, reason, responseText=resp.status, resp.reason, resp.read()
    finally:
        conn.close()
    return status, reason, responseText

#code from http://www.noah.org/python/daemonize.py
'''This module is used to fork the current process into a daemon.

Almost none of this is necessary (or advisable) if your daemon 
is being started by inetd. In that case, stdin, stdout and stderr are 
all set up for you to refer to the network connection, and the fork()s 
and session manipulation should not be done (to avoid confusing inetd). 
Only the chdir() and umask() steps remain as useful. 

References:
    UNIX Programming FAQ
        1.7 How do I get my program to act like a daemon?
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
   
    Advanced Programming in the Unix Environment
        W. Richard Stevens, 1992, Addison-Wesley, ISBN 0-201-56317-7.
'''

def daemonize (stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    '''This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.
    Note that stderr is opened unbuffered, so
    if it shares a file with stdout then interleaved output
    may not appear in the order that you expect.
    '''

    # Do first fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0)   # Exit first parent.
    except OSError, e: 
        sys.stderr.write ("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)

    # Decouple from parent environment.
    os.chdir("/") 
    os.umask(0) 
    os.setsid() 

    # Do second fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0)   # Exit second parent.
    except OSError, e: 
        sys.stderr.write ("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)

    # Now I am a daemon!
    
    # Redirect standard file descriptors.
    si = open(stdin, 'r')
    so = open(stdout, 'a+')
    se = open(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def pids(program, arg0):
    '''Return a list of [process id, owner] for all processes that are running
    "program".  Relies on a particular output format for ps a little
    too much.'''

    result = []
    f = os.popen('ps aux', 'r')
    for l in f.readlines():
        fields = string.split(l)
        processName = fields[10]
        processName = processName.split("/")[-1]
        if processName == program:
            processArg0 = fields[11]
            if processArg0 == arg0:
                owner = fields[0] # name of the Unix user who owns this program
                #print "found: %s %s owned by %s" % (processName, processArg0, owner)
                result.append([int(fields[1]), owner])
    return result

