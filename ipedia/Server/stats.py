
from mod_python import apache
import os, MySQLdb, _mysql_exceptions, iPediaDatabase, arsutils

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
    return MySQLdb.Connect(host=iPediaDatabase.DB_HOST, user=iPediaDatabase.DB_USER, passwd=iPediaDatabase.DB_PWD, db=iPediaDatabase.MANAGEMENT_DB)
    
def _dayOrDays(num):
    if 1==num:
        return "%d day" % num
    else:
        return "%d days" % num
        
def _avgPerDay(num, days):
    return "%d (%.2f per day)" % (num, float(num)/float(days))

def _findLookupsForDate(lookupsRows, date):
    for row in lookupsRows:
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
    for row in regsRows:
        issueDate=row[0]
        regsCount=row[1]
        lookupsCount=_findLookupsForDate(lookupsRows, issueDate)
        if selected:
            body=body+"<tr class=\"selected\">\n"
            selected=False
        else:
            body=body+"<tr>\n"
            selected=True
        if "Day"==header:
            body=body+"  <td><a href=\"stats.py/daily?date=%s\">%s</a></td>\n" % (issueDate, issueDate)
        else:
            body=body+"<td>%s</td>\n" % issueDate
        
        body=body+"  <td>%d</td>\n" % lookupsCount
            
        if "Day"==header:
            body=body+"  <td><a href=\"stats.py/daily_lookups?date=%s\">%d</a></td>\n" % (issueDate, lookupsCount)
        else:
            body=body+"  <td>%d</td>\n" % lookupsCount
                        
        rowsCount=rowsCount+1
        if limit>0 and rowsCount>=limit:
            break
    body=body+"</table>\n"  
    return (body, rowsCount)
    
def summary(req):
    contents=_readTemplate(req)
    body="<b>Summary</b>&nbsp;|&nbsp;<a href=\"stats.py/active_users\">Active users</a><p>"
    db=_connect()
    uniqueCookies=_singleResult(db, "SELECT COUNT(*) FROM cookies")
    days=_singleResult(db, "SELECT TO_DAYS(MAX(issue_date))-TO_DAYS(MIN(issue_date)) FROM cookies")
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
    lookupsQuery="SELECT DATE_FORMAT(request_date, '%Y-%U') AS when_date, COUNT(*) AS lookups_count FROM requests GROUP BY when_date ORDER BY when_date DESC"
    body, rowsCount=_weeklyDailyStats(db, body, "Week", regsQuery, lookupsQuery, -1)
    body=body+"""
        </td>
        <td>"""
    regsQuery="SELECT DATE_FORMAT(issue_date, '%Y-%m-%d') AS when_date, COUNT(*) AS regs_count FROM cookies GROUP BY when_date ORDER BY when_date DESC"
    lookupsQuery="SELECT DATE_FORMAT(request_date, '%Y-%m-%d') AS when_date, COUNT(*) AS lookups_count FROM requests GROUP BY when_date ORDER BY when_date DESC"
    body, ignore=_weeklyDailyStats(db, body, "Day", regsQuery, lookupsQuery, rowsCount)
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
    
    db.close()
    return contents % body
        
    
def index(req):
    return summary(req)

    
    