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
# * new referrers that day

fileName = "c:\\blogkowalczyk.info-access_log"

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
            assert "[" == line[0]
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

class Stats:
    def __init__(self,date):
        self.date = date
        self.reqCount = 0
        self.visitorsCount = 0
        self.referers = []
        self.visitors = []

    def addVisitor(self,visitorIP):
        if not visitorIP in self.visitors:
            self.visitors.append(visitorIP)
            self.visitorsCount += 1

    def dump(self):
        #print "date:     %s" % self.date
        #print "requests: %d" % self.reqCount
        #print "vistors:  %d" % self.visitorsCount
        print "%s %5d %5d" % (self.date,self.reqCount,self.visitorsCount)

startAtLine = 0
maxLines = 20
linesCount = 0
daysToProcess = 115
g_daysCount = 0

referers = {}
dayStats = {}

def analyzeLogLine(logLine):
    global dayStats, referers, g_daysCount
    parsed = parseLogLine(logLine)
    date = getRequestDate(parsed)
    if dayStats.has_key(date):
        stats = dayStats[date]
    else:
        stats = Stats(date)
        dayStats[date] = stats
        g_daysCount += 1
    stats.reqCount += 1
    stats.addVisitor(getClientIP(parsed))

fo = open(fileName)
for line in fo:
    analyzeLogLine(line)
    linesCount += 1
    #if linesCount > maxLines:
    #    break
    if g_daysCount > daysToProcess:
        break
fo.close()

print "days: %d" % g_daysCount
for stats in dayStats.values():
    stats.dump()
    #print
