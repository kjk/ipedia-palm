# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Collect routines frequently used in other places

import os,sys,time
try:
    import process
except:
    print "requires process module (http://starship.python.net/crew/tmick/)"
    sys.exit(0)

# which diff tool to use. AraxisMerge is the best, imo (shows character-level
# diffs, not only line-level)
(DIFF_WINDIFF,DIFF_ARAXIS, DIFF_WINMERGE) = range(3)

#g_DiffTool = DIFF_WINDIFF
g_DiffTool = DIFF_ARAXIS
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

class Timer:
    def __init__(self,fStart=False):
        self.startTime = None
        self.endTime = None
        if fStart:
            self.start()
    def start(self):
        self.startTime = time.clock()
    def stop(self):
        self.endTime = time.clock()
    def dumpInfo(self):
        dur = self.endTime - self.startTime
        txt = "duration %f seconds\n" % dur
        sys.stderr.write(txt)

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
    p = process.ProcessOpen(["windiff.exe", orig, converted])
    fFinishProcess(p,True)

def diffWithAraxis(orig,converted):
    p = process.ProcessOpen(["C:\Program Files\Araxis Merge 2001\compare.exe", orig, converted])
    fFinishProcess(p,True)

def diffWithWinMerge(orig,converted):
    p = process.ProcessOpen(["c:\Program Files\WinMerge\WinMergeU.exe", orig, converted])
    fFinishProcess(p,True)

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
def isValidDiTag(tag):
    if len(tag)<2:
        return False
    tagName=tag[:2]
    validTagNames={'HS':"HotSync Name", 'SN':"Serial Number", 'HN':"Handspring Serial Number", 'PN':"Phone Number", 'OC':"OEM Company ID", 'OD':"OEM Device ID", 'DN':"Hell knows"}
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
    name="Unknown (%s/%s)" % (oc, od)
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
    
