#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import sys, os, string, re, random, time, pickle, smtplib
import MySQLdb, _mysql_exceptions

import arsutils
#import ServerErrors, Fields

# TODO:
# - add per-user stats (how many requests a given user did)
# - add requests stats

DB_HOST    = 'localhost'
DB_PWD     = "ipedia"
DB_USER    = 'ipedia'
DB_NAME    = 'ipedia_manage'

# this is the request_id column from request_log table of the last request_id
# processed in previous run
g_lastRequestLogId = None
# this is the user_id column from users table of the last user_id processed
# in previous run
g_lastUserId = None

g_dailyStats = {}
g_modifiedDays = {}

g_pickleFileName = "parse_logs_pickle.dat"

if sys.platform == "linux2":
    # this must be my rackshack server
    g_pickleFileName = "/home/ipedia/parse_logs_pickle.dat"

def pickleState():
    global g_pickleFileName, g_lastRequestLogId, g_lastUserId, g_dailyStats
    fo = open(g_pickleFileName, "wb")
    pickle.dump(g_lastRequestLogId,fo)
    pickle.dump(g_lastUserId,fo)
    pickle.dump(g_dailyStats,fo)
    fo.close()

def unpickleState():
    global g_pickleFileName, g_lastRequestLogId, g_lastUserId, g_dailyStats
    try:
        fo = open(g_pickleFileName, "rb")
    except IOError:
        # it's ok to not have the file
        return
    g_lastRequestLogId = pickle.load(fo)
    g_lastUserId = pickle.load(fo)
    g_dailyStats = pickle.load(fo)
    fo.close()

g_conn = None
def getConnection():
    global g_conn
    if None == g_conn:
        g_conn = MySQLdb.Connect(host=DB_HOST, user=DB_USER, passwd=DB_PWD, db=DB_NAME)
    return g_conn

def deinitDatabase():
    global g_conn
    #print "deinitDatabase()"
    closeAllNamedCursors()
    if g_conn:
        g_conn.close()
        g_conn = None

g_namedCursors = {}
def getNamedCursor(conn,curName):
    global g_namedCursors
    # a little pooling of cursors based on their names
    # the idea is to save time by not calling conn.cursor()/conn.close()
    if not g_namedCursors.has_key(curName):
        g_namedCursors[curName] = conn.cursor()
    return g_namedCursors[curName]

def closeNamedCursor(curName):
    global g_namedCursors
    if g_namedCursors.has_key(curName):
        cur = g_namedCursors[curName]
        cur.close()
        del g_namedCursors[curName]

def closeAllNamedCursors():
    global g_namedCursors
    for cur in g_namedCursors.values():
        cur.close()
    g_namedCursors.clear()

def dbEscape(txt):
    # it's silly that we need connection just for escaping strings
    global g_conn
    return g_conn.escape_string(txt)


# A format of a request accepted by a server is very strict:
# validClientRequest = validClientField ":" fieldValue? "\n"
# fieldValue = " " string
# validClientField = "Get-Cookie" | "Protocol-Version" etc.
# In other words:
#  - if request has no parameters, then it must be a requestField immediately
#    followed by a colon (":") and a newline ("\n")
#  - if request has parameters, then it must be a requestField immediately
#    followed by a colon (":"), space (" "), arbitrary string which is an argument and newline ("\n")
#
# This function parses the request line from the server and returns a tuple
# (field,value). If request has no parameters, value is None
# If there was an error parsing the line (it doesn't correspond to our strict
# format), field is None
def parseRequestLine(line):
    parts = line.split(":", 1)
    if 1==len(parts):
        # there was no ":" so this is invalid request
        return (None,None)
    field = parts[0]
    value = parts[1]
    if 0==len(value):
        # the second part is an empty line which means that this is a request
        # without an argument
        return (field, None)
    # this is a request with an argument, so it should begin with a space
    if ' '!=value[0]:
        # it doesn't begin with a space, so invalid
        return (None,None)
    value = value[1:]
    return (field,value)

# given a device info as a string in our encoded form, return a dictionary
# whose keys are tags (e.g. "PL", "SN", "PN") and value is a tuple: 
# (value as decoded hex string, value as original hex-encoded string)
# Return None if device info is not in a (syntactically) correct format.
# Here we don't check if tags are valid (known), just the syntax
def decodeDeviceInfo(deviceInfo):
    result = {}
    parts = deviceInfo.split(":")
    for part in parts:
        # each part has to be in the format: 2-letter tag followed by
        # hex-encoded value of that tag
        if len(part)<4:
            # 4 characters are: 2 for the tag, 2 for at least one byte of value
            return None
        tag = part[0:2]
        tagValueHex = part[2:]
        if len(tagValueHex) % 2 != 0:
            return None
        rest = tagValueHex
        tagValueDecoded = ""
        while len(rest)>0:
            curByteHex = rest[0:2]
            rest = rest[2:]
            try:
                curByte = int(curByteHex,16)
                tagValueDecoded += chr(curByte)
            except:
                return False
        result[tag] = (tagValueDecoded,tagValueHex)
    return result

def deviceInfoAsTxt(deviceInfo, deviceInfoDecoded = None):
    if None == deviceInfoDecoded:
        deviceInfoDecoded = decodeDeviceInfo(deviceInfo)
    result = ""
    platform = ""
    for (tag,value) in deviceInfoDecoded.items():
        valueDecoded = value[0]
        valueHex = value[1]
        if tag == "PL":
            platform = valueDecoded
            continue
        if arsutils.fStringPrintable(valueDecoded):
            result += "%s:%s, " % (tag, valueDecoded)
        else:
            result += "%s:0x%s, " % (tag, valueHex)
    if len(result)>2:
        # remove the last ", "
        result = result[:-2]
    result = platform + ", " + result
    return result

# TODO: add Smartphone/Pocket PC tags
validTags = ["PL", "PN", "SN", "HN", "OC", "OD", "HS", "IM"]
def fValidDeviceInfo(deviceInfo):
    deviceInfoDecoded = decodeDeviceInfo(deviceInfo)
    if None == deviceInfoDecoded:
        log(SEV_HI,"couldn't decode device info '%s'\n" % deviceInfo)
        return False
    tagsPresent = deviceInfoDecoded.keys()
    for tag in tagsPresent:
        if tag not in validTags:
            log(SEV_HI,"tag '%s' is not valid\n" % tag)
            return False
    # "PL" (Platform) is a required tag - must be sent by all clients
    if "PL" not in tagsPresent:
        return False
    return True

# If we know for sure that device id was unique, we issue previously assigned
# cookie. This prevents using program indefinitely by just reinstalling it
# after a limit for unregistered version has been reached.
# Unique tags are: 
#   PN (phone number)
#   SN (serial number)
#   HN (handspring serial number)
#   IM (Treo IMEI number)
def fDeviceInfoUnique(deviceInfo):
    deviceInfoDecoded = decodeDeviceInfo(deviceInfo)
    if None == deviceInfoDecoded:
        return False
    tags = deviceInfoDecoded.keys()
    if ("PN" in tags) or ("SN" in tags) or ("HN" in tags) or ("IM" in tags):
        return True
    return False

# Which mail server to use when sending an e-mail
MAILHOST = None
# list of e-mail addresses to which send the e-mail
EMAILS_TO_NOTIFY = ["krzysztofk@pobox.com", "kkowalczyk@gmail.com"]
#EMAILS_TO_NOTIFY = ["szknitter@wp.pl", "smiech@op.pl"]

FROM = None

if sys.platform == "linux2":
    # this is our rackshack server
    #MAILHOST = "ipedia.arslexis.com"
    MAILHOST = "127.0.0.1"
    FROM = "ipedia@ipedia.arslexis.com"
else:
    # this must be windows
    if "KJKLAP1"==os.getenv("COMPUTERNAME"):
        # this must be my laptop
        # this will only work when I'm connected to nwlink.com
        EMAILS_TO_NOTIFY = ["kkowalczyk@gmail.com"]
        MAILHOST = "mail.nwlink.com"
        FROM = "kjk@nwlink.com"
    if "DVD"==os.getenv("COMPUTERNAME"):
        # this must be my desktop machine
        EMAILS_TO_NOTIFY = ["kkowalczyk@gmail.com"]
        MAILHOST = "mail.nwlink.com"
        FROM = "kjk@nwlink.com"
    if "MAGG"==os.getenv("COMPUTERNAME"):
        # this must be my - szymon - machine
        EMAILS_TO_NOTIFY = ["arslexis@wp.pl, arslexis@op.pl, arslexis@mail.ru"]
        MAILHOST = "smtp.mail.ru"
        FROM = "szknitter@mail.ru"
    if MAILHOST == None:
        print "Your computer name is:%s" % os.getenv("COMPUTERNAME")
        print "No mail about parsing failures will be send"

def mailTxt(txt):
    global MAILHOST, FROM, EMAILS_TO_NOTIFY
    if None == MAILHOST:
        print "Didn't send because MAILHOST empty"
        return
    curDate = time.strftime( "%Y-%m-%d", time.localtime() )
    SUBJECT = "iPedia log parsing results on %s" % (curDate)
    body = string.join((
        "From: %s" % FROM,
        "To: %s" % string.join(EMAILS_TO_NOTIFY,", "),
        "Subject: %s" % SUBJECT,
        "",
        txt), "\r\n")
    server = smtplib.SMTP(MAILHOST)
    server.sendmail(FROM, EMAILS_TO_NOTIFY, body)
    server.quit()

g_hourInSeconds = float(60*60*60)

class RequestData:
    def __init__(self):
        self.request_id = None
        self.user_id = None
        self.log_date = None
        self.free_p = None
        self.request = None
        self.result = None
        self.error = None

(DEV_PALM, DEV_POCKET_PC, DEV_SMARTPHONE, DEV_TEST_CLIENT, DEV_UNKNOWN) = range(5)

class UserData:
    def __init__(self):
        self.user_id = None
        self.device_info = None
        self.device_info_decoded = None
        self.device_info_as_txt = None
        self.device_type = None
        self.cookie_issue_date = None
        self.req_code = None
        self.registration_date = None
        self.disabled_p = None
        self.new_user_p = None

    def ensureDecodedDeviceInfo(self):
        if None == self.device_info_decoded:
            self.device_info_decoded = decodeDeviceInfo(self.device_info)

    def deviceType(self):
        if None != self.device_type:
            return self.device_type
        self.ensureDecodedDeviceInfo()
        platform = self.device_info_decoded["PL"][0]
        platform = platform.lower()
        if 0 == platform.find("palm"):
            self.device_type = DEV_PALM
        elif 0 == platform.find("pocketpc"):
            self.device_type = DEV_POCKET_PC
        elif 0 == platform.find("smartphone"):
            self.device_type = DEV_SMARTPHONE
        elif 0 == platform.find("00"):
            self.device_type = DEV_TEST_CLIENT
        else:
            self.device_type = DEV_UNKNOWN
        return self.device_type

    def palmDeviceName(self):
        assert DEV_PALM == self.deviceType()
        oc = self.device_info_decoded["OC"]
        oc = oc[0]
        od = self.device_info_decoded["OD"]
        od = od[0]
        deviceName = arsutils.getDeviceNameByOcOd(oc, od)
        return deviceName

    def pocketPCDeviceName(self):
        assert DEV_POCKET_PC == self.deviceType()
        oc = self.device_info_decoded["OC"]
        deviceName = oc[0]
        return deviceName

    def deviceName(self):
        if DEV_PALM == self.deviceType():
            return self.palmDeviceName()
        elif DEV_POCKET_PC == self.deviceType():
            return self.pocketPCDeviceName()
        else:
            return None

    def deviceInfoAsTxt(self):
        self.ensureDecodedDeviceInfo()
        if None == self.device_info_as_txt:
            self.device_info_as_txt = deviceInfoAsTxt(None, self.device_info_decoded)
        return self.device_info_as_txt

    def isRegistered(self):
        if self.reg_code != None:
            return True
        return False

g_userStats = []

# Retrieve all unprocessed data from users table and cache them in memory
def retrieveUsers():
    global g_lastUserId, g_userStats
    cursor = None
    conn = getConnection()
    try:
        sql = "SELECT user_id, device_info, DATE_FORMAT(cookie_issue_date, '%Y-%m-%d'), reg_code, DATE_FORMAT(registration_date, '%Y-%m-%d'), disabled_p FROM users ORDER BY user_id;";
        #sql = "SELECT user_id, device_info, DATE_FORMAT(cookie_issue_date, '%Y-%m-%d'), reg_code, DATE_FORMAT(registration_date, '%Y-%m-%d'), disabled_p FROM users WHERE user_id > " + str(g_lastUserId) + "ORDER BY user_id;";

        cursor = conn.cursor()
        cursor.execute(sql)

        processed = 0
        prev_id = -1
        while True:
            row = cursor.fetchone()
            if None == row:
                break
            userData = UserData()
            userData.user_id = row[0]
            userData.device_info = row[1]
            userData.cookie_issue_date = row[2]
            userData.reg_code = row[3]
            userData.registration_date = row[4]
            userData.disabled_p = row[5]
            if None == userData.registration_date:
                userData.fRegistered = False
            else:
                userData.fRegistered = True

            if userData.user_id > g_lastUserId:
                userData.new_user_p = True
            else:
                userData.new_user_p = False

            assert userData.user_id > prev_id 
            prev_id = userData.user_id

            g_userStats.append(userData)
            if userData.user_id > g_lastUserId:
                g_lastUserId = userData.user_id
            processed += 1
        cursor.close()

        # print "processed %d requests" % processed
    except _mysql_exceptions.Error, ex:
        if cursor:
            cursor.close()
        #log(SEV_HI, arsutils.exceptionAsStr(ex))
        print "exception in retrieveUsers()"
        print arsutils.exceptionAsStr(ex)

# Retrieve all unprocessed request data from the database and cache them in
# memory
def retrieveRequests():
    global g_lastRequestLogId, g_dailyStats, g_modifiedDays
    cursor = None
    conn = getConnection()
    try:
        if None == g_lastRequestLogId:
            sql = "SELECT request_id, user_id, DATE_FORMAT(log_date, '%Y-%m-%d'), free_p, request, result, error FROM request_log ORDER BY request_id;"
        else:
            sql = "SELECT request_id, user_id, DATE_FORMAT(log_date, '%Y-%m-%d'), free_p, request, result, error FROM request_log WHERE request_id > " + str(g_lastRequestLogId) + " ORDER BY request_id;"

        cursor = conn.cursor()
        cursor.execute(sql)

        processed = 0
        prev_id = -1
        while True:
            row = cursor.fetchone()
            if None == row:
                break
            reqData = RequestData()
            reqData.request_id = row[0]
            reqData.user_id = row[1]
            reqData.log_date = row[2]
            reqData.free_p = row[3]
            reqData.request = row[4]
            reqData.result = row[5]
            reqData.error = row[6]  # it's either a number or None if there was no error

            assert reqData.request_id > prev_id 
            prev_id = reqData.request_id
            
            logDate = reqData.log_date
            if g_dailyStats.has_key(logDate):
                g_dailyStats[logDate].append(reqData)
            else:
                g_dailyStats[logDate] = [reqData]

            if not g_modifiedDays.has_key(logDate):
                g_modifiedDays[logDate] = 1

            if reqData.request_id > g_lastRequestLogId:
                g_lastRequestLogId = reqData.request_id
            processed += 1
        cursor.close()

        # print "processed %d requests" % processed
    except _mysql_exceptions.Error, ex:
        if cursor:
            cursor.close()
        #log(SEV_HI, arsutils.exceptionAsStr(ex))
        print "exception in retrieveRequests()"
        print arsutils.exceptionAsStr(ex)

def cmpFieldCount(e1,e2):
    return cmp(e2[1],e1[1])

def buildDailySummaryStats(day):
    requests = g_dailyStats[day]
    reqCount = 0
    failedReqCount = 0
    fieldCounts = {}
    failedFieldCounts = {}
    for reqData in requests:
        assert reqData.log_date == day
        reqCount += 1
        request = reqData.request
        (fieldName,fieldValue) = parseRequestLine(request)
        if fieldCounts.has_key(fieldName):
            fieldCounts[fieldName] = fieldCounts[fieldName] + 1
        else:
            fieldCounts[fieldName] = 1

        if None != reqData.error:
            if failedFieldCounts.has_key(fieldName):
                failedFieldCounts[fieldName] = failedFieldCounts[fieldName] + 1
            else:
                failedFieldCounts[fieldName] = 1
            failedReqCount += 1

 
    txt = "day: %s\n" % day
    txt += "  total  requests: %d\n" % reqCount
    txt += "  failed requests: %d\n" % failedReqCount

    txt += "  FAILED requests aggregated counts:\n"
    sorted = failedFieldCounts.items()
    sorted.sort(cmpFieldCount)
    for item in sorted:
        txt += "  %4d %s\n" % (item[1], item[0])

    txt += "  OK requests aggregated counts:\n"
    sorted = fieldCounts.items()
    sorted.sort(cmpFieldCount)
    for item in sorted:
        txt += "  %4d %s\n" % (item[1], item[0])
    return txt

def buildDailyDetailedStats(day):
    perFieldData = {}
    requests = g_dailyStats[day]
    for reqData in requests:
        request = reqData.request
        (fieldName,fieldValue) = parseRequestLine(request)
        if None == fieldValue:
            continue
        if perFieldData.has_key(fieldName):
            perFieldData[fieldName].append(fieldValue)
        else:
            perFieldData[fieldName] = [fieldValue]
    sortedFieldNames = perFieldData.keys()
    sortedFieldNames.sort()
    txt = "day: %s\n" % day
    for fieldName in sortedFieldNames:
        txt = "%s%s\n" % (txt, fieldName)
        for fieldValue in perFieldData[fieldName]:
            txt = "%s   %s\n" % (txt, fieldValue)
    return txt

# process data retrieved via retrieveUsers()
def processUsers():
    global g_userStats
    totalUsers = 0
    totalPalmUsers = 0
    totalPocketPCUsers = 0
    totalSmartphoneUsers = 0
    totalTestClientUsers = 0
    registeredUsers = 0
    palmRegisteredUsers = 0
    pocketPCRegisteredUsers = 0
    smartphoneRegisteredUsers = 0
    testClientRegisteredUsers = 0
    newTotalUsers = 0
    newRegisteredUsers = 0
    newUsersInfo = []

    deviceStats = {}

    for userData in g_userStats:
        fReg = userData.isRegistered()

        totalUsers += 1
        if fReg:
            registeredUsers += 1

        if DEV_PALM == userData.deviceType():
            totalPalmUsers += 1
            if fReg:
                palmRegisteredUsers += 1
        elif DEV_POCKET_PC == userData.deviceType():
            totalPocketPCUsers += 1
            if fReg:
                pocketPCRegisteredUsers += 1
        elif DEV_SMARTPHONE == userData.deviceType():
            totalSmartphoneUsers += 1
            if fReg:
                smartphoneRegisteredUsers += 1
        elif DEV_TEST_CLIENT:
            totalTestClientUsers += 1
            if fReg:
                testClientRegisteredUsers += 1

        deviceName = userData.deviceName()
        if None != deviceName:
            if deviceStats.has_key(deviceName):
                deviceStats[deviceName] = deviceStats[deviceName] + 1
            else:
                deviceStats[deviceName] = 1

        if userData.new_user_p == True:
            newTotalUsers += 1
            if fReg:
                newRegisteredUsers += 1

    result  = "Users:     %5d, registered: %5d\n" % (totalUsers, registeredUsers)
    result += "New users: %5d, registered: %5d\n" % (newTotalUsers, newRegisteredUsers)
    result += "Palm: %d/%d, Smartphone: %d/%d, Pocket PC: %d/%d, test client: %d/%d\n" % (totalPalmUsers, palmRegisteredUsers, totalSmartphoneUsers, smartphoneRegisteredUsers, totalPocketPCUsers, pocketPCRegisteredUsers, totalTestClientUsers, testClientRegisteredUsers)

    result += "\n"
    # TODO: sort by count
    devStatsSorted = []
    for (deviceName, count) in deviceStats.items():
        devStatsSorted.append( (deviceName, count) )

    devStatsSorted.sort(cmpFieldCount)

    for deviceInfo in devStatsSorted:
        deviceName = deviceInfo[0]
        count = deviceInfo[1]
        result += " %s: %d\n" % (deviceName, count)

    result += "\n"
    for userData in g_userStats:
        if userData.new_user_p == True:
            if userData.isRegistered():
                result += "* %s\n" % userData.deviceInfoAsTxt()
            else:
                result += "  %s\n" % userData.deviceInfoAsTxt()
    return result

# process request data retrieved via retrieveRequests()
def processRequests():
    global g_lastRequestLogId, g_dailyStats, g_modifiedDays

    result = ""
    daysSorted = g_modifiedDays.keys()
    daysSorted.sort()
    dailyStats = []
    dailyDetailedStats = []
    for day in daysSorted:
        txt = buildDailySummaryStats(day)
        dailyStats.append(txt)
        txt = buildDailyDetailedStats(day)
        dailyDetailedStats.append(txt)

    dailyStats.reverse()
    txt = string.join(dailyStats, "\n")

    result += txt
    dailyDetailedStats.reverse()
    txt = string.join(dailyDetailedStats, "\n")
    result += txt
    return result

def main():
    toMail = ""
    try:
        unpickleState()
        #retrieveRequests()
        retrieveUsers()
        txt = processUsers()
        toMail += txt
        #txt = processRequests()
        #toMail += "\n"
        #toMail += txt
    finally:
        deinitDatabase()
        pickleState()
    #if not fDbExists:
    #    toMail = "ipedia_manage database doesn't exist. Something's rotten in Denmark.";
    mailTxt(toMail)

if __name__ == "__main__":
    main()

