#include "iPediaHyperlinkHandler.hpp"
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"
#include "GenericTextElement.hpp"
#include <Form.hpp>

bool iPediaHyperlinkHandler::handleExternalHyperlink(const ArsLexis::String& url)
{
    bool result = false;
    if (viewerDatabaseId_)
    {
        UInt16 urlLength = url.length();
        char* urlCopy = static_cast<char*>(MemPtrNew(urlLength+1));
        if (urlCopy)
        {
            MemMove(urlCopy, url.data(), urlLength);
            urlCopy[urlLength] = chrNull;
            Err error = MemPtrSetOwner(urlCopy, 0);
            assert(!error);
            error = SysUIAppSwitch(viewerCardNo_, viewerDatabaseId_, sysAppLaunchCmdGoToURL, urlCopy);
            if (error)
            {
                //! @todo Handle error running www viewer.
            }
            else 
                result = true;
        }
        else
            ArsLexis::handleBadAlloc();
    }
    return result;
}

bool iPediaHyperlinkHandler::handleTermHyperlink(const ArsLexis::String& term)
{
    bool result=false;
    iPediaApplication& app=iPediaApplication::instance();
    LookupManager* lookupManager=app.getLookupManager();  
    if (lookupManager && !lookupManager->lookupInProgress())
    {
        result=true;
        String lang;
        String realTerm = term;
        String::size_type pos = term.find(_T(':'));
        if (String::npos != pos)
        {
            lang.assign(term, 0, pos);
            realTerm.erase(0, pos+1);
        }
        lookupManager->lookupIfDifferent(realTerm, lang);
    }
    return result;        
}


iPediaHyperlinkHandler::iPediaHyperlinkHandler(UInt16 viewerCardNo, LocalID viewerDatabaseId):
    viewerCardNo_(viewerCardNo),
    viewerDatabaseId_(viewerDatabaseId)
{
}

void iPediaHyperlinkHandler::handleHyperlink(Definition& definition, DefinitionElement& element, const Point*)
{
    assert(element.isTextElement());
    TextElement& textElement=static_cast<TextElement&>(element);
    assert(textElement.isHyperlink());
    const TextElement::HyperlinkProperties* props=textElement.hyperlinkProperties();
    assert(props!=0);
    bool makeClicked=false;
    switch (props->type) 
    {
        case hyperlinkBookmark:
            //definition.goToBookmark(props->resource);
            break;
    
        case hyperlinkExternal:
            makeClicked=handleExternalHyperlink(props->resource);
            break;
            
        case hyperlinkTerm:            
            makeClicked=handleTermHyperlink(props->resource);
            break;

        default:
            assert(false);
    }    
/*            
    if (makeClicked) 
    {
        iPediaApplication& app=iPediaApplication::instance();
        props->type=hyperlinkClicked;
        Form* form=app.getOpenForm(mainForm);
        if (form) 
        {
            Graphics graphics(form->windowHandle());
            definition.renderSingleElement(graphics, app.preferences().renderingPreferences, element);
        }
    }
*/    
}

iPediaHyperlinkHandler::~iPediaHyperlinkHandler()
{}
