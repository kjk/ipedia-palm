
from mod_python import apache
import os, MySQLdb, _mysql_exceptions, arsutils

DB_HOST        = 'localhost'
DB_USER        = 'ipedia'
DB_PWD         = 'ipedia'
MANAGEMENT_DB  = 'ipedia_manage'

def _singleResult(db, query):
    cursor=db.cursor()
    cursor.execute(query)
    row=cursor.fetchone()
    cursor.close()
    if not row:
        return None
    else:
        return row[0]

def _getAllRows(db, query):
    cursor=db.cursor()
    cursor.execute(query)
    rows=cursor.fetchall()
    cursor.close()
    return rows

def _readTemplate(req):
    dirElems=req.canonical_filename.split("/")
    dirElems.pop()
    dirElems.append("stats.html")
    path=os.sep.join(dirElems)
    f=file(path, "r")
    txt=f.read()
    f.close()
    return txt
    
def _connect():
    return MySQLdb.Connect(host=DB_HOST, user=DB_USER, passwd=DB_PWD, db=MANAGEMENT_DB)
    
def _dayOrDays(num):
    if 1==num:
        return "%d day" % num
    else:
        return "%d days" % num
        
def _avgPerDay(num, days):
    return "%d (%.2f per day)" % (num, float(num)/float(days))

def _findValueForDate(rows, date):
    for row in rows:
        if row[0] == date:
            return row[1]
    return 0;
    
def _weeklyDailyStats(db, body, header, regsQuery, lookupsQuery, limit):
    body=body+"""
<table id="stats" cellspacing="0">
<tr class="header">
    <td>%s</td>
    <td>Regs</td>
    <td>Lookups</td>
</tr>""" % header
    regsRows=_getAllRows(db, regsQuery)
    lookupsRows=_getAllRows(db, lookupsQuery)
    rowsCount=0
    selected=False
    for row in lookupsRows:
        issueDate=row[0]
        lookupsCount=row[1]
        regsCount=_findValueForDate(regsRows, issueDate)
        if selected:
            body=body+"<tr class=\"selected\">\n"
            selected=False
        else:
            body=body+"<tr>\n"
            selected=True
        if "Day"==header:
            body=body+"  <td><a href=\"dailyStats?date=%s\">%s</a></td>\n" % (issueDate, issueDate)
        else:
            body=body+"<td>%s</td>\n" % issueDate
        
        body=body+"  <td>%d</td>\n" % regsCount
            
        if "Day"==header:
            body=body+"  <td><a href=\"dailyLookupsStats?date=%s\">%d</a></td>\n" % (issueDate, lookupsCount)
        else:
            body=body+"  <td>%d</td>\n" % lookupsCount
                        
        rowsCount=rowsCount+1
        if limit>0 and rowsCount>=limit:
            break
    body=body+"</table>\n"  
    return (body, rowsCount)
    
def _recentRegistrations(db, limit):
    body="""
<table id="stats" cellspacing="0">
<tr class="header">
  <td>Date</td>
  <td>Name</td>
  <td>Device</td>
</tr>"""
    query="SELECT cookie, device_info, DATE_FORMAT(issue_date, '%%Y-%%m-%%d') AS when_created, registered_users.id FROM cookies LEFT JOIN registered_users on cookies.id=registered_users.cookie_id ORDER BY when_created DESC LIMIT %d" % limit
    cursor=db.cursor()
    cursor.execute(query)
    row=cursor.fetchone()
    selected = False;
    while row:
        whenCreated=row[2]
        devInfo=row[1]
        if (selected):
            selected=False
            body=body+"<tr class=\"selected\">\n"
        else:
            selected=True
            body=body+"<tr>\n"

        body=body+"  <td>%s</td>\n" % whenCreated
        decodedDevInfo = arsutils.decodeDi(devInfo)
        deviceName=decodedDevInfo["device_name"]
        hotsyncName="Unavailable"
        if decodedDevInfo.has_key("HS"):
            hotsyncName=decodedDevInfo["HS"]
        body=body+"  <td>%s</td>\n" % hotsyncName
        body=body+"  <td>%s</td>\n" % deviceName
        body=body+"</tr>\n"
        row=cursor.fetchone()
    cursor.close()
    body=body+"</table>\n"
    return body
    
def _recentLookups(db, limit):
    body="""
<table id="stats" cellspacing="0">
<tr class="header">
  <td>Title 1</td>
  <td>Title 2</td>
  <td>Title 3</td>
</tr>"""
    limit=limit*3
    query= "SELECT requested_term, request_date FROM requests WHERE requested_term IS NOT NULL AND error=0 ORDER BY request_date DESC LIMIT %d" % limit
    cursor=db.cursor()
    cursor.execute(query)
    row=cursor.fetchone()
    selected = False
    whichWord = 1
    word1=None
    word2=None
    word3=None
    while row:
        if 1==whichWord:
            word1 = row[0]
        elif 2==whichWord:
            word2 = row[0]
        elif 3==whichWord:
            word3 = row[0]
        whichWord = whichWord+1
        if 4==whichWord:
            whichWord = 1;
            if selected:
                selected=False
                body=body+"<tr class=\"selected\">\n"
            else:
                selected=True
                body=body+"<tr>\n"
            body=body+"  <td>%s</td>\n" % word1
            body=body+"  <td>%s</td>\n" % word2
            body=body+"  <td>%s</td>\n" % word3
            body=body+"</tr>\n"
        row=cursor.fetchone()
    cursor.close()        
    body=body+"</table>\n"
    return body
    
def _statsCmp(a, b):
    sn1, sc1=a
    sn2, sc2=b
    if sn1==sn2:
        return 0
    elif sn1<sn2:
        return -1
    else:
        return 1
    
def _getDeviceStats(db):
    cursor=db.cursor()
    query="SELECT DISTINCT device_info FROM cookies"
    cursor.execute(query)
    statsDict=dict()
    for row in cursor:
        deviceInfo=row[0]
        devInfoDec=arsutils.decodeDi(deviceInfo)
        devName=devInfoDec["device_name"]
        if statsDict.has_key(devName):
            statsDict[devName]=statsDict[devName]+1
        else:
            statsDict[devName]=1
    cursor.close()
    stats=statsDict.items()
    stats.sort(_statsCmp)
    return stats
    
def _showDeviceStats(db):
    body="""
<table id="stats" cellspacing="0">
<tr class="header">
  <td>Device name</td>
  <td>Count</td>
</tr>"""
    stats=_getDeviceStats(db)
    selected = False
    for stat in stats:
        deviceName, count=stat
        if selected:
            selected=False
            body=body+"<tr class=\"selected\">\n"
        else:
            selected=True
            body=body+"<tr>\n"
        body=body+"  <td>%s</td>\n" % deviceName
        body=body+"  <td>%d</td>\n" % count
        body=body+"</tr>\n"
    body=body+"</table>\n"
    return body

    
def summary(req):
    contents=_readTemplate(req)
    body="<b>Summary</b>&nbsp;|&nbsp;<a href=\"activeUsers\">Active users</a><p>"
    db=_connect()
    uniqueCookies=_singleResult(db, "SELECT COUNT(*) FROM cookies")
    days=_singleResult(db, "SELECT TO_DAYS(MAX(request_date))-TO_DAYS(MIN(request_date))+1 FROM requests WHERE requested_term IS NOT NULL AND error=0")
    totalRequests=_singleResult(db, "SELECT COUNT(*) FROM requests")
    
    body=body+("iPedia has been published for %s. <br>" % _dayOrDays(days))
    body=body+("Unique cookies created: %s. <br>" % _avgPerDay(uniqueCookies, days))
    body=body+("Total requests: %s which is %.2f per unique device (unique user?). <br> <p>" % (_avgPerDay(totalRequests, days), float(totalRequests)/float(uniqueCookies)))
    body=body+"""
    <p>
    <table>
    <tr>
      <td>Weekly stats</td>
      <td>Daily stats</td>
    </tr>
    <tr>
        <td>"""
    regsQuery="SELECT DATE_FORMAT(issue_date, '%Y-%U') AS when_date, COUNT(*) AS regs_count FROM cookies GROUP BY when_date ORDER BY when_date DESC"
    lookupsQuery="SELECT DATE_FORMAT(request_date, '%Y-%U') AS when_date, COUNT(*) AS lookups_count FROM requests WHERE requested_term IS NOT NULL AND error=0 GROUP BY when_date ORDER BY when_date DESC"
    body, rowsCount=_weeklyDailyStats(db, body, "Week", regsQuery, lookupsQuery, 10)
    body=body+"""
        </td>
        <td>"""
    regsQuery="SELECT DATE_FORMAT(issue_date, '%Y-%m-%d') AS when_date, COUNT(*) AS regs_count FROM cookies GROUP BY when_date ORDER BY when_date DESC"
    lookupsQuery="SELECT DATE_FORMAT(request_date, '%Y-%m-%d') AS when_date, COUNT(*) AS lookups_count FROM requests WHERE requested_term IS NOT NULL AND error=0 GROUP BY when_date ORDER BY when_date DESC"
    body, ignore=_weeklyDailyStats(db, body, "Day", regsQuery, lookupsQuery, 10)
    body=body+"""
        </td>
    </tr>
    </table>
    <p>
    <table>
    <tr>
      <td>Recent registrations</td>
      <td>Recent lookups</td>
    </tr>
    <tr>
        <td>"""
    limit=20
    body=body+_recentRegistrations(db, limit)
    body=body+"""
        </td>
        <td>"""
    body=body+_recentLookups(db, limit)
    body=body+"""
        </td>
    </tr>
    </table>"""
    body=body+_showDeviceStats(db)        
    
    db.close()
    return contents % body

def activeUsers(req):
    contents=_readTemplate(req)
    body="""
<a href="summary">Summary</a>&nbsp;|&nbsp;
<b>Active users</b>
<p>"""
    db=_connect()
    rows=_getAllRows(db, "SELECT COUNT(cookie_id) AS cnt, cookie_id FROM requests INNER JOIN cookies ON requests.cookie_id=cookies.id GROUP BY cookie_id HAVING cnt>9")
    usersCount=len(rows)
    body=body+"Active users (made more than 9 requests): %d<p>" % usersCount
    body=body+"""
    <table id="stats" cellspacing="0">
    <tr class="header">
      <td>User</td>
      <td>Device</td>
      <td>Total</td>
      <td>Days registered</td>
      <td>Lookups per day</td>
    </tr>"""
    cursor=db.cursor()
    cursor.execute("SELECT COUNT(cookie_id) AS cnt, cookie_id, device_info, TO_DAYS(NOW())-TO_DAYS(issue_date)+1 FROM requests INNER JOIN cookies ON requests.cookie_id=cookies.id GROUP BY cookie_id ORDER BY cnt DESC")
    selected=False
    for row in cursor:
        totalLookupsCount=row[0]
        if totalLookupsCount<10:
            break
        cookieId=row[1]
        devInfo=row[2]
        daysReg=row[3]
        devInfoDec=arsutils.decodeDi(devInfo)
        devName=devInfoDec["device_name"]
        hsName="Unavailable"
        if devInfoDec.has_key("HS"):
            hsName=devInfoDec["HS"]
        reqCount=_singleResult(db, "SELECT COUNT(*) FROM requests WHERE cookie_id=%d" % cookieId)
        if selected:
            body=body+"<tr class=\"selected\">\n"
            selected=False
        else:
            body=body+"<tr>\n"
            selected=True
        body=body+"  <td><a href=\"userStats?cookieId=%d\">%s</a></td>\n" % (cookieId, hsName)
        body=body+"  <td>%s</td>\n" % devName
        body=body+"  <td>%d</td>\n" % reqCount
        body=body+"  <td>%d</td>\n" % daysReg
        body=body+"  <td>%.2f</td>\n" % (float(reqCount)/float(daysReg))
        body=body+"</tr>\n"
    cursor.close()
    body=body+"</table>\n"
    return contents % body
    
def dailyStats(req, date):
    contents=_readTemplate(req)
    body="""
<a href="summary">Summary</a>&nbsp;|&nbsp;
<b>Daily per user stats for %s</b>&nbsp;|&nbsp;
<a href=\"dailyLookupsStats?date=%s\">Daily lookup stats for %s&nbsp;</a>
<p>""" % (date, date, date)
    body=body+"""
    <table id="stats" cellspacing="0">
    <tr class="header">
      <td>User</td>
      <td>Device</td>
      <td>Today</td>
      <td>Total</td>
      <td>Days registered</td>
      <td>Lookups per day</td>
    </tr>"""
    db=_connect()
    cursor=db.cursor()
    query="SELECT COUNT(cookie_id) AS cnt, cookie_id, TO_DAYS(request_date)-TO_DAYS(issue_date)+1, device_info FROM requests INNER JOIN cookies on requests.cookie_id=cookies.id WHERE DATE_FORMAT(request_date, '%%Y-%%m-%%d')='%s' AND requested_term IS NOT NULL AND error=0 GROUP BY cookie_id ORDER BY cnt DESC" % date
    cursor.execute(query)
    selected = False
    for row in cursor:
        lookupsCount=row[0]
        cookieId=row[1]
        daysReg=row[2]
        devInfo=row[3]
        devInfoDec=arsutils.decodeDi(devInfo)
        devName=devInfoDec["device_name"]
        hsName="Unavailable"
        if devInfoDec.has_key("HS"):
            hsName=devInfoDec["HS"]
        totalLookupsCount=_singleResult(db, "SELECT COUNT(*) FROM requests WHERE cookie_id=%d AND requested_term IS NOT NULL AND error=0" % cookieId)

        if selected:
            body=body+"<tr class=\"selected\">\n"
            selected=False
        else:
            body=body+"<tr>\n"
            selected=True

        body=body+"  <td><a href=\"userStats?cookieId=%d\">%s</a></td>\n" % (cookieId, hsName)
        body=body+"  <td>%s</td>\n" % devName
        body=body+"  <td>%d</td>\n" % lookupsCount
        body=body+"  <td>%d</td>\n" % totalLookupsCount
        body=body+"  <td>%d</td>\n" % daysReg
        body=body+"  <td>%.2f</td>\n" % (float(totalLookupsCount)/float(daysReg))
        body=body+"</tr>\n"
    cursor.close()
    body=body+"</table>\n"
    return contents % body  
    
def userStats(req, cookieId):
    contents=_readTemplate(req)
    body="""
<a href="summary">Summary</a>&nbsp;|&nbsp;
<b>User info for user with cookie_id %d</b>
<p>""" % int(cookieId)
    return contents % body

def dailyLookupsStats(req, date):
    contents=_readTemplate(req)
    body="""
<a href="summary">Summary</a>&nbsp;|&nbsp;
<a href=\"dailyStats?date=%s\">Daily per user stats for %s</a>&nbsp;|&nbsp;
<b>Daily lookup stats for %s&nbsp;</b>
<p>""" % (date, date, date)
    body=body+"""
    <table id="stats" cellspacing="0">
    <tr class="header">
      <td>Word requested</td>
      <td>Word found</td>
      <td>User</td>
      <td>Total requests</td>
      <td>Days registered
      <td>Lookups per day</td>
    </tr>"""
    db=_connect()
    cursor=db.cursor()
    query="SELECT requested_term, cookie_id, TO_DAYS(request_date)-TO_DAYS(issue_date)+1, device_info, definition_for FROM requests INNER JOIN cookies on requests.cookie_id=cookies.id WHERE DATE_FORMAT(request_date, '%%Y-%%m-%%d')='%s' AND requested_term IS NOT NULL AND error=0" % date
    cursor.execute(query)
    selected=False
    for row in cursor:
        term=row[0]
        cookieId=row[1]
        daysReg=row[2]
        devInfo=row[3]
        defFor=row[4]
        devInfoDec=arsutils.decodeDi(devInfo)
        devName=devInfoDec["device_name"]
        hsName="Unavailable"
        if devInfoDec.has_key("HS"):
            hsName=devInfoDec["HS"]
        totalLookups=_singleResult(db, "SELECT COUNT(*) FROM requests WHERE cookie_id=%d AND requested_term IS NOT NULL AND error=0" % cookieId)
        if selected:
            body=body+"<tr class=\"selected\">\n"
            selected=False
        else:
            bod=body+"<tr>\n"
            selected=True
        body=body+"  <td>%s</td>\n" % term
        if not defFor:
            defFor="[Not found]"
        body=body+"  <td>%s</td>\n" % defFor
        body=body+"  <td><a href=\"userStats?cookieId=%d\">%s</a></td>\n" % (cookieId, hsName)
        body=body+"  <td>%d</td>\n" % totalLookups
        body=body+"  <td>%d</td>\n" % daysReg
        body=body+"  <td>%.2f</td>\n" % (float(totalLookups)/float(daysReg))
        body=body+"</tr>\n"
    cursor.close()
    body=body+"</table>\n"
    return contents % body
    
def index(req):
    return summary(req)

    
    
