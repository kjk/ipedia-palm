# Copyright: Krzysztof Kowalczyk
# Owner: Andrzej Ciarkowski
#
# Creates iPedia database from wikipedia sql dump
#
# Command line parameters:
#  -recreatedb : if given, recreate ipedia database
#  -recreatedatadb : if given, recreate ipedia data database
#  -verbose : if used will print a lot of debugging input to stdout. May slow
#             down conversion process
#  -limit n : limit the number of converter articles to N. This is good for testing
#             changes to the converter. It takes a lot of time to fetch all
#             original articles from enwiki db, this option will limit it to N
#             articles which should be enough to detect major problems with
#             the converter
# -showdups : sets g_fShowDups to True. The idea is that if we convert to an empty ipedia.articles
#             database, we should never have duplicates. If we have it means that we're loosing
#             some of the original articles. With this flag we dump dups to stdout.
#             Don't use if ipedia.articles isn't empty
# -nopsyco : if used, won't use psyco
# fileName : convert directly from sql file, no need for enwiki.cur database

import sys, os, MySQLdb
import  arsutils, wikipediasql,articleconvert
try:
    import psyco
    g_fPsycoAvailable = True
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"
    g_fPsycoAvailable = False

# if True, we'll print a lot of debug text to stdout
g_fVerbose       = False

# if True, we'll show if we're updating ipedia table twice for the same title
# shouldn't happen if it was empty to begin with
g_fShowDups      = False

g_connRoot       = None
g_connIpedia     = None
g_connIpediaDbName = None

g_dbName = None

MANAGEMENT_DB = 'ipedia_manage'

def usageAndExit():
    print "wikiToDbConvert.py [-verbose] [-limit n] [-showdups] [-nopsyco] [-recreatedb] [-recreatedatadb] sqlDumpName"
    sys.exit(0)

def getOneResult(conn,query):
    cur = conn.cursor()
    cur.execute(query)
    row = cur.fetchone()
    res = row[0]
    cur.close()
    return res

def getRootConnection():
    global g_connRoot
    if g_connRoot:
        return g_connRoot
    g_connRoot = MySQLdb.Connect(host='localhost', user='root', passwd='', db='')
    return g_connRoot

def getIpediaConnection(dbName):
    global g_connIpedia, g_connIpediaDbName
    if dbName==None:
        assert g_connIpedia
        return g_connIpedia
    if g_connIpedia:
        assert dbName == g_connIpediaDbName
    g_connIpedia = MySQLdb.Connect(host='localhost', user='ipedia', passwd='ipedia', db=dbName)
    g_connIpediaDbName = dbName
    return g_connIpedia

g_ipediaRowCount = None
def getIpediaRowCount():
    global g_ipediaRowCount
    if None == g_ipediaRowCount:
        conn = getIpediaConnection(None)
        g_ipediaRowCount = getOneResult(conn, """SELECT COUNT(*) FROM ipedia.articles;""")
    return g_ipediaRowCount

def printIpediaRowCount():
    ipediaRows = getIpediaRowCount()
    sys.stderr.write("rows in ipedia: %d\n" % ipediaRows)

def deinitDatabase():
    global g_connIpedia, g_connRoot
    print "deinitDatabase()"
    closeAllNamedCursors()
    if g_connIpedia:
        g_connIpedia.close()
    if g_connRoot:
        g_connRoot.close()

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
    global g_connIpedia
    return g_connIpedia.escape_string(txt)

# Given a title of the article (title) the title of the article
# to which it's redirected (cur_redirect), a hash of all redirects
# (allRedirects) and hash containing titles of all non-redirect articles
# (allArticles) find the title of final non-redirect article (i.e. eliminate
# chained redirects). Return None if the redirect is invalid (i.e. the article
# to which it tries to redirect doesn't exist)
def resolveRedirect(title,cur_redirect, allRedirects, allArticles):
    # check for (hopefuly frequent) case: this a valid, direct redirect
    if allArticles.has_key(cur_redirect):
        return cur_redirect
    visited = [title]
    visited.append(cur_redirect)
    while True:
        if allArticles.has_key(cur_redirect):
            # this points to a valid article, so we resolved the redirect
            return cur_redirect
        if allRedirects.has_key(cur_redirect):
            # there is some other redirects for this -> keep looking
            cur_redirect = allRedirects[cur_redirect]
            if cur_redirect in visited:
                #print "found circular redirect: %s" % cur_redirect
                break
            visited.append(cur_redirect)
        else:
            # no more redirects -> we couldn't resolve the redirect
            break
    dumpUnresolvedRedirect(visited)
    return None

class UnresolvedRedirectsWriter:
    def __init__(self,sqlDumpName):
        self.fileName = wikipediasql.genBaseAndSuffix(sqlDumpName,"_unres_redirects.txt")
        self.fo = None
    def open(self):
        assert self.fo == None
        self.fo = open(self.fileName,"wb")
    def write(self,visited):
        n = 0
        for txt in visited:
            if n==0:
                # this is title
                self.fo.write(": %s\n" % txt.strip())
            else:
                self.fo.write("  %s\n" % txt.strip())
            n+=1
    def close(self):        
        if self.fo:
            self.fo.close()

g_redirectsWriter = None

def dumpUnresolvedRedirect(visited):
    global g_redirectsWriter
    if g_redirectsWriter:
        g_redirectsWriter.write(visited)

def setUnresolvedRedirectWriter(sqlDump):
    global g_redirectsWriter
    assert None == g_redirectsWriter
    g_redirectsWriter = UnresolvedRedirectsWriter(sqlDump)
    g_redirectsWriter.open()

class ConvertedArticle:
    def __init__(self,ns,title,txt):
        self.ns = ns
        self.title = title
        self.txt = txt
    def getText(self): return self.txt
    def getNamespace(self): return self.ns
    def fRedirect(self): return False
    def getTitle(self): return self.title

class ConvertedArticleRedirect:
    def __init__(self,ns,title,redirect):
        self.ns = ns
        self.title = title
        self.redirect = redirect
    def getTitle(self): return self.title
    def fRedirect(self): return True
    def getRedirect(self): return self.redirect
    def getNamespace(self): return self.ns

def getDbNameFromFileName(sqlFileName):
    base = os.path.basename(sqlFileName)
    txt = wikipediasql.getBaseFileName(base)
    pos = txt.find("_cur_table")
    date = txt[:pos]
    dbName = "ipedia_%s" % date
    return dbName

# First pass: go over all articles, either directly from
# sql dump or from cache and gather the following cache
# data:
#   - all redirects
#   - extract link from articles
# Second pass: do the conversion, including veryfing links and put
# converted articles in the database.
# TODO: do something about case-insensitivity. Article titles in Wikipedia are
# case-sensitive but our title column in the database is not. Currently we just
# over-write. It's ok for redirects but for real articles we need to investigate
# how often that happens and decide what to do about that
def convertArticles(sqlDump,dbName,articleLimit):
    count = 0
    redirects = {}
    articleTitles = {}
    fTesting = False
    if fTesting:
        fUseCache = False
        fRecreateCache = True
    else:
        fUseCache = True
        fRecreateCache = False
    for article in wikipediasql.iterWikipediaArticles(sqlDump,articleLimit,fUseCache,fRecreateCache):
        # we only convert article from the main namespace
        assert article.getNamespace() == wikipediasql.NS_MAIN
        title = article.getTitle()
        if article.fRedirect():
            redirects[title] = article.getRedirect()
        else:
            txt = article.getText()
            links = articleconvert.articleExtractLinks(txt)
            #articleTitles[title] = links
            articleTitles[title] = 1
        count += 1
        if 0 == count % 1000:
            sys.stderr.write("processed %d rows, last title=%s\n" % (count,title.strip()))
        if articleLimit and count >= articleLimit:
            break
    # verify redirects
    print "Number of real articles: %d" % len(articleTitles)
    print "Number of all redirects: %d (%d in total)" % (len(redirects), len(articleTitles)+len(redirects))
    unresolvedCount = 0
    setUnresolvedRedirectWriter(sqlDump)
    redirectsExisting = {}
    for (title,redirect) in redirects.items():
        redirectResolved = resolveRedirect(title,redirect,redirects,articleTitles)
        if None == redirectResolved:
            unresolvedCount +=1
            #print "redirect '%s' (to '%s') not resolved" % (title,redirect)
        else:
            redirectsExisting[title] = redirectResolved
    print "Number of unresolved redirects: %d" % unresolvedCount

    ipedia_write_cur = getNamedCursor(getIpediaConnection(dbName), "ipedia_write_cur")
        
    # go over articles again (hopefully now using the cache),
    # convert them to a destination format (including removing invalid links)
    # and insert into a database
    sizeStats = {}
    count = 0
    convWriter = wikipediasql.ConvertedArticleCacheWriter(sqlDump)
    convWriter.open()
    for article in wikipediasql.iterWikipediaArticles(sqlDump,articleLimit,True,False):
        title = article.getTitle()
        articleSize = 0 # 0 is for redirects, which we don't log
        if article.fRedirect():
            convertedArticle = ConvertedArticleRedirect(article.getNamespace(), title, article.getRedirect())
        else:
            txt = article.getText()
            converted = articleconvert.convertArticle(title,txt)
            noLinks = articleconvert.removeInvalidLinks(converted,redirects,articleTitles)
            if noLinks:
                converted = noLinks
            convertedArticle = ConvertedArticle(article.getNamespace(), article.getTitle(), converted)
            articleSize = len(converted)

        #title = title.lower()
        if article.fRedirect():
            if redirectsExisting.has_key(title):
                redirect = redirectsExisting[title]
                try:
                    title = title.replace("_", " ")
                    redirect = redirect.replace("_", " ")
                    ipedia_write_cur.execute("""INSERT INTO redirects (title, redirect) VALUES ('%s', '%s')""" % (dbEscape(title), dbEscape(redirect)))
                except:
                    print "DUP REDERICT '%s' => '%s'" % (title, redirect)
        else:
            title = title.replace("_", " ")
            if g_fVerbose:
                log_txt = "title: %s " % title
            try:
                ipedia_write_cur.execute("""INSERT INTO articles (title, body) VALUES ('%s', '%s')""" % (dbEscape(title), dbEscape(converted)))
                if g_fVerbose:
                    log_txt += "*New record"
            except:
                # assuming that the exception happend because of trying to insert
                # item with a duplicate title (duplication due to lower-case
                # conversion might convert 2 differnt titles into the same,
                # lower-cased title)
                if g_fShowDups:
                    print "dup: " + title
                if g_fVerbose:
                    log_txt += "Update existing record"
                print "DUP ARTICLE: '%s'" % title
                ipedia_write_cur.execute("""UPDATE articles SET body='%s' WHERE title='%s'""" % (dbEscape(converted), dbEscape(title)))
            if g_fVerbose:
                print log_txt
        convWriter.write(convertedArticle)
        if articleSize != 0:
            if not sizeStats.has_key(articleSize):
                sizeStats[articleSize] = 1
            else:
                sizeStats[articleSize] = sizeStats[articleSize]+1
        count += 1
        if count % 1000 == 0:
            sys.stderr.write("phase 2 processed %d, last title=%s\n" % (count,article.getTitle()))
    convWriter.close()
    # dump size stats to a file
    statsFileName = wikipediasql.getSizeStatsFileName(sqlDump)
    statsFo = open(statsFileName, "wb")
    sizes = sizeStats.keys()
    sizes.sort()
    for size in sizes:
        count = sizeStats[size]
        statsFo.write("%d\t\t%d\n" % (size,count))
    statsFo.close()

g_dbList = None
# return a list of databases on the server
def getDbList():
    global g_dbList
    conn = getRootConnection()
    if None == g_dbList:
        cur = conn.cursor()
        cur.execute("SHOW DATABASES;")
        dbs = []
        for row in cur.fetchall():
            dbs.append(row[0])
        cur.close()    
        g_dbList = dbs
    return g_dbList

genSchemaSql = """
CREATE TABLE `articles` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `title` varchar(255) NOT NULL,
  `body` mediumtext NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `title_index` (`title`)
) TYPE=MyISAM; 
"""

genSchema2Sql = """
CREATE TABLE `redirects` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `title` varchar(255) NOT NULL,
  `redirect` varchar(255) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `title_index` (`title`)
) TYPE=MyISAM; 

"""

def delDb(conn,dbName):
    cur = conn.cursor()
    cur.execute("DROP DATABASE %s" % dbName)
    cur.close()
    print "Database '%s' deleted" % dbName

def createDb(conn,dbName):
    cur = conn.cursor()
    cur.execute("CREATE DATABASE %s" % dbName)
    cur.execute("USE %s" % dbName)
    cur.execute(genSchemaSql)
    cur.execute(genSchema2Sql)
    cur.execute("GRANT ALL ON %s.* TO 'ipedia'@'localhost' IDENTIFIED BY 'ipedia';" % dbName)
    cur.close()
    print "Created '%s' database and granted perms to ipedia user" % dbName

cookiesSql = """CREATE TABLE `cookies` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `cookie` varchar(32) binary NOT NULL default '',
  `device_info_token` varchar(255) NOT NULL default '',
  `issue_date` timestamp(14) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `cookie_unique` (`cookie`)
) TYPE=MyISAM;"""

regCodesSql = """CREATE TABLE reg_codes (
    reg_code    VARCHAR(64) NOT NULL,
    purpose     VARCHAR(255) NOT NULL,
    when_entered TIMESTAMP NOT NULL,
    disabled_p   CHAR(1) NOT NULL DEFAULT 'f',

    PRIMARY KEY (reg_code)
) TYPE=MyISAM;""";

# TODO: we need to improve that. We'll have users table. Users can be registered
# or not. Unregistered users send us cookie that we assigned them. Registered
# users send us reg code.
# We use user_id for logging since that can be used to get cookie and/or reg code
# without the need to log them. Also, we'll try to not use MySQL specific SQL.
# We'll get rid of "cookies" table and combine it's info with "users" table (since
# for our purposes, a new cookie essentially means a new user).
# So our tables will look like:
# CREATE TABLE users (
#  id          INT(10) NOT NULL auto_increment, --- TODO: find standard SQL equivalent of INT(10). Or maybe it is standard SQL?
#  cookie      VARCHAR(64) NOT NULL,
#  device_info VARCHAR(255) NOT NULL,
#  cookie_issue_date TIMESTAMP(14) NOT NULL,
#  reg_code    VARCHAR(64) NULL,  -- if not NULL, user is registered
#  registration_date TIMESTAMP(14) NOT NULL
#  PRIMARY KEY(id)
# ) TYPE=MyISAM;
#
# CREATE TABLE request_log (
#   user_id    INT(10) NOT NULL REFERENCES users(id) # REFERENCES probably doesn't work on MySQL
#   client_ip  INT(1) NOT NULL,
#   requested_title VARCHAR(255) NULL, -- if not NULL, this is a SEARCH request
#   extended_search_term VARCHAR(255) NULL, -- if not NULL, this is EXTENDED SEARCH request. requested_title and extended_search_title can't be both NULL or not NULL
#   request_date TIMESTAMP(14) NOT NULL, -- when a request has been made
#   error  INT(10) NULL, -- if not NULL, there was an error processing the request
#   article_title VARCHAR(255) NULL, -- if not NULL, this is the article that was returned for SEARCH request
# ) TYPE=MyISAM;

regUsersSql = """CREATE TABLE `registered_users` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `cookie_id` int(10) unsigned default '0',
  `user_name` varchar(255) default '',
  `reg_code` varchar(255) binary NOT NULL default '',
  `registration_date` timestamp(14) NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=MyISAM;"""

requestsSql = """CREATE TABLE `requests` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `client_ip` int(10) unsigned NOT NULL default '0',
  `has_get_cookie_field` tinyint(1) NOT NULL default '0',
  `cookie_id` int(10) unsigned default '0',
  reg_code VARCHAR(64) NULL default '',
  `requested_term` varchar(255) default '',
  `error` int(10) unsigned NOT NULL default '0',
  `request_date` timestamp(14) NOT NULL,
  `definition_for` varchar(255) default '',
  PRIMARY KEY  (`id`)
) TYPE=MyISAM; """

def delDataDb(conn):
    cur = conn.cursor()
    cur.execute("DROP DATABASE %s" % MANAGEMENT_DB)
    cur.close()
    print "Database '%s' deleted" % MANAGEMENT_DB

def createDataDb(conn):
    cur = conn.cursor()
    cur.execute("CREATE DATABASE %s" % MANAGEMENT_DB)
    cur.execute("USE %s" % MANAGEMENT_DB)
    cur.execute(cookiesSql)
    cur.execute(regCodesSql)
    cur.execute(regUsersSql)
    cur.execute(requestsSql)
    cur.execute("GRANT ALL ON %s.* TO 'ipedia'@'localhost' IDENTIFIED BY 'ipedia';" % MANAGEMENT_DB)
    cur.close()
    print "Created '%s' database and granted perms to ipedia user" % MANAGEMENT_DB

def recreateDataDb(fRecreate=False):
    connRoot = getRootConnection()
    if MANAGEMENT_DB not in getDbList():
        createDataDb(connRoot)
    else:
        if fRecreate:
            delDataDb(connRoot)
            createDataDb(connRoot)
        else:
            print "Database '%s' exists" % MANAGEMENT_DB

def createIpediaDb(sqlDumpName,dbName,fRecreateDb=False,fRecreateDataDb=False):
    connRoot = getRootConnection()

    if dbName not in getDbList():
        createDb(connRoot,dbName)
    else:
        if fRecreateDb:
            delDb(connRoot,dbName)
            createDb(connRoot,dbName)
        else:
            print "Database '%s' already exists. Use -recreatedb flag in order to force recreation of the database" % dbName
            sys.exit(0)


def createFtIndex():
    print "starting to create full-text index"
    query = "CREATE FULLTEXT INDEX full_text_index ON articles(title,body);"
    conn = getIpediaConnection(None)
    cur = conn.cursor()
    cur.execute(query)
    cur.close()
    print "finished creating full-text index"

if __name__=="__main__":

    fNoPsyco = arsutils.fDetectRemoveCmdFlag("-nopsyco")
    if g_fPsycoAvailable and not fNoPsyco:
        print "using psyco"
        psyco.full()

    g_fVerbose = arsutils.fDetectRemoveCmdFlag("-verbose")
    g_fShowDups = arsutils.fDetectRemoveCmdFlag("-showdups")
    fRecreateDb = arsutils.fDetectRemoveCmdFlag("-recreatedb")
    fRecreateDataDb = arsutils.fDetectRemoveCmdFlag("-recreatedatadb")
    articleLimit = arsutils.getRemoveCmdArgInt("-limit")

    # we always need to try to create it
    recreateDataDb(fRecreateDataDb)
    if fRecreateDataDb and len(sys.argv) == 1:
        # no arguments allowed if we only try to recreate data db
        sys.exit(0)

    if len(sys.argv) != 2:
        usageAndExit()

    sqlDump = sys.argv[1]

    dbName = getDbNameFromFileName(sqlDump)
    foLog = None
    try:
        createIpediaDb(sqlDump,dbName,fRecreateDb,fRecreateDataDb)
        timer = arsutils.Timer(fStart=True)
        logFileName = wikipediasql.getLogFileName(sqlDump)
        foLog = open(logFileName, "wb")
        sys.stdout = foLog
        sys.stderr = foLog
        convertArticles(sqlDump,dbName,articleLimit)
        timer.stop()
        timer.dumpInfo()
        createFtIndex()
    finally:
        deinitDatabase()
        if None != foLog:
            foLog.close()

