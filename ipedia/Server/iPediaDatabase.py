import re, random, sys

DB_HOST = 'localhost'
DB_USER = 'ipedia'
DB_PWD  = 'ipedia'

MANAGEMENT_DB = 'ipedia_manage'

redirectCommand =    "#REDIRECT"
termStartDelimiter = "[["
termEndDelimiter =   "]]"

g_fVerbose=False

# if true we'll log terms that redirect to themselves to a file
g_fLogCircularReferences = True
g_circularReferencesLogName = "circular.log"

class CircularDetector(object):
    def __init__(self,logFileName):
        self.logFileName = logFileName
        self.loadLog()
    def loadLog(self):
        self.circulars = {}
        try:
            fo = open(self.logFileName, "rb")
            for lines in fo.readlines():
                (defId,term) = line.split(":")
                self.circulars[defId] = term
            fo.close()
        except:
            pass #it's ok if file doesn't exist
    def log(self,defId,term):
        if not self.circulars.has_key(defId):
            self.circulars[defId] = term
    def saveLog(self):
         fo = open(self.logFileName,"wb")
         for defId in self.circulars.keys():
            term = self.circulars[defId]
            toWrite = defId + ":" + term + "\n"
            fo.write(toWrite)
         fo.close()

g_circularDetector = None
def logCircular(defId,term):
    global g_fLogCircularReferences, g_circularDetector, g_circularReferencesLogName
    if not g_fLogCircularReferences:
        return
    if not g_circularDetector:
        g_circularDetector = CircularDetector(g_circularReferencesLogName)
    g_circularDetector.log(defId,term)

def saveCircular():
    global g_fLogCircularReferences, g_circularDetector
    if not g_fLogCircularReferences:
        return
    if g_circularDetector:
        g_circularDetector.saveLog()

def testCircular():
    logCircular("me", "him")
    logCircular("me", "him2")
    logCircular("one", "two")
    logCircular("three", "four")
    saveCircular()

def startsWithIgnoreCase(s1, substr):
    if len(s1)<len(substr):
        return False
    if s1[:len(substr)].upper()==substr.upper():
        return True
    return False

internalLinkRe=re.compile(r'\[\[(.*?)(\|.*?)?\]\]', re.S)
testedLinks = {}
validLinks = {}

#def validateInternalLinks(db, cursor, definition):
#    global g_fVerbose, validLinks, testedLinks
#
#    if g_fVerbose:
#        sys.stdout.write("* Validaiting internal links: ")
#    matches=[]
#    for iter in internalLinkRe.finditer(definition):
#        matches.append(iter)
#    matches.reverse()
#    for match in matches:
#        term=match.group(1)
#        if len(term)!=0 and not testedLinks.has_key(term):
#            testedLinks[term] = 1
#            idTermDef=findExactDefinition(db, cursor, term)
#            if idTermDef:
#                if g_fVerbose:
#                    sys.stdout.write("'%s' [ok], " % term)
#                validLinks[term] = 1
#        if not validLinks.has_key(term):
#            name=match.group(match.lastindex).lstrip('| ').rstrip().replace('_', ' ')
#            if g_fVerbose:
#                sys.stdout.write("'%s' => '%s', " % (term,name))
#            definition=definition[:match.start()]+name+definition[match.end():]
#    return definition

