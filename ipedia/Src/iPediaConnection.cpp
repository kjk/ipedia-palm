#include "iPediaConnection.hpp"
#include <iPediaApplication.hpp>
#include "DefinitionParser.hpp"
#include <SysUtils.hpp>
#include <DeviceInfo.hpp>
#include <Text.hpp>
#include "LookupManager.hpp"
#include <ipedia.h>

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
    performFullTextSearch_(false),
    getRandom_(false),
    regCodeValid_(regCodeTypeUnset)
{
}

iPediaConnection::~iPediaConnection()
{
    delete definitionParser_;
    delete searchResultsHandler_;
}

#define protocolVersion _T("1")

#define getDefinitionField      _T("Get-Definition")
#define getRandomField          _T("Get-Random-Article")
#define resultsForField         _T("Results-For")
#define definitionField         _T("Definition")
#define notFoundField           _T("Not-Found")
#define searchField             _T("Search")
#define searchResultsField      _T("Search-Results")
#define getArticleCountField    _T("Get-Article-Count")
#define articleCountField       _T("Article-Count")
#define getDatabaseTimeField    _T("Get-Database-Time")
#define databaseTimeField       _T("Database-Time")
#define verifyRegCodeField      _T("Verify-Registration-Code")
#define regCodeValidField       _T("Registration-Code-Valid")

void iPediaConnection::prepareRequest()
{
    iPediaApplication& app=iPediaApplication::instance();

    // decide if we want to send registration code. We don't send it if
    // we don't have it or if we're asking to verify registration code (a strange
    // but possible case when user re-enters registration code even though he
    // already provided valid reg code before)
    bool fSendRegCode = true;
    if (app.preferences().serialNumber.empty() || !regCodeToVerify.empty())
        fSendRegCode = false;

    bool fSendCookie = !fSendRegCode;
    // TODO: for now always send cookie because that's what the server expects
    fSendCookie = true;

    String request;
    appendField(request, protocolVersionField, protocolVersion);
    appendField(request, clientInfoField, "Palm 0.5" );
    char_t buffer[16];
    tprintf(buffer, _T("%08lx"), transactionId_);
    appendField(request, transactionIdField, buffer);

    if (fSendCookie)
    {
        if (chrNull==app.preferences().cookie[0])
            appendField(request, getCookieField, deviceInfoToken());
        else
            appendField(request, cookieField, app.preferences().cookie);
    }

    if (!term_.empty())
    {
        if (performFullTextSearch_)
            appendField(request, searchField, term_);
        else
            appendField(request, getDefinitionField, term_);
    }

    if (!regCodeToVerify.empty())
    {
        assert(!fSendRegCode);
        appendField(request, verifyRegCodeField, regCodeToVerify);
    }

    if (fSendRegCode)
        appendField(request, regCodeField, app.preferences().serialNumber);

    if (getRandom_)
    {
        assert(term_.empty());
        appendField(request, getRandomField);
    }

    // get number of articles and database update time in the first request to
    // the server. do it only once per application launch
    if (!app.fArticleCountChecked)
    {
        appendField(request, getArticleCountField);
        appendField(request, getDatabaseTimeField);
        app.fArticleCountChecked = true; // or do it later, when we process the response
    }

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

#ifdef DETAILED_CONNECTION_STATUS
    lookupManager_.setStatusText(_T("Opening connection..."));
#else
    lookupManager_.setStatusText(_T("Downloading article..."));
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
#ifdef DETAILED_CONNECTION_STATUS
    // sometimes we want to see detailed info about the connection stages
    // but for users we simplify as much as possible
    status=_T("Sending requests...");
#else
    status=_T("Downloading article...");
#endif

    lookupManager_.setStatusText(status);
    ArsLexis::sendEvent(LookupManager::lookupProgressEvent);

#if defined(_PALM_OS)        
    assert(!error);
    ArsLexis::SocketLinger linger;
    linger.portable.onOff=true;
    linger.portable.time=0;
    ArsLexis::Application& app=ArsLexis::Application::instance();
    // according to newsgroups in os 5 linger is broken and we need to do this
    // hack. Seems to help on Tungsten. However, on Treo 600 it doesn't seem
    // to be necessary
    if ( !isTreo600() && (5==app.romVersionMajor()))
        std::swap(linger.portable.onOff, linger.portable.time);
    error=socket().setLinger(linger);
    if (error)
    {
        log().debug()<<"setOption() returned error while setting linger: "<<error;
        error=errNone;
    }
#endif        
    return errNone;
}

ArsLexis::status_t iPediaConnection::notifyProgress()
{
    ArsLexis::status_t error=FieldPayloadProtocolConnection::notifyProgress();
    if (error)
        return error;

#ifdef DETAILED_CONNECTION_STATUS
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

// Called incrementally for each field/value we obtain from server's response.
// Based on those values accumulates internal state that can be inspected
// later after we get the whole response from the server.
// TODO: we should add some more checking of the type "regCodeValidField should
// be the only field send by the server (with the exception of standard fields
// like transactionIdField)
ArsLexis::status_t iPediaConnection::handleField(const String& name, const String& value)
{
    long                numValue;
    ArsLexis::status_t  error=errNone;
    iPediaApplication&  app=iPediaApplication::instance();

    if (transactionIdField==name)
    {
        error=numericValue(value, numValue, 16);
        if (error || (numValue!=transactionId_))
            error=errResponseMalformed;
    }
    else if (notFoundField==name)
        notFound_=true;
    else if (formatVersionField==name)
    {
        error=numericValue(value, numValue);
        if (!error)
            formatVersion_=numValue;
        else
            error=errResponseMalformed;
    }
    else if (resultsForField==name)
        resultsFor_=value;
    else if (name==definitionField)
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
    else if (searchResultsField==name)
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
    else if (cookieField==name)
    {
        if (value.length()>iPediaApplication::Preferences::cookieLength)
            error=errResponseMalformed;
        else
            app.preferences().cookie=value;
    }
    else if (errorField==name)
    {
        error=numericValue(value, numValue);
        if (error)
            return errResponseMalformed;
        if (numValue>=serverErrorFirst && numValue<=serverErrorLast)
            serverError_=static_cast<iPediaServerError>(numValue);
        else
            error=errResponseMalformed;
    }
    else if (articleCountField==name)
    {
        error=numericValue(value, numValue);
        if (error)
            error=errResponseMalformed;
        else
            app.preferences().articleCount=numValue;
    }
    else if (databaseTimeField==name)
    {
        app.preferences().databaseTime=value;
    }
    else if (regCodeValidField==name)
    {
        error=numericValue(value, numValue);
        if (error)
            return errResponseMalformed;

        if (1==numValue)
            regCodeValid_ = regCodeTypeValid;
        else if (0==numValue)
            regCodeValid_ = regCodeTypeInvalid;
        else
            error=errResponseMalformed;
    }
    else 
        error=FieldPayloadProtocolConnection::handleField(name, value);
    return error;
}

// called when the whole response from the server have been read
// inspects the state set during response parsing and sets appropriate
// outcome to be inspected by those who initiated requests
ArsLexis::status_t iPediaConnection::notifyFinished()
{
    ArsLexis::status_t error=FieldPayloadProtocolConnection::notifyFinished();
    if (error)
        return error;

    LookupFinishedEventData data;
    if (serverError_)
    {
        data.outcome=data.outcomeServerError;
        data.serverError=serverError_;
        ArsLexis::sendEvent(LookupManager::lookupFinishedEvent, data);
        assert(errNone==error);
        return errNone;
    }

    iPediaApplication& app=iPediaApplication::instance();
    if (NULL!=definitionParser_)
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
   
    if (notFound_)
        data.outcome=data.outcomeNotFound;

    if (regCodeTypeValid==regCodeValid_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome=data.outcomeRegCodeValid;
    }
    else if (regCodeTypeInvalid==regCodeValid_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome=data.outcomeRegCodeInvalid;
    }        

    ArsLexis::sendEvent(LookupManager::lookupFinishedEvent, data);

    assert( errNone == error );
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

