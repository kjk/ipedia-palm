#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# Purpose: verify that redirects (data in the 'redirects' table) point
#   to real articles (data in articles table) 
#
# Usage:
#   -db name  : use database name
#   -listdbs  : list all available ipedia databases

import sys, re, random, datetime, MySQLdb, _mysql_exceptions
import arsutils,iPediaDatabase,iPediaServer
try:
    import psyco
    psyco.full()
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"

ipediaRe = re.compile("ipedia_[0-9]{8}", re.I)

g_conn = None
g_dbName = None

def getConn():
    global g_conn, g_dbName
    if None == g_conn:
        g_conn = MySQLdb.Connect(host=iPediaDatabase.DB_HOST, user=iPediaDatabase.DB_USER, passwd=iPediaDatabase.DB_PWD, db=g_dbName)
    return g_conn

def closeConn():
    global g_conn
    if None != g_conn:
        g_conn.close()
        g_conn = None

def fRedirectValid(redirect):
    conn = getConn()
    cur = conn.cursor()
    cur.execute("SELECT title FROM articles WHERE title='%s'" % conn.escape_string(redirect))
    row = cur.fetchone()
    cur.close()
    if row==None:
        return False
    return True

def validateRedirects():
    print "Reading all redirects into memory"
    conn = getConn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM redirects")
    row = cur.fetchone()
    redirectsCount = row[0]
    print "Number of redirects: %d" % redirectsCount

    cur.execute("SELECT title,redirect FROM redirects")
    redirects = {}
    allRows = cur.fetchall()
    count = len(allRows)
    for row in allRows:
        title = row[0]
        redirect = row[1]
        redirects[title] = redirect
    print "Loaded %d redirects, starting to validate redirects" % count
    count = 0
    invalidCount = 0
    for (title,redirect) in redirects.items():
        fValid = fRedirectValid(redirect)
        if not fValid:
            print "'%s' INVALID" % title
            invalidCount += 1
        count += 1    
        if 0 == (count % 1000):
            print "Validated %d redirects, last title='%s'" % (count,title)
    print "%d invalid redirects" % invalidCount

def main():
    global g_dbName
    dbs = iPediaServer.getIpediaDbList()
    if 0==len(dbs):
        print "No databases available"

    dbs.sort()

    fListDbs = arsutils.fDetectRemoveCmdFlag("-listdbs")
    if fListDbs:
        for dbName in dbs:
            print dbName
        sys.exit(0)

    dbName=arsutils.getRemoveCmdArg("-db")

    if dbName:
        if dbName in dbs:
            print "Using database '%s'" % dbName
        else:
            print "Database '%s' doesn't exist" % dbName
            print "Available databases:"
            for name in dbs:
                print "  %s" % name
            sys.exit(0)
    else: 
        dbName=dbs[-1] # use the latest database

    print "Using database '%s'" % dbName
    g_dbName = dbName
    validateRedirects()
    closeConn()

if __name__ == "__main__":
    main()

