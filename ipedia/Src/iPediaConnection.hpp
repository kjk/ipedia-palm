#ifndef __DEFINITION_REQUEST_CONNECTION_HPP__
#define __DEFINITION_REQUEST_CONNECTION_HPP__

#include "LookupManager.hpp"
#include "SysUtils.hpp"
#include <FieldPayloadProtocolConnection.hpp>
#include <BaseTypes.hpp>

class DefinitionParser;

class iPediaConnection: public ArsLexis::FieldPayloadProtocolConnection
{
    LookupManager& lookupManager_;
    ulong_t transactionId_;
    ArsLexis::String term_;
    uint_t formatVersion_;
    ArsLexis::String resultsFor_;
    DefinitionParser* definitionParser_;

    class SearchResultsHandler: public ArsLexis::FieldPayloadProtocolConnection::PayloadHandler
    {
        ArsLexis::String searchResults_;

    public:

        SearchResultsHandler()
        {}
        
        ArsLexis::status_t handleIncrement(const ArsLexis::String& text, ulong_t& length, bool finish)
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
    
    void prepareRequest();
    
    enum PayloadType 
    {
        payloadNone,
        payloadDefinition,
        payloadSearchResults
    };
    
    PayloadType payloadType_;

protected:

    ArsLexis::status_t notifyFinished();
    
    void handleError(ArsLexis::status_t error);
    
    ArsLexis::status_t handleField(const ArsLexis::String& name, const ArsLexis::String& value);
    
    void notifyPayloadFinished();
    
    ArsLexis::status_t notifyProgress();

    ArsLexis::status_t open();
    
public:

    ArsLexis::status_t enqueue();

    iPediaConnection(LookupManager& lm);
    
    ~iPediaConnection();
    
    void setTerm(const ArsLexis::String& term)
    {term_=term;}
    
    void setPerformFullTextSearch(bool value)
    {performFullTextSearch_=value;}

    void setRandom()
    {getRandom_=true;}
    
    void setRetrieveArticleCount(bool value=true)
    {getArticleCount_=value;}
    
private:
    
    iPediaServerError serverError_;

    bool notFound_:1;
    bool registering_:1;
    bool performFullTextSearch_:1;
    bool getRandom_:1;
    bool getArticleCount_:1;
    
};

#endif