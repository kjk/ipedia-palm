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
# -revlinksonly : only do reverse links
# fileName : convert directly from sql file, no need for enwiki.cur database

import sys, os, string, MySQLdb
import  arsutils, wikipediasql,articleconvert,iPediaServer
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
    print "wikiToDbConvert.py [-verbose] [-revlinksonly] [-limit n] [-showdups] [-nopsyco] [-recreatedb] [-recreatedatadb] sqlDumpName"
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
    g_redirectsWriter.write(visited)

def setUnresolvedRedirectWriter(sqlDump):
    global g_redirectsWriter
    assert None == g_redirectsWriter
    g_redirectsWriter = UnresolvedRedirectsWriter(sqlDump)
    g_redirectsWriter.open()

def closeUnresolvedRedirectWriter():
    global g_redirectsWriter
    g_redirectsWriter.close()
    g_redirectsWriter = None

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
def convertArticles(sqlDump,articleLimit):
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
            #links = articleconvert.articleExtractLinks(txt)
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
    closeUnresolvedRedirectWriter()
    print "Number of unresolved redirects: %d" % unresolvedCount

    dbName = getDbNameFromFileName(sqlDump)
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

# we want to limit how many reverse links we have. There is a small number (few
# hundred) of heavily linked articles and there is no point of sending tens of
# kilobytes of links, they won't display on a PDA well anyway. So we just limit
# the number of reverse links we accumulate.
REVERSE_LINK_LIMIT = 200
LINK_SEPARATOR = '\n'
def calcReverseLinks(fileName):
    print "Calculating reverse links"
    count = 0
    reverseLinks = {}
    totalLinksCount = 0
    for article in wikipediasql.iterConvertedArticles(fileName):
        if article.fRedirect():
            continue
        count += 1
        title = article.getTitle()
        if -1 != title.find(LINK_SEPARATOR):
            print "rejected title '%s', has link separator (%d)" % (title, ord(LINK_SEPARATOR))
            continue
        body = article.getText()
        links = articleconvert.articleExtractLinksSimple(body)
        totalLinksCount += len(links)
        for link in links:
            linkLower = link.lower()
            if reverseLinks.has_key(linkLower):
                currentLinks = reverseLinks[linkLower]
                if len(currentLinks)<REVERSE_LINK_LIMIT:
                    if title not in currentLinks: # TODO: only needed because of duplicates?
                        currentLinks.append(title)
            else:
                reverseLinks[linkLower] = [link,title]
        if count % 20000 == 0:
            sys.stderr.write("processed %d articles\n" % count)
    print "number of articles with reverse links: %d" % len(reverseLinks)
    avgLinksCount = float(totalLinksCount)/float(len(reverseLinks))
    print "average number of links: %.2f" % avgLinksCount
    # now dump them into a database
    print "started inserting data into reverse_links table"
    dbName = getDbNameFromFileName(fileName)
    cur = getNamedCursor(getIpediaConnection(dbName), "rev_links_write_cur")
    for rLinks in reverseLinks.values():
        title = rLinks[0]
        links = rLinks[1:]
        assert len(links)>0
        # need to escape the character we use for gluing the strings together
        # client will have to un-escape
        #body = string.join([l.replace(":", "::") for l in links],":")
        body = string.join(links, LINK_SEPARATOR)
        try:
            sql = "INSERT INTO reverse_links (title,links_to_it) VALUES ('%s', '%s');" % (dbEscape(title), dbEscape(body))
            cur.execute(sql)
        except:
            # assuming that the exception happend because of trying to insert
            # item with a duplicate title (duplication due to lower-case
            # conversion might convert 2 differnt titles into the same,
            # lower-cased title)
            try:
                sql = "UPDATE reverse_links SET links_to_it='%s' WHERE title='%s';" % (dbEscape(body), dbEscape(title))
                cur.execute(sql)
            except:
                # nothing we can do about it
                sys.stderr.write("Exception in UPDATE article '%s' with body of len %d\n" % (title, len(body)))
    print "finished inserting data into reverse_links table"

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

articlesSql = """
CREATE TABLE `articles` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `title` varchar(255) NOT NULL,
  `body` mediumtext NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `title_index` (`title`)
) TYPE=MyISAM;
"""

redirectsSql = """
CREATE TABLE `redirects` (
  `title` varchar(255) NOT NULL,
  `redirect` varchar(255) NOT NULL,
  PRIMARY KEY  (`title`)
) TYPE=MyISAM;
"""

reverseLinksSql = """
CREATE TABLE reverse_links (
  title varchar(255) NOT NULL,
  links_to_it mediumtext NOT NULL,
  PRIMARY KEY (title)
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
    cur.execute(articlesSql)
    cur.execute(redirectsSql)
    cur.execute(reverseLinksSql)
    cur.execute("GRANT ALL ON %s.* TO 'ipedia'@'localhost' IDENTIFIED BY 'ipedia';" % dbName)
    cur.close()
    print "Created '%s' database and granted perms to ipedia user" % dbName

usersSql = """CREATE TABLE users (
  user_id           INT(10) NOT NULL auto_increment,
  cookie            VARCHAR(64)  NOT NULL,
  device_info       VARCHAR(255) NOT NULL,
  cookie_issue_date TIMESTAMP(14) NOT NULL,
  reg_code          VARCHAR(64) NULL,
  registration_date TIMESTAMP(14) NULL,
  disabled_p        CHAR(1) NOT NULL default 'f',

  PRIMARY KEY(user_id),
  UNIQUE (cookie)

) TYPE=MyISAM;"""

requestLogSql = """CREATE TABLE request_log (
    user_id          INT(10) NOT NULL REFERENCES users(user_id),
    client_ip        VARCHAR(24) NOT NULL,
    log_date         TIMESTAMP(14) NOT NULL,

    search_term  VARCHAR(255) NULL,
    -- if not NULL, this is EXTENDED SEARCH request. search_term and
    -- extended_search_title can't be both NULL or not NULL
    extended_search_term VARCHAR(255) NULL,
    -- if not NULL, there was an error processing the request and this is the 
    -- error number
    error            INT(10) NULL,
    -- if not NULL, this is the article that was returned for SEARCH request
    -- (taking redirects into account)
    article_title    VARCHAR(255) NULL
) TYPE=MyISAM;"""

getCookieLogSql = """CREATE TABLE get_cookie_log (
    user_id         INT(10) NOT NULL REFERENCES users(user_id),
    client_ip       VARCHAR(24) NOT NULL,
    log_date        TIMESTAMP(14) NOT NULL,
    device_info     VARCHAR(255) NOT NULL,
    cookie          VARCHAR(64) NOT NULL,
) TYPE=MyISAM;"""

verifyRegCodeLogSql = """CREATE TABLE verify_reg_code_log (
    user_id         INT(10) NOT NULL REFERENCES users(user_id),
    client_ip       VARCHAR(24) NOT NULL,
    log_date        TIMESTAMP(14) NOT NULL,
    reg_code        VARCHAR(64) NOT NULL,
    reg_code_valid_p CHAR(1) NOT NULL
) TYPE=MyISAM;"""

# table contains list of valid registration codes
regCodesSql = """CREATE TABLE reg_codes (
  reg_code      VARCHAR(64) NOT NULL,
  purpose       VARCHAR(255) NOT NULL,
  when_entered  TIMESTAMP NOT NULL,
  disabled_p    CHAR(1) NOT NULL DEFAULT 'f',

  PRIMARY KEY (reg_code)
) TYPE=MyISAM;"""

def delDataDb(conn):
    cur = conn.cursor()
    cur.execute("DROP DATABASE %s" % MANAGEMENT_DB)
    cur.close()
    print "Database '%s' deleted" % MANAGEMENT_DB

def insertRegCode(cur,regCode,fEnabled):
    disabled_p = 'f'
    if not fEnabled:
        disabled_p = 't'
    query = """INSERT INTO reg_codes (reg_code, purpose, when_entered, disabled_p) VALUES ('%s', 'test', now(), '%s');""" % (regCode,disabled_p)
    cur.execute(query)

def createDataDb(conn):
    print "creating '%s' database" % MANAGEMENT_DB

    cur = conn.cursor()
    cur.execute("CREATE DATABASE %s" % MANAGEMENT_DB)
    cur.execute("USE %s" % MANAGEMENT_DB)
    cur.execute(usersSql)
    cur.execute(requestLogSql)
    cur.execute(getCookieLogSql)
    cur.execute(verifyRegCodeLogSql)
    cur.execute(regCodesSql)
    cur.execute("GRANT ALL ON %s.* TO 'ipedia'@'localhost' IDENTIFIED BY 'ipedia';" % MANAGEMENT_DB)
    insertRegCode(cur, iPediaServer.testValidRegCode, True)
    insertRegCode(cur, iPediaServer.testDisabledRegCode, False)
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

def createIpediaDb(sqlDumpName,fRecreateDb=False,fRecreateDataDb=False):
    connRoot = getRootConnection()

    dbName = getDbNameFromFileName(sqlDump)

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

def revLinksOnly(sqlDump):
    try:
        connRoot = getRootConnection()

        dbName = getDbNameFromFileName(sqlDump)

        if dbName not in getDbList():
            print "Database '%s' doesn't exist and we need it for -revlinksonly" % dbName
        calcReverseLinks(sqlDump)
    finally:
        deinitDatabase()

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
    fRevLinksOnly = arsutils.fDetectRemoveCmdFlag("-revlinksonly")

    # we always need to try to create it
    recreateDataDb(fRecreateDataDb)
    if fRecreateDataDb and len(sys.argv) == 1:
        # no arguments allowed if we only try to recreate data db
        sys.exit(0)

    if len(sys.argv) != 2:
        usageAndExit()

    sqlDump = sys.argv[1]

    if fRevLinksOnly:
        revLinksOnly(sqlDump)
        sys.exit(0) 

    foLog = None
    try:
        createIpediaDb(sqlDump,fRecreateDb,fRecreateDataDb)
        timer = arsutils.Timer(fStart=True)

        logFileName = wikipediasql.getLogFileName(sqlDump)
        # use small buffer so that we can observe changes with tail -w
        foLog = open(logFileName, "wb", 64)
        sys.stdout = foLog
        # sys.stderr = foLog
        convertArticles(sqlDump,articleLimit)
        calcReverseLinks(sqlDump)
        timer.stop()
        timer.dumpInfo()
        createFtIndex()
    finally:
        deinitDatabase()
        if None != foLog:
            foLog.close()

