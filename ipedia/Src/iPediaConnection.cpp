#include "iPediaConnection.hpp"
#include <iPediaApplication.hpp>
#include "DefinitionParser.hpp"
#include <SysUtils.hpp>
#include <DeviceInfo.hpp>
#include <Text.hpp>
#include "LookupManager.hpp"
#include <ipedia.h>

iPediaConnection::iPediaConnection(LookupManager& lookupManager):
    FieldPayloadProtocolConnection(lookupManager.connectionManager()),
    lookupManager_(lookupManager),
    transactionId_(random((ulong_t)-1)),
    formatVersion_(0),
    definitionParser_(NULL),
    searchResultsHandler_(NULL),
    reverseLinksResultsHandler_(NULL),
    payloadType_(payloadNone),
    serverError_(serverErrorNone),
    notFound_(false),
    performFullTextSearch_(false),
    getRandom_(false),
    regCodeValid_(regCodeTypeUnset),
    fGetAvailableLangs_(false),
    isSwitchLangRequest_(false)
{
#ifdef _PALM_OS
    setTransferTimeout(SysTicksPerSecond() * 15);
#elif defined(_WIN32)
    setTransferTimeout(15000); // Timeout after 15 seconds of inactivity
#endif
}

iPediaConnection::~iPediaConnection()
{
    delete definitionParser_;
    delete searchResultsHandler_;
    delete reverseLinksResultsHandler_;
}

#define protocolVersion _T("1")

#define getArticleField         _T("Get-Article")
#define getArticleUField        _T("Get-Article-U")
#define getRandomField          _T("Get-Random-Article")
#define articleTitleField       _T("Article-Title")
#define articleBodyField        _T("Article-Body")
#define reverseLinksField       _T("Reverse-Links")
#define notFoundField           _T("Not-Found")
#define searchField             _T("Search")
#define searchResultsField      _T("Search-Results")
#define getArticleCountField    _T("Get-Article-Count")
#define articleCountField       _T("Article-Count")
#define getDatabaseTimeField    _T("Get-Database-Time")
#define databaseTimeField       _T("Database-Time")
#define verifyRegCodeField      _T("Verify-Registration-Code")
#define regCodeValidField       _T("Registration-Code-Valid")
#define getAvailableLangsField  _T("Get-Available-Langs")
#define availableLangsField     _T("Available-Langs")
#define useLangField            _T("Use-Lang")

#define lineSeparator _T("\n")

// Given a fieldName and fieldValue, make it a protocol field and add to the
// existing request.
// Format of protocol field:
// - if we have value: fieldName ": " fieldValue lineSeparator
// - if we don't have value: fieldName ":" lineSeparator
// Return NULL if failed to add it to existing request (memory allocation failed)
// TODO: this should always use char * instead of char_t * since we're constructing
// a char * value in the end
static DynStr *DynStrAddField(DynStr *dstr, const char_t *fieldName, const char_t *fieldValue)
{
    assert(NULL != fieldName);
    // TODO: could be optimized
    if (NULL == DynStrAppendCharP(dstr, fieldName))
        return NULL;

    if (NULL == fieldValue)
    {
        if (NULL == DynStrAppendChar(dstr, _T(':')))
            return NULL;
    }
    else
    {
        if (NULL == DynStrAppendCharPBuf(dstr, _T(": "), 2))
            return NULL;

        if (NULL == DynStrAppendCharP(dstr, fieldValue))
            return NULL;
    }

    if (NULL == DynStrAppendCharP(dstr, lineSeparator))
        return NULL;

    return dstr;
}

status_t iPediaConnection::prepareRequest()
{
    iPediaApplication& app = iPediaApplication::instance();

    // decide if we want to send registration code. We don't send it if
    // we don't have it or if we're asking to verify registration code (a strange
    // but possible case when user re-enters registration code even though he
    // already provided valid reg code before)
    bool fSendRegCode = true;
    if (app.preferences().regCode.empty() || !regCodeToVerify.empty())
        fSendRegCode = false;

    bool fSendCookie = !fSendRegCode;
 
    DynStr *request = DynStrNew(128);
    if (NULL == request)
        goto Error;

    if (NULL == DynStrAddField(request, protocolVersionField, protocolVersion))
        goto Error;

#if defined(_PALM_OS)
    if (NULL == DynStrAddField(request, clientInfoField, clientInfo))
        goto Error;
#endif
#if defined(WIN32_PLATFORM_PSPC)
    if (NULL == DynStrAddField(request, clientInfoField, pocketPCClientInfo ))
        goto Error;
#endif
#if defined(WIN32_PLATFORM_WFSP)
    if (NULL == DynStrAddField(request, clientInfoField, smartphoneClientInfo))
        goto Error;
#endif

    char_t buffer[16];
    tprintf(buffer, _T("%08lx"), transactionId_);
    if (NULL == DynStrAddField(request, transactionIdField, buffer))
        goto Error;

    if (fSendCookie)
    {
        if (chrNull==app.preferences().cookie[0])
        {
            if (NULL == DynStrAddField(request, getCookieField, deviceInfoToken().c_str()))
                goto Error;
        }
        else
        {
            if (NULL == DynStrAddField(request, cookieField, app.preferences().cookie.c_str()))
                goto Error;
        }
    }

    if (!newDbLangCode_.empty())
    {
        // a bit of a hack but this one has priority over langToUse
        if (NULL == DynStrAddField(request, useLangField, newDbLangCode_.c_str()))
            goto Error;
    }
    else if (!langToUse_.empty())
    {
        if (NULL == DynStrAddField(request, useLangField, langToUse_.c_str()))
            goto Error;
    }

    if (!term_.empty())
    {
        if (performFullTextSearch_)
        {
            if (NULL == DynStrAddField(request, searchField, term_.c_str()))
                goto Error;
        }
        else
        {
            if (NULL == DynStrAddField(request, getArticleField, term_.c_str()))
                goto Error;
        }
    }

    if (!regCodeToVerify.empty())
    {
        assert(!fSendRegCode);
        if (NULL == DynStrAddField(request, verifyRegCodeField, regCodeToVerify.c_str()))
            goto Error;
    }

    if (fSendRegCode)
        if (NULL == DynStrAddField(request, regCodeField, app.preferences().regCode.c_str()))
            goto Error;

    if (getRandom_)
    {
        assert(term_.empty());
        if (NULL == DynStrAddField(request, getRandomField, NULL))
            goto Error;
    }

    // get article count from the server when during first request or after a day
    // (because on smartphone applications rarely quit)
    bool fNeedsToGetArticleCount;
	fNeedsToGetArticleCount = false;

    if (!app.fArticleCountChecked || !newDbLangCode_.empty())
    {
        fNeedsToGetArticleCount = true;
    }

#ifdef _WIN32
    // wince only code
    SYSTEMTIME currTime;
    GetSystemTime(&currTime);
    if (currTime.wDay != app.lastArticleCountCheckTime.wDay)
    {
        fNeedsToGetArticleCount = true;
    }
#endif

    if (fNeedsToGetArticleCount)
    {
        if (NULL == DynStrAddField(request, getArticleCountField, NULL))
            goto Error;
        if (NULL == DynStrAddField(request, getDatabaseTimeField, NULL))
            goto Error;
        if (NULL == DynStrAddField(request, getAvailableLangsField, NULL))
            goto Error;
#ifdef _WIN32
        // wince only code
        GetSystemTime(&app.lastArticleCountCheckTime);
#endif
    }

    if (NULL == DynStrAppendChar(request, _T('\n')))
        goto Error;

#ifdef _PALM_OS
    ulong_t len = DynStrLen(request);
    setRequestOwn(DynStrReleaseStr(request), len); 
#else
    char* newReq;
	newReq = Utf16ToStr(DynStrGetCStr(request), DynStrLen(request));
    if (NULL == newReq)
        goto Error;
    setRequestOwn(newReq, strlen(newReq)); 
#endif
    DynStrDelete(request);
    return errNone;
Error:
    if (NULL != request)
        DynStrDelete(request);
    return memErrNotEnoughSpace;
}

status_t iPediaConnection::enqueue()
{
    status_t error=FieldPayloadProtocolConnection::enqueue();
    if (error)
        return error;

#ifdef DETAILED_CONNECTION_STATUS
    lookupManager_.setStatusText(_T("Opening connection..."));
#else
    lookupManager_.setStatusText(_T("Downloading data..."));
#endif
    lookupManager_.setPercentProgress(LookupManager::percentProgressDisabled);
    sendEvent(LookupManager::lookupStartedEvent);
    return errNone;
}

status_t iPediaConnection::open()
{
    status_t error;

    error = prepareRequest();
    if (errNone != error)
        return error;

    error = SimpleSocketConnection::open();
    if (error)
        return error;

#ifdef DETAILED_CONNECTION_STATUS
    // sometimes we want to see detailed info about the connection stages
    // but for users we simplify as much as possible
    lookupManager_.setStatusText(_T("Sending requests..."));
#else    
    lookupManager_.setStatusText(_T("Downloading data..."));
#endif

    sendEvent(LookupManager::lookupProgressEvent);

#if defined(_PALM_OS)        
    assert(!error);
    SocketLinger linger;
    linger.portable.onOff = true;
    linger.portable.time = 0;
    Application& app=Application::instance();
    // according to newsgroups in os 5 linger is broken and we need to do this
    // hack. Seems to help on Tungsten. However, on Treo 600 it doesn't seem
    // to be necessary
    if ( !isTreo600() && (5==romVersionMajor()))
        std::swap(linger.portable.onOff, linger.portable.time);
    error=socket().setLinger(linger);
    if (error)
    {
        //log().debug()<<"setOption() returned error while setting linger: "<<error;
        error=errNone;
    }
#endif        
    return errNone;
}

status_t iPediaConnection::notifyProgress()
{
    status_t error = FieldPayloadProtocolConnection::notifyProgress();
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
            status = _T("Downloading data...");
    }
    lookupManager_.setStatusText(status.c_txt());
#else
    lookupManager_.setStatusText(_T("Downloading data..."));
#endif
    uint_t progress=LookupManager::percentProgressDisabled;
    if (inPayload_)
        progress = ((payloadLength()-payloadLengthLeft())*100L)/payloadLength();
    lookupManager_.setPercentProgress(progress);
    sendEvent(LookupManager::lookupProgressEvent);
    return error;
}

// Called incrementally for each field/value we obtain from server's response.
// Based on those values accumulates internal state that can be inspected
// later after we get the whole response from the server.
// TODO: we should add some more checking of the type "regCodeValidField should
// be the only field send by the server (with the exception of standard fields
// like transactionIdField)
status_t iPediaConnection::handleField(const char_t *name, const char_t *value)
{
    long            numValue;
    status_t        error = errNone;
    iPediaApplication&  app = iPediaApplication::instance();

    if (0 == tstrcmp(transactionIdField, name))
    {
        error = numericValue(value, numValue, 16);
        assert(errNone==error);
        if (error || ((ulong_t)numValue!=transactionId_))
            error = errResponseMalformed;
    }
    else if (0 == tstrcmp(notFoundField, name))
    {
        notFound_ = true;
    }
    else if (0 == tstrcmp(formatVersionField, name))
    {
        error = numericValue(value, numValue);
        assert(errNone==error);
        if (errNone!=error)
            error = errResponseMalformed;
        else
            formatVersion_ = numValue;
    }
    else if (0 == tstrcmp(articleTitleField, name))
    {
        articleTitle_ = value;
    }
    else if (0 == tstrcmp(articleBodyField, name))
    {
        error=numericValue(value, numValue);
        assert(errNone==error);
        if (errNone!=error)
            error = errResponseMalformed;
        else
        {
            DefinitionParser* parser=new DefinitionParser();
            startPayload(parser, numValue);
            payloadType_ = payloadArticleBody;
        }
    }
    else if (0 == tstrcmp(reverseLinksField, name))
    {
        error = numericValue(value, numValue);
        assert(errNone==error);
        if (errNone!=error)
            error = errResponseMalformed;
        else
        {
            ReverseLinksResultsHandler* parser = new ReverseLinksResultsHandler();
            startPayload(parser, numValue);
            payloadType_ = payloadReverseLinks;
        }
    }
    else if (0 == tstrcmp(searchResultsField, name))
    {
        error = numericValue(value, numValue);
        assert(errNone==error);
        if (error)
            error = errResponseMalformed;
        else
        {
            SearchResultsHandler* handler=new SearchResultsHandler();
            startPayload(handler, numValue);
            payloadType_ = payloadSearchResults;
        }
    }
    else if (0 == tstrcmp(cookieField, name))
    {
        assert(tstrlen(value)<=iPediaApplication::Preferences::cookieLength);
        if (tstrlen(value)>iPediaApplication::Preferences::cookieLength)
            error = errResponseMalformed;
        else
            app.preferences().cookie=value;
    }
    else if (0 == tstrcmp(errorField, name))
    {
        error = numericValue(value, numValue);
        assert(errNone==error);
        if (error)
            return errResponseMalformed;
        if (numValue>=serverErrorFirst && numValue<=serverErrorLast)
            serverError_ = static_cast<iPediaServerError>(numValue);
        else
        {
            assert(false);
            error = errResponseMalformed;
        }
    }
    else if (0 == tstrcmp(articleCountField, name))
    {
        error=numericValue(value, numValue);
        assert(errNone==error);
        if (error)
            error=errResponseMalformed;
        else
        {
            app.preferences().articleCount = numValue;
            app.fArticleCountChecked = true;
        }
    }
    else if (0 == tstrcmp(databaseTimeField, name))
    {
        app.preferences().databaseTime = value;
    }
    else if (0 == tstrcmp(availableLangsField, name))
    {
        app.preferences().availableLangs = value;
    }
    else if (0 == tstrcmp(regCodeValidField, name))
    {
        error = numericValue(value, numValue);
        assert(errNone==error);
        if (error)
            return errResponseMalformed;
        assert((0==numValue) || (1==numValue));
        if (1==numValue)
            regCodeValid_ = regCodeTypeValid;
        else if (0==numValue)
            regCodeValid_ = regCodeTypeInvalid;
        else
            error = errResponseMalformed;
    }
    else
        error = FieldPayloadProtocolConnection::handleField(name, value);
    return error;
}

// called when the whole response from the server have been read
// inspects the state set during response parsing and sets appropriate
// outcome to be inspected by those who initiated requests
status_t iPediaConnection::notifyFinished()
{
    status_t error = FieldPayloadProtocolConnection::notifyFinished();
    if (error)
        return error;

    LookupFinishedEventData data;
    if (serverError_)
    {
        data.outcome = data.outcomeServerError;
        data.serverError = serverError_;
        sendEvent(LookupManager::lookupFinishedEvent, data);
        assert(errNone==error);
        return errNone;
    }

    iPediaApplication& app=iPediaApplication::instance();
    if (!newDbLangCode_.empty() && isSwitchLangRequest_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome = data.outcomeDatabaseSwitched;
        app.preferences().currentLang.assign(newDbLangCode_);
    }

    if (NULL!=definitionParser_)
    {
		DefinitionModel* model = definitionParser_->createModel();
		if (NULL == model)
			return memErrNotEnoughSpace;

		PassOwnership(model, lookupManager_.lastDefinitionModel);		
		
        lookupManager_.setLastFoundTerm(articleTitle_);
        lookupManager_.lastFoundLang_ = lookupManager_.lastSearchLang_;
        if (getRandom_)
            lookupManager_.setLastSearchTerm(articleTitle_);
        data.outcome = data.outcomeArticleBody;
    }

    if (NULL!=reverseLinksResultsHandler_)
    {
        // TODO: we don't handle Reverse-Links field yet in the client
        assert(NULL != definitionParser_);
        lookupManager_.setLastReverseLinks(reverseLinksResultsHandler_->reverseLinksResults());        
    }

    if (NULL!=searchResultsHandler_)
    {
        assert(NULL == definitionParser_);
        lookupManager_.setLastExtendedSearchResults(searchResultsHandler_->searchResults());
        lookupManager_.setLastExtendedSearchTerm(articleTitle_);
        data.outcome = data.outcomeList;
    }

    if (notFound_)
        data.outcome = data.outcomeNotFound;

    if (regCodeTypeValid==regCodeValid_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome = data.outcomeRegCodeValid;
    }
    else if (regCodeTypeInvalid==regCodeValid_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome = data.outcomeRegCodeInvalid;
    }        

    if (fGetAvailableLangs_)
    {
        assert(data.outcomeNothing==data.outcome);
        data.outcome = data.outcomeAvailableLangs;
        // we already have available langs in  app.preferences().availableLangs
    }

    assert(data.outcomeNothing!=data.outcome);
    if (data.outcomeNothing==data.outcome)
        return errResponseMalformed;

    sendEvent(LookupManager::lookupFinishedEvent, data);

    assert(errNone == error);
    return error;        
}

void iPediaConnection::handleError(status_t error)
{
    //log().error()<<_T("handleError(): error code ")<<error;
    LookupFinishedEventData data(LookupFinishedEventData::outcomeError, error);
    sendEvent(LookupManager::lookupFinishedEvent, data);
    SimpleSocketConnection::handleError(error);
}

status_t iPediaConnection::notifyPayloadFinished()
{
    switch (payloadType_)
    {
        case payloadArticleBody:
            delete definitionParser_;
            definitionParser_=static_cast<DefinitionParser*>(releasePayloadHandler());
            break;
        
        case payloadSearchResults:
            delete searchResultsHandler_;
            searchResultsHandler_=static_cast<SearchResultsHandler*>(releasePayloadHandler());
            break;

        case payloadReverseLinks:
            delete reverseLinksResultsHandler_;
            reverseLinksResultsHandler_=static_cast<ReverseLinksResultsHandler*>(releasePayloadHandler());
            break;

        default:
            assert(false);
    }
    payloadType_ = payloadNone;
    return FieldPayloadProtocolConnection::notifyPayloadFinished();
}

