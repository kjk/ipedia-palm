# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# Purpose: intelligent, incremental parsing of web server
# log files.

# Things I want to know:
# * daily, weekly, monthly stats on:
# - hits
# - pages
# - visits
# - referrers
# - new referrers that day
# - search terms this day
# - new search terms this day

import sys, string, pickle

g_fileName = "c:\\blogkowalczyk.info-access_log"

def parseLogLine(line):
    line = line.strip()
    #print line
    parts = []
    while True:
        #if len(parts)>0:
        #    print parts[-1]
        #print "_%s_" % line
        if 3==len(parts):
            # 4th is the date in the format "[...]"
            if '[' != line[0]:
                print line
            assert '[' == line[0]
            (part,rest) = line.split("] ",1)
            part = part[1:]
            parts.append(part)
            line = rest
            continue
        try:
            if '"'==line[0]:
                (part, rest) = line.split("\" ",1)
                part = part[1:]
            else:
                (part, rest) = line.split(" ", 1)
        except ValueError:
            # this means we're trying to split a string but there's nothing
            # else to split so this is the last part
            parts.append(line)
            break
        parts.append(part)
        line = rest
        continue
    return parts

def getClientIP(parts):
    return parts[0]
def getRequestTime(parts):
    return parts[3]
def getRequest(parts):
    return parts[4]
def getResponseCode(parts):
    return parts[5]
def getResponseSize(parts):
    return parts[6]
def getRequestReferer(parts):
    return parts[7]
def getRequestClient(parts):
    return parts[8]

g_monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
def getMonthNumberByName(monthName):
    global g_monthNames
    try:
        monthPos = g_monthNames.index(monthName)
    except:
        print monthName
        raise
    return monthPos+1

# return date on which request has been made in the form yyyy-mm-dd e.g. 2004-07-13
def getRequestDate(parts):
    dateTime = getRequestTime(parts)
    parts = dateTime.split("/")
    day = parts[0]
    monthName = parts[1]
    monthNumber = getMonthNumberByName(monthName)
    yearWithTime = parts[2]
    yearParts = yearWithTime.split(":")
    year = yearParts[0]
    assert 4 == len(year)
    monthNumberInt = int(monthNumber)
    dayInt = int(day)
    date = "%s-%02d-%02d" % (year, monthNumberInt, dayInt)
    return date

# keeps a dict of all referers we've seen so far so that we can 
g_referersSoFar = {}

g_dailyStats = {}

g_lastFilePos = 0

def getDaysCount():
    global g_dailyStats
    return len(g_dailyStats)

g_pickleFileName = "picledData.dat"
def pickleState():
    global g_pickleFileName, g_dailyStats, g_referersSoFar, g_lastFilePos
    # save all the variables that we want to persist across session on disk
    fo = open(g_pickleFileName, "wb")
    pickle.dump(g_lastFilePos,fo)
    pickle.dump(g_dailyStats,fo)
    pickle.dump(g_referersSoFar,fo)
    fo.close()

def unpickleState():
    global g_pickleFileName, g_dailyStats, g_referersSoFar, g_lastFilePos
    # restores all the variables that we want to persist across session from
    # the disk
    try:
        fo = open(g_pickleFileName, "rb")
    except IOError:
        # it's ok to not have the file
        return
    g_lastFilePos = pickle.load(fo)
    g_dailyStats = pickle.load(fo)
    g_referersSoFar = pickle.load(fo)
    fo.close()


class SearchTermDay:
    def __init__(self,term,count,fNew):
        self.term = term
        self.count = count
        self.fNew = fNew

class DailyStats:
    def __init__(self, date):
        self.date = date
        self.hitsCount = 0
        # self.pagesCount = 0 # not sure how to calculate that? Only count *.html stuff
        self.visitors = []
        self.newReferers = []
        self.searchTerms = []
        self.referers = []

    def incHitsCount(self):
        self.hitsCount += 1

    def getVisitorsCount(self):
        return len(self.visitors)

    def addVisitor(self,visitorIP):
        if not visitorIP in self.visitors:
            self.visitors.append(visitorIP)

    def dump(self):
        #print "date:     %s" % self.date
        #print "requests: %d" % self.reqCount
        #print "vistors:  %d" % self.visitorsCount
        print "%s %5d %5d" % (self.date,self.hitsCount,self.getVisitorsCount())

g_maxLines = 50000
g_daysToProcess = 10

def analyzeLogLine(logLine):
    global g_dailyStats, g_referersSoFar
    parsed = parseLogLine(logLine)
    date = getRequestDate(parsed)
    if g_dailyStats.has_key(date):
        stats = g_dailyStats[date]
    else:
        stats = DailyStats(date)
        g_dailyStats[date] = stats
    stats.incHitsCount()
    stats.addVisitor(getClientIP(parsed))

def main():
    global g_fileNameg_dailyStats,g_lastFilePos, g_daysToProcess, g_maxLines
    fo = open(g_fileName, "rb")
    print "Seeking to pos %d" % g_lastFilePos
    fo.seek(g_lastFilePos)
    linesCount = 0
    for line in fo:
        analyzeLogLine(line)
        linesCount += 1
        if linesCount > g_maxLines:
            break
        #if getDaysCount() > g_daysToProcess:
        #    break
    g_lastFilePos = fo.tell()
    print "last file pos: %d" % g_lastFilePos
    fo.close()

    print "days: %d" % getDaysCount()
    days = g_dailyStats.keys()
    days.sort()
    for day in days:
        dailyStats = g_dailyStats[day]
        dailyStats.dump()
        #print

if __name__=="__main__":
    try:
        unpickleState()
        main()
    finally:
        # make sure that we pickle the state even if we crash
        pickleState()
