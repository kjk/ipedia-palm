#!/usr/bin/python
# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# This script:
#  - downloads the main page of http://download.wikimedia.org
#  - parsers it to find the name of the current english wikipedia cur database
#    e.g.: http://download.wikimedia.org/archives/en/20040403_cur_table.sql.bz2
#  - downloads it if it hasn't been downloaded yet

# requires process module from
# http://starship.python.net/crew/tmick/index.html#process

import sys,string,re,time,urllib2,os,os.path,process

g_workingDir = "c:\\ArsLexis\\wikipedia\\"
g_logFileName = g_workingDir + "log.txt"

g_reEnName = re.compile('archives/en/(\d+)_cur_table.sql.bz2', re.I)
g_reFrName = re.compile('archives/fr/(\d+)_cur_table.sql.bz2', re.I)
g_reDeName = re.compile('archives/de/(\d+)_cur_table.sql.bz2', re.I)

g_enUrlToDownload = None
g_deUrlToDownload = None
g_frUrlToDownload = None

g_foLog = None
def openLogFileIfNotOpen():
    global g_foLog, g_logFileName
    if None == g_foLog:
        g_foLog = open(g_logFileName, "ab+")
        curTime = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() )
        g_foLog.write( "Activity on %s\n" % curTime)
    return g_foLog

def closeLogFile():
    global g_foLog
    if g_foLog:
        g_foLog.close()

def logEvent(txtToLog):
    #print txtToLog
    fo = openLogFileIfNotOpen()
    fo.write("  " + txtToLog + "\n")


def matchUrlInTxt(txt, regExp):
    match=regExp.search(txt)
    if not match:
        return None

    fileName = txt[match.start():match.end()]
    fileUrl = 'http://download.wikimedia.org/' + fileName
    return fileUrl

def findEnFileUrlInStr(txt):
    global g_reEnName
    return matchUrlInTxt(txt, g_reEnName)

def findFrFileUrlInStr(txt):
    global g_reFrName
    return matchUrlInTxt(txt, g_reFrName)

def findDeFileUrlInStr(txt):
    global g_reDeName
    return matchUrlInTxt(txt, g_reDeName)

def getCurrentFileUrls():
    global g_enUrlToDownload, g_deUrlToDownload, g_frUrlToDownload
    try:
        f = urllib2.urlopen('http://download.wikimedia.org/')
        wikipediaHtml = f.read()
        f.close()
    except:
        logEvent("Failed to download http://download.wikimedia.org")
        raise
    #print wikipediaHtml
    logEvent("Downloaded http://download.wikimedia.org/index.html")
    g_enUrlToDownload = findEnFileUrlInStr(wikipediaHtml)
    if not g_enUrlToDownload:
        logEvent("Didn't find the url for en cur database in http://download.wikimedia.org/index.html")
    else:
        logEvent("Found url for en cur database: " + g_enUrlToDownload )

    g_frUrlToDownload = findFrFileUrlInStr(wikipediaHtml)
    if not g_frUrlToDownload:
        logEvent("Didn't find the url for fr cur database in http://download.wikimedia.org/index.html")
    else:
        logEvent("Found url for fr cur database: " + g_frUrlToDownload )

    g_deUrlToDownload = findDeFileUrlInStr(wikipediaHtml)
    if not g_deUrlToDownload:
        logEvent("Didn't find the url for de cur database in http://download.wikimedia.org/index.html")
    else:
        logEvent("Found url for de cur database: " + g_deUrlToDownload )

def fFileExists(filePath):
    try:
        st = os.stat(filePath)
    except OSError:
        # TODO: should check that Errno is 2
        return False
    return True

# based on url of the form http://*/$lang/$fileName construct a file name of
# form "%s_%s" % ($lang, $fileName)
def fileNamesFromUrl(url):
    global g_workingDir
    fileName = url.split("/")[-1]
    lang = url.split("/")[-2]
    fileNameGzipped = "%s_%s" % (lang,fileName)
    filePathGzipped = os.path.join(g_workingDir,fileNameGzipped)

    # convert "foo.sql.bz2" to "foo.sql"
    parts = filePathGzipped.split(".")
    filePathUngzipped = string.join(parts[0:-1], ".")
    filePathUngzipped = os.path.join(g_workingDir,filePathUngzipped)

    #print filePathGzipped
    #print filePathUngzipped

    return (filePathGzipped, filePathUngzipped)

def fDbDownloaded(url):
    (fileGzipped, fileUngizpped) = fileNamesFromUrl(url)
    if fFileExists(fileGzipped):
        return True
    if fFileExists(fileUngizpped):
        return True
    return False

# I could try to use python's urllib2 module to do the downloading, but
# I prefer to outsorce that to wget
def downloadUrl(url):
    global g_workingDir

    if None == url:
        return
    os.chdir(g_workingDir)
    (fileNameGzipped, fileNameUngzipped) = fileNamesFromUrl(url)
    p = process.ProcessOpen(['wget.exe', '-c', url, '--output-document', fileNameGzipped])

    res_stdout = p.stdout.read()                                     
    res_stderr = p.stderr.read()
    status = p.wait()   # .wait() returns the child's exit status

    #print "status = %d" % status

    if -1 != res_stderr.find("is not recognized"):
        logEvent("didn't launch wget.exe properly")
        return
    
    if fDbDownloaded(url):
        logEvent("succesfully downloaded %s" % url)
    else:
        logEvent("failed to download %s" % url)

def downloadDb(url):
    if fDbDownloaded(url):
        logEvent("%s has already been downloaded" % url)
    else:
        downloadUrl(url)

if __name__=="__main__":
    getCurrentFileUrls()
    downloadDb(g_enUrlToDownload)
    downloadDb(g_frUrlToDownload)
    downloadDb(g_deUrlToDownload)

