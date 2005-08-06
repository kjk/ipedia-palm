import sys, os, codecs, gzip
from xml.sax import handler, make_parser
from xml.sax.saxutils import escape

g_elemsCount = 0
MAX_ELEMS_COUNT = 10

class Page:
    def __init__(self):
        self.title = None
        self.body = None

class MyEntityResolver:
    def resolveEntity(self, publicId, systemId):
        print "publicId: '%s'" % publicId
        print "systemId: '%s'" % publicId

class ContentGenerator(handler.ContentHandler):

    def __init__(self, outFileName):
        handler.ContentHandler.__init__(self)
        self.curPage = None
        self.inText = False
        self.inTitle = False
        self.fo = None
        self.outFileName = outFileName

    def startDocument(self):
        self.fo = codecs.open(self.outFileName, "wb", "utf-8")

    def endDocument(self):
        self.fo.close()

    def startElement(self, name, attrs):
        if name == "page":
            assert None == self.curPage
            self.curPage = Page()
        elif name == "title":
            self.inTitle = True
        elif name == "text":
            self.inText = True

    def endElement(self, name):
        if name == "page":
            assert None != self.curPage
            self.curPage = None
        elif name == "title":
            self.inTitle = False
        elif name == "text":
            self.inText = False

    def characters(self, content):
        if self.inText:
            assert None != self.curPage
            if None == self.curPage.body:
                self.curPage.body = [content]
                sys.stdout.write("\n")
                self.fo.write("\n#")
            else:
                self.curPage.body.append(content)
            #sys.stdout.write(content)
            self.fo.write(content)
            #print "text: '%s'" % content
        elif self.inTitle:
            assert None != self.curPage
            self.curPage.title = content
            sys.stdout.write("\nTitle:")
            sys.stdout.write(content)
            self.fo.write("!")
            self.fo.write(content)
            self.fo.write("\n")
            #print "title: '%s'" % content

#    def ignorableWhitespace(self, content):
#        self._out.write(content)

#    def processingInstruction(self, target, data):

if __name__=='__main__':
    fileName = "c:\\kjk\\20050713_pages_current.xml.gz"
    outFileName = "c:\\kjk\\out.xml"
    fo = gzip.GzipFile(fileName, "rb", 9)
    parser = make_parser()
    parser.setContentHandler(ContentGenerator(outFileName))
    parser.setEntityResolver(MyEntityResolver())
    #parser.feed("""<?xml version='1.0' encoding='utf-8'?>""")
    #parser.parse(fo)
    parser.parse(fo)
    fo.close()

