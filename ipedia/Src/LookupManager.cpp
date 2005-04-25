#include <LookupManager.hpp>
#include "LookupHistory.hpp"
#include <iPediaConnection.hpp>
#include "DefinitionElement.hpp"
#include <Text.hpp>
#include "ipedia_Rsc.h"

LookupManager::~LookupManager()
{
	delete lastDefinitionModel;
}

namespace {

#ifdef __MWERKS__
#pragma pcrelconstdata on
#endif

static const uint_t serverErrorToAlertMap[][2]=
{
    { serverErrorFailure, serverFailureAlert},
    { serverErrorUnsupportedDevice, unsupportedDeviceAlert},
    { serverErrorInvalidRegCode, invalidRegCodeAlert},
    { serverErrorMalformedRequest, malformedRequestAlert },
    { serverErrorLookupLimitReached, lookupLimitReachedAlert},
    { serverErrorInvalidRequest, invalidRequestAlert},
    { serverErrorInvalidCookie, invalidCookieAlert},
    { serverErrorUnexpectedRequestArgument, unexpectedRequestArgumentAlert},
    { serverErrorRequestArgumentMissing, requestArgumentMissingAlert},
    { serverErrorInvalidProtocolVersion, invalidProtocolVersionAlert},
    { serverErrorUserDisabled, userDisabledAlert},
};

} // namespace

using ArsLexis::status_t;

LookupManager::LookupManager(LookupHistory& history):
    history_(history),
    historyChange_(historyMoveForward),
	lastDefinitionModel(NULL)
{
    iPediaApplication& app = iPediaApplication::instance();
    lastFoundLang_ = lastSearchLang_ = app.preferences().currentLang;
}
    


// map errors that can be returned from the server to alerts that we display
// in the ui for this error. 
// returning 0 means there's no mapping for this error
static uint_t getAlertIdFromServerError(iPediaServerError serverError)
{
    assert(serverErrorNone!=serverError);
    assert(serverErrorLast>=serverError);
    
    uint_t error = (uint_t)serverError;
    int    arrSize = sizeof(serverErrorToAlertMap)/sizeof(serverErrorToAlertMap[0]);
    for (int i=0; i<arrSize; i++)
    {
        if (error==serverErrorToAlertMap[i][0])
            return serverErrorToAlertMap[i][1];
    }
    return 0;
}

void LookupManager::handleServerError(iPediaServerError serverError)
{

    if (serverErrorForceUpgrade == serverError)
    {
        // special treatment - this doesn't map to a simple alert, so we
        // need to trigger more complicated handling
        sendEvent(iPediaApplication::appForceUpgrade);
        return;
    }
    if (serverErrorLangNotAvailable == serverError)
    {
        sendEvent(iPediaApplication::appLangNotAvailable);
        return;
    }
    uint_t alertId = getAlertIdFromServerError(serverError);
    if (0==alertId)
        alertId = serverFailureAlert;
    
    iPediaApplication::sendDisplayAlertEvent(alertId);

    lastSearchTerm_.clear();
    lastExtendedSearchTerm_.clear();
}

void LookupManager::handleConnectionError(status_t error)
{
    ushort_t alertId=connectionErrorAlert;
    switch (error)
    {
        case SocketConnection::errResponseTooLong:
            alertId=articleTooLongAlert;
            break;
            
        case SocketConnection::errResponseMalformed:
            alertId=malformedResponseAlert;
            break;
            
        case SocketConnection::errNetLibUnavailable:
            alertId=networkUnavailableAlert;
            break;
        
        case netErrTimeout:
            alertId=connectionTimedOutAlert;
            break;

        case netErrSocketClosedByRemote:
            // this most likely means we couldn't even connect to the server
            // i.e. server is not even running
            alertId=connectionServerNotRunning;
            break;

        case memErrNotEnoughSpace:
            alertId=notEnoughMemoryAlert;
            break;            

    }

    lastSearchTerm_.clear();
    lastExtendedSearchTerm_.clear();

    iPediaApplication::sendDisplayAlertEvent(alertId);
}

void LookupManager::handleDefinition()
{
    switch (historyChange_)
    {
        case historyReplaceForward:
            history_.replaceAllNext(lastFoundTerm_, lastFoundLang_);
            break;
        
        case historyMoveBack:
            history_.movePrevious(lastFoundTerm_, lastFoundLang_);
            break;
        
        case historyMoveForward:
            history_.moveNext(lastFoundTerm_, lastFoundLang_);
            break;
    }
}

void LookupManager::handleDefinitionMissing()
{
    iPediaApplication& app=iPediaApplication::instance();
    app.sendDisplayCustomAlertEvent(articleNotFoundAlert, lastSearchTerm());
}


void LookupManager::handleLookupFinishedInForm(const LookupFinishedEventData& data)
{
    switch (data.outcome)
    {
        case data.outcomeError:
            handleConnectionError(data.error);
            break;
        
        case data.outcomeServerError:
            handleServerError(data.serverError);
            break;
            
        case data.outcomeNotFound:
            handleDefinitionMissing();
            break;
    }
}

void LookupManager::handleLookupFinished(const LookupFinishedEventData& data)
{
    if (data.outcome==data.outcomeArticleBody)
        handleDefinition();
}

// return true if last search term is different than term
bool LookupManager::lastSearchTermDifferent(const String& term, const String& lang)
{
    if (lastSearchTerm().empty() || !equalsIgnoreCase(lastSearchTerm(), term) || (!lang.empty() && lang != lastSearchLang_))
        return true;
    return false;
}

// if search term is different than the last one, initiate lookup and return true.
// otherwise return false.
bool LookupManager::lookupIfDifferent(const String& term, const String& lang)
{
    if (!lastSearchTermDifferent(term, lang))
        return false;

    lastSearchTerm_ = term;
    lookupTerm(term, lang);
    return true;
}

void LookupManager::lookupTerm(const String& term, const String& lang)
{
    historyChange_ = historyReplaceForward;
    iPediaConnection* conn = new iPediaConnection(*this);
    lastSearchTerm_ = term;
    if (!lang.empty())
        lastSearchLang_ = lang;
    else
        lastSearchLang_ = lastFoundLang_;
    conn->setTerm(term);
    conn->setLang(lastSearchLang_);
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->enqueue();
}

void LookupManager::switchDatabase(const char_t* langCode)
{
    iPediaApplication& app=iPediaApplication::instance();
    iPediaConnection* conn = new iPediaConnection(*this);
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->switchDatabase(langCode);
    conn->enqueue();
}

void LookupManager::getAvailableLangs()
{
    iPediaConnection* conn = new iPediaConnection(*this);
    conn->getAvailableLangs();
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->enqueue();
}

void LookupManager::lookupRandomTerm()
{
    historyChange_ = historyReplaceForward;
    iPediaConnection* conn = new iPediaConnection(*this);
    conn->setRandom();
    iPediaApplication& app = iPediaApplication::instance();
    conn->setLang(lastSearchLang_ = app.preferences().currentLang);
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->enqueue();
}

void LookupManager::search(const ArsLexis::String& expression)
{
    historyChange_ = historyReplaceForward;
    iPediaConnection* conn = new iPediaConnection(*this);
    lastSearchTerm_ = expression;
    conn->setTerm(expression);
    iPediaApplication& app = iPediaApplication::instance();
    conn->setLang(lastSearchLang_ = app.preferences().currentLang);
    conn->setPerformFullTextSearch(true);
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->enqueue();
}

void LookupManager::moveHistory(bool forward)
{
    if ((forward && history_.hasNext()) || (!forward && history_.hasPrevious()))
    {
        historyChange_ = historyMoveBack;
        if (forward)
            historyChange_ = historyMoveForward;
        iPediaConnection* conn=new iPediaConnection(*this);
        if (forward)
        {
            lastSearchTerm_ = history_.nextTerm();
            lastSearchLang_ = history_.nextLang();
        }
        else
        {
            lastSearchTerm_ = history_.previousTerm();
            lastSearchLang_ = history_.previousLang();
        }

        conn->setTerm(lastSearchTerm_);
        conn->setLang(lastSearchLang_);
        conn->serverAddress = iPediaApplication::instance().serverAddress;
        conn->enqueue();
    }
}

// send a Verify-Registration-Code query to the server with value being
// registration code. Server responds with Registration-Code-Valid whose value
// is 1 (reg code valid) or 0 (reg code invalid)
void LookupManager::verifyRegistrationCode(const ArsLexis::String& regCode)
{
    iPediaConnection* conn = new iPediaConnection(*this);
    conn->regCodeToVerify = regCode;
    conn->serverAddress = iPediaApplication::instance().serverAddress;
    conn->enqueue();
}

bool LookupManager::hasPreviousHistoryTerm() const
{
    return  history_.hasPrevious(); 
}

bool LookupManager::hasNextHistoryTerm() const 
{
    return history_.hasNext(); 
}

