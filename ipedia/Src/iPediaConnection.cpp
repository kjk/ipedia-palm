#include "iPediaConnection.hpp"
#include <iPediaApplication.hpp>
#include "DefinitionParser.hpp"
#include <SysUtils.hpp>
#include <DeviceInfo.hpp>
#include <Text.hpp>
#include "LookupManager.hpp"
#include "ipedia.h"

using namespace ArsLexis;

iPediaConnection::iPediaConnection(LookupManager& lookupManager):
    FieldPayloadProtocolConnection(lookupManager.connectionManager()),
    lookupManager_(lookupManager),
    transactionId_(random((ulong_t)-1)),
    formatVersion_(0),
    definitionParser_(0),
    searchResultsHandler_(0),
    payloadType_(payloadNone),
    serverError_(serverErrorNone),
    notFound_(false),
    registering_(false),
    performFullTextSearch_(false),
    getRandom_(false),
    getArticleCount_(false)
{
}

iPediaConnection::~iPediaConnection()
{
    delete definitionParser_;
    delete searchResultsHandler_;
}

#define protocolVersion _T("1")

#define transactionIdField      _T("Transaction-ID")
#define protocolVersionField    _T("Protocol-Version")
#define clientVersionField      _T("Client-Version")
#define getCookieField          _T("Get-Cookie")
#define getDefinitionField      _T("Get-Definition")
#define getRandomDefField       _T("Get-Random-Definition")
#define cookieField             _T("Cookie")
#define registerField           _T("Register")
#define formatVersionField      _T("Format-Version")
#define resultsForField         _T("Results-For")
#define definitionField         _T("Definition")
#define errorField              _T("Error")
#define notFoundField           _T("Not-Found")
#define searchField             _T("Search")
#define searchResultsField      _T("Search-Results")
#define getArticleCountField    _T("Get-Article-Count")
#define articleCountField       _T("Article-Count")

void iPediaConnection::prepareRequest()
{
    iPediaApplication& app=iPediaApplication::instance();
    String request;
    appendField(request, protocolVersionField, protocolVersion);
    appendField(request, clientVersionField, appVersion);
    char_t buffer[9];
    tprintf(buffer, _T("%lx"), transactionId_);
    appendField(request, transactionIdField, buffer);
    if (chrNull==app.preferences().cookie[0])
        appendField(request, getCookieField, deviceInfoToken());
    else
        appendField(request, cookieField, app.preferences().cookie);

    if (!term_.empty())
        appendField(request, (performFullTextSearch_?searchField:getDefinitionField), term_);

    registering_=!(app.preferences().serialNumberRegistered || chrNull==app.preferences().serialNumber[0]);
    if (registering_)
        appendField(request, registerField, app.preferences().serialNumber);

    if (getRandom_)
    {
        assert(term_.empty());
        appendField(request, getRandomDefField);
    }
    
    if (getArticleCount_)
        appendField(request, getArticleCountField);

    request+='\n';
    NarrowString req;
    TextToByteStream(request, req);
    setRequest(req); 
}

ArsLexis::status_t iPediaConnection::enqueue()
{
    ArsLexis::status_t error=FieldPayloadProtocolConnection::enqueue();
    if (error)
        return error;

#ifdef INTERNAL_BUILD
    lookupManager_.setStatusText(_T("Opening connection..."));
#else
    lookupManager_.setStatusText(_T("Downloading article"));
#endif
    lookupManager_.setPercentProgress(LookupManager::percentProgressDisabled);
    ArsLexis::sendEvent(LookupManager::lookupStartedEvent);
    return errNone;
}

ArsLexis::status_t iPediaConnection::open()
{
    
    prepareRequest();
    ArsLexis::status_t error=SimpleSocketConnection::open();
    if (error)
        return error;

    String status;
#ifdef INTERNAL_BUILD
    // we want to see detailed info about the connection stages
    // in internal build, but for users we simplify as much as possible
    status=_T("Sending requests...");
#else
    status=+T("Downloading article");
#endif

    lookupManager_.setStatusText(status);
    ArsLexis::sendEvent(LookupManager::lookupProgressEvent);
        
#if defined(_PALM_OS)        
    if (!error)
    {
        ArsLexis::SocketLinger linger;
        linger.portable.onOff=true;
        linger.portable.time=0;
        error=socket().setLinger(linger);
        if (error)
        {
            log().debug()<<"setOption() returned error while setting linger: "<<error;
            error=errNone;
        }
    }
#endif        
    return errNone;
}

ArsLexis::status_t iPediaConnection::notifyProgress()
{
    ArsLexis::status_t error=FieldPayloadProtocolConnection::notifyProgress();
    if (error)
        return error;

#ifdef INTERNAL_BUILD
    String status;
    if (sending())
        status = _T("Sending request...");
    else
    {
        if (response().empty())
            status = _T("Waiting for server\'s answer...");
        else
            status = _T("Downloading article...");
    }
    lookupManager_.setStatusText(status);
#else
    lookupManager_.setStatusText(_T("Downloading article..."));
#endif
    uint_t progress=LookupManager::percentProgressDisabled;
    if (inPayload())
        progress=((payloadLength()-payloadLengthLeft())*100L)/payloadLength();
    lookupManager_.setPercentProgress(progress);
    ArsLexis::sendEvent(LookupManager::lookupProgressEvent);
    return error;
}


ArsLexis::status_t iPediaConnection::handleField(const String& name, const String& value)
{
    long numValue;
    ArsLexis::status_t error=errNone;
    if (0==name.find(transactionIdField))
    {
        error=numericValue(value, numValue, 16);
        if (error || (numValue!=transactionId_))
            error=errResponseMalformed;
    }
    else if (0==name.find(notFoundField))
        notFound_=true;
    else if (0==name.find(formatVersionField))
    {
        error=numericValue(value, numValue);
        if (!error)
            formatVersion_=numValue;
        else
            error=errResponseMalformed;
    }
    else if (0==name.find(resultsForField))
        resultsFor_=value;
    else if (0==name.find(definitionField))
    {
        error=numericValue(value, numValue);
        if (!error)
        {
            DefinitionParser* parser=new DefinitionParser();
            startPayload(parser, numValue);
            payloadType_=payloadDefinition;
        }
        else
            error=errResponseMalformed;
    }
    else if (0==name.find(searchResultsField))
    {
        error=numericValue(value, numValue);
        if (!error)
        {
            SearchResultsHandler* handler=new SearchResultsHandler();
            startPayload(handler, numValue);
            payloadType_=payloadSearchResults;
        }
        else
            error=errResponseMalformed;
    }
    else if (0==name.find(cookieField))
    {
        iPediaApplication& app=iPediaApplication::instance();
        if (value.length()>iPediaApplication::Preferences::cookieLength)
            error=errResponseMalformed;
        else
            app.preferences().cookie=value;
    }
    else if (0==name.find(errorField))
    {
        error=numericValue(value, numValue);
        if (!error)
        {
            if (numValue>=serverErrorFirst && numValue<=serverErrorLast)
                serverError_=static_cast<iPediaServerError>(numValue);
            else
                error=errResponseMalformed;
        }            
        else
            error=errResponseMalformed;
    }
    else if (0==name.find(articleCountField))
    {
        error=numericValue(value, numValue);
        if (!error)
        {
            iPediaApplication& app=iPediaApplication::instance();
            app.preferences().articleCount=numValue;
        }
        else
            error=errResponseMalformed;
    }
    else 
        error=FieldPayloadProtocolConnection::handleField(name, value);
    return error;
}

ArsLexis::status_t iPediaConnection::notifyFinished()
{
    ArsLexis::status_t error=FieldPayloadProtocolConnection::notifyFinished();
    if (!error)
    {
        LookupFinishedEventData data;
        if (!serverError_)
        {
            iPediaApplication& app=iPediaApplication::instance();
            if (definitionParser_!=0)
            {
                std::swap(definitionParser_->elements(), lookupManager_.lastDefinitionElements());
                lookupManager_.setLastFoundTerm(resultsFor_);
                if (getRandom_)
                    lookupManager_.setLastInputTerm(resultsFor_);
                data.outcome=data.outcomeDefinition;
            }
            if (searchResultsHandler_!=0)
            {
                lookupManager_.setLastSearchResults(searchResultsHandler_->searchResults());
                lookupManager_.setLastSearchExpression(resultsFor_);
                data.outcome=data.outcomeList;
            }

            if (registering_ && !serverError_)
                app.preferences().serialNumberRegistered=true;
            
            if (notFound_)
                data.outcome=data.outcomeNotFound;
        }
        else
        {
            data.outcome=data.outcomeServerError;
            data.serverError=serverError_;
        }
        ArsLexis::sendEvent(LookupManager::lookupFinishedEvent, data);               
    }
    return error;        
}

void iPediaConnection::handleError(ArsLexis::status_t error)
{
    log().error()<<_T("handleError(): error code ")<<error;
    LookupFinishedEventData data(LookupFinishedEventData::outcomeError, error);
    ArsLexis::sendEvent(LookupManager::lookupFinishedEvent, data);
    SimpleSocketConnection::handleError(error);
}

void iPediaConnection::notifyPayloadFinished()
{
    switch (payloadType_)
    {
        case payloadDefinition:
            delete definitionParser_;
            definitionParser_=static_cast<DefinitionParser*>(releasePayloadHandler());
            break;
        
        case payloadSearchResults:
            delete searchResultsHandler_;
            searchResultsHandler_=static_cast<SearchResultsHandler*>(releasePayloadHandler());
            break;
            
        default:
            assert(false);
    }
    payloadType_=payloadNone;
    FieldPayloadProtocolConnection::notifyPayloadFinished();
}

