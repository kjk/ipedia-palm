# Copyright: Krzysztof Kowalczyk
# Owner: Andrzej Ciarkowski
#
# Purpose:
#  Convert the body of wikipedia article from original wikipedia
#  format to our format

import sys,traceback,re,unicodedata,entities, string
import arsutils

def stripBlocks(text, startPattern, endPattern):
    opened=0
    spanStart=-1
    spans=[]
    pattern=r"(%s)|(%s)" % (startPattern, endPattern)
    blockRe=re.compile(pattern, re.I+re.S)
    for match in blockRe.finditer(text):
        if match.lastindex==1: # This means it's a start tag
            if not opened:
                spanStart=match.start(match.lastindex)
            opened+=1
        else:                       # This is end tag
            if opened==1:
                spans.append((spanStart, match.end(match.lastindex)))
            opened-=1;
            if opened<0:
                opened=0
    if opened:
        spans.append((spanStart, len(text)))
    spans.reverse()             # Iterate from end so that text indices remain valid when we slice and concatenate text
    for span in spans:
        start, end=span
        text=text[:start]+text[end:]
    return text

def stripTagBlocks(text, blockElem):
    return stripBlocks(text, '<%s.*?>' % blockElem, '</%s>' % blockElem)

def replaceRegExp(text, regExp, repl):
    match=regExp.search(text)
    while match:
        #print "Replacing: ", text[match.start():match.end()], " with: ", repl
        text=text[0:match.start()]+repl+text[match.end():]
        match=regExp.search(text)
    return text

def replaceTagList(text, tagList, repl):
    for tag in tagList:
        text=replaceRegExp(text, re.compile(r'<(/)?%s(\s+.*?)?>' % tag, re.I), repl)
    return text

# this is a hack to change "&sup2" entities without trailing ";" into "&sup2;"
# wikipedia renders "&sup2" (incorrectly ?) as "&sup2;" so we should too
# fairly unconventional algorithm but easy to do in Python (split by "&sup2;"
# to make sure we won't accidently turn "&sup2;" into "&sup2;;", replace
# "&sup2" with "&sup2;" in remaining text, join back the parts with "&sup2;"
# to restore the original text
def fixSup2(text):
    parts = text.split("&sup2;")
    if 1==len(parts):
        # optimization for a special case of no "&sup2;" in the text
        return text.replace("&sup2", "&sup2;")
    outArr = []
    for p in parts:
        outArr.append(p.replace("&sup2","&sup2;"))
    outTxt = string.join(outArr,"&sup2;")
    return outTxt

# Remove image tags, version using regexps.
imageRe=re.compile(r"\[\[image:.*?(\[\[.*?\]\].*?)*?\]\]", re.I+re.S)
def removeImageRx(text):
    return replaceRegExp(text, imageRe, "")

# Remove image tags, version not using regexps.
# [[Image:Seattlepikeplace2002.JPG|right|thumb|[[Pike Place Market]]]] 
# So we need remove everything between "[[Image:" and "]]", ignoring
# embedded links like "[[foo]]"

# case-insesitivity is important so we'll use regexp instead of string.find()
imageStartRe = re.compile("\[\[Image:", re.I)
# TODO: it doesn't always work, e.g. for "oh[[image:man[[bo[[la]]e]]]]gal"
def removeImageStrOld(text):
    while True:
        match = imageStartRe.search(text)
        if None == match:
            return text
        txtLen = len(text)
        posImageStart = match.start()
        # now find ending "]]" but counting nesting levels of "[[" and "]]"
        nesting = 0
        prevChar = None
        pos = match.end()
        fChanged = False
        while pos < txtLen:
            curChar = text[pos]
            if ']'==prevChar and ']'==curChar:
                if nesting>0:
                    nesting -= 1
                else:
                    # remove image stuff
                    txtTmp = text[:posImageStart] + text[pos+1:]
                    text = txtTmp
                    fChanged = True
                    break
            if '['==prevChar and '['==curChar:
                nesting += 1
            prevChar = curChar
            pos += 1
        if not fChanged:
            return text

# Remove image tags, another version using strings.
# TODO: this sucker doesn't work either
def removeImageStr(text):
    while True:
        match = imageStartRe.search(text)
        if None == match:
            return text
        posImageStart = match.start()
        curPos = posImageStart + len("[[Image:")
        assert curPos == match.end()
        nesting = 0
        fChanged = False
        while True:
            openPos  = text.find("[[", curPos)
            closePos = text.find("]]", curPos)

            if -1 == closePos:
                # we didn't find an ending "]]" so something is wrong, but
                # we can't do much about it
                break

            if -1 == openPos:
                # we didn't find starting "[[" for nested tag but found
                # ending "]]". If nesting level is 0, then we need to remove
                # everything in between, otherwise decrease nesting level
                if nesting == 0:
                    txtTmp = text[:posImageStart] + text[closePos+len("]]"):]
                    text = txtTmp
                    fChanged = True
                    break
                else:
                    nesting -= 1
                    curPos = closePos + len("[[")
                    continue

            # we have both "[[" and "]]"
            if openPos < closePos:
                # we have "[[" before "]]", so we increase nesting level
                nesting += 1
                curPos = openPos + len("[[")
                continue
            else:
                nesting -= 1
                if nesting <= 0:
                    txtTmp = text[:posImageStart] + text[closePos+len("]]"):]
                    text = txtTmp
                    fChanged = True
                    break

            assert nesting>=0

        if not fChanged:
            return text

commentRe=re.compile("<!--.*?-->", re.S)
scriptRe=re.compile("<script.*?</script>", re.I+re.S)
badLinkRe=re.compile(r"\[\[((\w\w\w?(-\w\w)?)|(simple)|(image)|(media)):.*?\]\]", re.I+re.S)
# most links to other-language version are caught by badLinkRe, but not "tokipona"
tokiponaRe=re.compile(r"\[\[tokipona:.*?\]\]", re.I+re.S)

multipleLinesRe=re.compile("\n{3,100}")
# replace multiple (1+) empty lines with just one empty line.
def stripMultipleNewLines(txt):
    txt=replaceRegExp(txt,multipleLinesRe,"\n\n")
    return txt

wikiMacrosReplacements = {
    "{{msg:stub}}"     : "",
    "{{msg:spoiler}}"  : "'''Warning:''' Plot details follow.",
    "{{msg:disambig}}" : "This is a disambiguation page; that is, one that points to other pages that might otherwise have the same name.",
#    "{{msg:copyvio1}}"   : "",
#    "{{msg:copyvio2}}"   : "",
#    "{{msg:NPOV}}"       : "",
#    "{{msg:disputed}}"   : "",
#    "{{msg:inclusion}}"  : "",
#    "{{msg:protected}}"  : "",
#    "{{msg:inuse}}"      : "",
#    "{{msg:controversial}}" : "",
}

wikiMacroRe=re.compile("\{\{((msg)|(subst))\:.*?\}\}", re.I)

wikiTemplateRe=re.compile("\{\{.*\}\}", re.I)

categoryRe=re.compile("\[\[Category:.*\]\]", re.I)

def replaceWikiMacros(text):
    for (macro,replacement) in wikiMacrosReplacements.items():
        text = text.replace(macro, replacement)
    text=replaceRegExp(text, wikiMacroRe, "")
    return text

#def dumpException(e):
#    print str(e)
#    print sys.exc_info()[0]
#    print sys.exc_info()[1]
#    print traceback.print_tb(sys.exc_info()[2])

# main function: given the text of wikipedia article in original wikipedia
# format, return the article in our own format
def convertArticle(term, text):
    try:
        text=text.replace('__NOTOC__', '')
        text=fixSup2(text)
        text=removeImageRx(text)
        # remove categories. TODO: provide a better support for categories
        # i.e. we remember categories on the server and client can display
        # all articles in a given category
        text=replaceRegExp(text, categoryRe, '')
        text=replaceWikiMacros(text)
        # remove remaining templates. TODO: better support for templates
        # in wikipedia template text is replaced by a page from Template:
        # namespace
        text=replaceRegExp(text, wikiTemplateRe, '')
        text=text.replace('\r','')
        text=replaceRegExp(text, commentRe, '')     # This should be safe, as it's illegal in html to nest comments

        text=stripTagBlocks(text, 'div')
        text=stripTagBlocks(text, 'table')
        text=stripBlocks(text, r'\{\|', r'\|\}')

        text=replaceRegExp(text, scriptRe, '')

        text=replaceTagList(text, ['b', 'strong'], "'''")
        text=replaceTagList(text, ['em', 'i', 'cite'], "''")
        text=replaceTagList(text, ['hr'], '----')
        text=replaceTagList(text, ['p'], '<br>')
        text=replaceTagList(text, ['dfn', 'code', 'samp', 'kbd', 'var', 'abbr', 'acronym', 'blockquote', 'q', 'pre', 'ins', 'del', 'dir', 'menu', 'img', 'object', 'big', 'span', 'applet', 'font', 'basefont', 'tr', 'td', 'table', 'center', 'div'], '')
        text=replaceRegExp(text, badLinkRe, '')
        text=replaceRegExp(text, tokiponaRe, '')
        text=entities.convertNamedEntities(term, text)
        text=entities.convertNumberedEntities(term, text)
        text=stripMultipleNewLines(text)
        text=text.strip()
        text+='\n'
        return text
    except Exception, ex:
        print "Exception while converting term: ", term
        print arsutils.exceptionAsStr(ex)
        return ''

class WikipediaLink:
    def __init__(self,link,name):
        self.link = link
        self.name = name
    def getLink(self): return self.link
    def getName(self): return self.name
    def __eq__(self,other):
        if self.link==other.getLink() and self.name==other.getName():
            return True
        else:
            return False
    def __ne__(self,other):
        return not self.__eq__(other)
    def dump(self):
        print "'%s':'%s'" % (self.link,self.name)

linkRe=re.compile(r'\[\[([^\n]*?)(\|.*?)?\]\]', re.S)

# extract all links from wikipedia article and return them as a list of WikipediaLink
# return None if there are no links
def articleExtractLinks(articleTxt):
    links = []
    for match in linkRe.finditer(articleTxt):
        link=match.group(1)
        name=match.group(2)
        if None != name:
            name = name[1:]  # remove "|" from the beginning which is part of regexp
        wikiLink = WikipediaLink(link,name)
        links.append(wikiLink)
    if len(links)==0:
        return None
    return links

# extract all links from wikipedia article and return them as a list
# return empty list if there are no links
def articleExtractLinksSimple(articleTxt):
    links = []
    for match in linkRe.finditer(articleTxt):
        link=match.group(1)
        name=match.group(2)
        if None != name:
            name = name[1:]  # remove "|" from the beginning which is part of regexp
        links.append(link)
    return links

def fValidLink(link,redirects,articlesLinks):
    if redirects.has_key(link) or articlesLinks.has_key(link):
        return True
    return False

# remove invalid wikipedia links from txt. Invalid link is a link
# to an article that is not present in articlesLinks or redirects
# dictionaries
def removeInvalidLinks(txt,redirects,articlesLinks):
    fModified = False
    while True:
        fLocallyModified = False
        for match in linkRe.finditer(txt):
            link=match.group(1)
            link=link.replace(' ', '_')
            if fValidLink(link,redirects,articlesLinks):
                #print "VALID_LINK: '%s'" % link
                continue
            #else:
            #    print "%s-INVALID LINK" % link
            name=match.group(2)
            if None != name:
                replacement = name[1:]
            else:
                replacement =link.replace('_',' ')
            #print "INVALID_LINK '%s', REPL '%s'" % (link,replacement)
            txt = txt[:match.start()]+replacement+txt[match.end():]
            fModified = True
            fLocallyModified = True
            break
        if not fLocallyModified:
            break

    if fModified:
        return txt
    else:
        return None
