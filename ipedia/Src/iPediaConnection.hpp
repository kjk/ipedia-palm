#ifndef __DEFINITION_REQUEST_CONNECTION_HPP__
#define __DEFINITION_REQUEST_CONNECTION_HPP__

#include "LookupManager.hpp"
#include "SysUtils.hpp"
#include <FieldPayloadProtocolConnection.hpp>
#include <BaseTypes.hpp>

using ArsLexis::status_t;

class DefinitionParser;

class iPediaConnection: public FieldPayloadProtocolConnection
{
    LookupManager&      lookupManager_;
    ulong_t             transactionId_;
    ArsLexis::String    term_;
    uint_t              formatVersion_;
    ArsLexis::String    articleTitle_;
    DefinitionParser*   definitionParser_;
    ArsLexis::String    newDbLangCode_;
    ArsLexis::String    langToUse_;
    bool                fGetAvailableLangs_;
    bool isSwitchLangRequest_;
    

    class SearchResultsHandler: public FieldPayloadProtocolConnection::PayloadHandler
    {
        ArsLexis::String searchResults_;

    public:

        SearchResultsHandler()
        {}
        
        status_t handleIncrement(const ArsLexis::char_t* text, ulong_t& length, bool finish)
        {
            if (finish)
                searchResults_.assign(text, 0, length);
            else
                length=0;                
            return errNone;
        }
        
        const ArsLexis::String& searchResults() const
        {return searchResults_;}
        
    };
    
    SearchResultsHandler* searchResultsHandler_;

    // TODO: ReverseLinksResultsHandler is identical to SearchResultsHandler. Maybe we should just have
    // one SimpleResultsHandler instead?
    class ReverseLinksResultsHandler: public FieldPayloadProtocolConnection::PayloadHandler
    {
        ArsLexis::String reverseLinksResults_;

    public:

        ReverseLinksResultsHandler()
        {}
        
        status_t handleIncrement(const ArsLexis::char_t * text, ulong_t& length, bool finish)
        {
            if (finish)
                reverseLinksResults_.assign(text, 0, length);
            else
                length=0;                
            return errNone;
        }
        
        const ArsLexis::String& reverseLinksResults() const
        {return reverseLinksResults_;}
        
    };

    ReverseLinksResultsHandler* reverseLinksResultsHandler_;
        
    status_t prepareRequest();
    
    enum PayloadType 
    {
        payloadNone,
        payloadArticleBody,
        payloadSearchResults,
        payloadReverseLinks
    };

    enum RegCodeValidationType
    {
        regCodeTypeUnset=-1,
        regCodeTypeValid=1,
        regCodeTypeInvalid=0
    };

    PayloadType payloadType_;

protected:

    status_t notifyFinished();
    
    void handleError(status_t error);
    
    status_t handleField(const char_t *name, const char_t *value);
    
    status_t notifyPayloadFinished();
    
    status_t notifyProgress();

    status_t open();
    
public:

    status_t enqueue();

    iPediaConnection(LookupManager& lm);
    
    ~iPediaConnection();
    
    void setTerm(const ArsLexis::String& term)
    {term_=term;}
    
    void setPerformFullTextSearch(bool value)
    {performFullTextSearch_=value;}

    void setRandom()
    {getRandom_=true;}

    // if set, send Verify-Registration-Code
    ArsLexis::String  regCodeToVerify;

    void switchDatabase(const char_t* langCode)
    {
        newDbLangCode_.assign(langCode);
        isSwitchLangRequest_ = true;
    }
    
    void setLang(const String& lang)
    {
        langToUse_ = lang;
    }

    void getAvailableLangs()
    {
        fGetAvailableLangs_ = true;
    }

private:

    iPediaServerError serverError_;

    RegCodeValidationType regCodeValid_;

    bool notFound_:1;
    bool performFullTextSearch_:1;
    bool getRandom_:1;
    
};

#endif
