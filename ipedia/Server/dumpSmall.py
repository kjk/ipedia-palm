# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Purpose:
#   Dumps to stdout all articles, whose size is under threshold.
# Usage:
#   -size $size : threshold
#   fileName - which sql file to process

from __future__ import generators   # for 2.2 compatibility
import sys,os,os.path,string,re,random,time,md5,bz2
import arsutils,wikipediasql,articleconvert
try:
    import psyco
    psyco.full()
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"

DEFAULT_SIZE = 20

def usageAndExit():
    print "Usage: dumpSmall.py [-size $size] fileName"
    print "Default size: %d bytes" % DEFAULT_SIZE
    sys.exit(0)

def findConvertedArticlesUnderThreshold(fileName,thresholdSize):
    print "looking for converted articles smaller than %d bytes" % thresholdSize
    count = 0
    articles = []
    for article in wikipediasql.iterConvertedArticles(fileName):
        if article.fRedirect():
            continue
        body = article.getText()
        if len(body)<thresholdSize:
            #print "size: %d, title: '%s'" % (len(body),article.getTitle())
            articles.append(article)
        count += 1
        if count % 20000 == 0:
            print "processed %d articles, found %d small" % (count,len(articles))
    return articles

def findOrigArticlesUnderThreshold(fileName,thresholdSize):
    print "looking for original articles smaller than %d bytes" % thresholdSize
    count = 0
    articles = []
    for article in wikipediasql.iterWikipediaArticles(fileName,None,fUseCache=True,fRecreateCache=False):
        if article.fRedirect():
            continue
        body = article.getText()
        if len(body)<thresholdSize:
            #print "size: %d, title: '%s'" % (len(body),article.getTitle())
            articles.append(article)
        count += 1
        if count % 20000 == 0:
            print "processed %d articles, found %d small" % (count,len(articles))
    return articles

def dumpArticles(fileName,articles):
    fo = open(fileName, "wb")
    for article in articles:
        fo.write("!'%s'\n" % article.getTitle().strip())
        fo.write("'%s'\n" % (article.getText().strip()) )
    fo.close()

if __name__=="__main__":
    size = arsutils.getRemoveCmdArg("-size")
    if None == size:
        size = DEFAULT_SIZE
    else:
        size = int(size)

    # now we should only have file name
    if len(sys.argv) != 2:
        print "Have to provide *.sql or *.sql.bz2 file name with wikipedia dump"
        usageAndExit()
    fileName = sys.argv[1]
    fileNameOutConv = wikipediasql.getSmallConverterFileName(fileName)
    fileNameOutOrig = wikipediasql.getSmallOrigFileName(fileName)

    articles = findConvertedArticlesUnderThreshold(fileName,size)
    dumpArticles(fileNameOutConv,articles)

    articles = findOrigArticlesUnderThreshold(fileName,size)
    dumpArticles(fileNameOutOrig,articles)

