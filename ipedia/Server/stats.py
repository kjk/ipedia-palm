
from mod_python import apache
import os, MySQLdb, _mysql_exceptions, iPediaDatabase, arsutils

def _singleResult(db, query):
	cursor=db.cursor()
	cursor.execute(query)
	row=cursor.fetchone()
	if not row:
		return None
	else:
		return row[0]

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
	
def summary(req):
	contents=_readTemplate(req)
	body="<b>Summary</b>&nbsp;|&nbsp;<a href=\"stats.php/active_users\">Active users</a><p>"
	db=_connect()
	uniqueCookies=_singleResult(db, "SELECT COUNT(*) FROM cookies")
	days=_singleResult(db, "SELECT TO_DAYS(MAX(issue_date))-TO_DAYS(MIN(issue_date)) FROM cookies")
	totalRequests=_singleResult(db, "SELECT COUNT(*) FROM requests")
	
	body=body+("iNoah has been published for %s. <br>" % _dayOrDays(days))
	body=body+("Unique cookies created: %s. <br>" % _avgPerDay(uniqueCookies, days))
	body=body+("Total requests: %s which is %.2f per unique device (unique user?). <br> <p>" % (_avgPerDay(totalRequests, days), float(totalRequests)/float(uniqueCookies)))
    
	db.close()
	return contents % body
		
	
def index(req):
	return summary(req)

	
	