#include <LookupManager.hpp>
#include "LookupHistory.hpp"
#include <iPediaConnection.hpp>
#include "DefinitionElement.hpp"
#include <Text.hpp>
#include "ipedia_Rsc.h"

LookupManager::~LookupManager()
{
    std::for_each(lastDefinitionElements_.begin(), lastDefinitionElements_.end(), ArsLexis::ObjectDeleter<DefinitionElement>());
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
    { serverErrorUserDisabled, userDisabledAlert}
};

} // namespace

using ArsLexis::status_t;

// 0 means not found
static uint_t getAlertFromServerError(iPediaServerError serverError)
{
    assert(serverErrorNone!=serverError);
    assert(serverErrorLast>=serverError);
    
    uint_t error = (uint_t)serverError;
    int arrSize = sizeof(serverErrorToAlertMap)/sizeof(serverErrorToAlertMap[0]);
    for (int i=0; i<arrSize; i++)
    {
        if (error==serverErrorToAlertMap[i][0])
            return serverErrorToAlertMap[i][1];
    }
    return 0;
}

void LookupManager::handleServerError(iPediaServerError serverError)
{
    uint_t alertId = getAlertFromServerError(serverError);
    if (0==alertId)
        iPediaApplication::sendDisplayAlertEvent(serverFailureAlert);
    else
        iPediaApplication::sendDisplayAlertEvent(alertId);
    lastInputTerm_ = _T("");
    lastSearchExpression_ = _T("");
}

void LookupManager::handleConnectionError(status_t error)
{
    using ArsLexis::SocketConnection;
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

    lastInputTerm_ = _T("");
    lastSearchExpression_ = _T("");

    iPediaApplication::sendDisplayAlertEvent(alertId);
}

void LookupManager::handleDefinition()
{
    switch (historyChange_)
    {
        case historyReplaceForward:
            history_.replaceAllNext(lastFoundTerm_);
            break;
        
        case historyMoveBack:
            history_.movePrevious(lastFoundTerm_);
            break;
        
        case historyMoveForward:
            history_.moveNext(lastFoundTerm_);
            break;
    }
}

void LookupManager::handleDefinitionMissing()
{
    iPediaApplication& app=iPediaApplication::instance();
    app.sendDisplayCustomAlertEvent(articleNotFoundAlert, lastInputTerm());
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

// if search term is different than the last one, initiate lookup and return true.
// otherwise return false.
bool LookupManager::lookupIfDifferent(const ArsLexis::String& term)
{
    using ArsLexis::equalsIgnoreCase;
    if (lastInputTerm().empty() || !equalsIgnoreCase(lastInputTerm(), term))
    {
        lastInputTerm_ = term;
        lookupTerm(term);
        return true;
    }
    return false;
}

void LookupManager::lookupTerm(const ArsLexis::String& term)
{
    historyChange_=historyReplaceForward;
    iPediaConnection* conn=new iPediaConnection(*this);
    conn->setTerm(lastInputTerm_=term);
    conn->setAddress(iPediaApplication::instance().server());
    conn->enqueue();
}

void LookupManager::lookupRandomTerm()
{
    historyChange_=historyReplaceForward;
    iPediaConnection* conn=new iPediaConnection(*this);
    conn->setRandom();
    conn->setAddress(iPediaApplication::instance().server());
    conn->enqueue();
}

void LookupManager::search(const ArsLexis::String& expression)
{
    historyChange_=historyReplaceForward;
    iPediaConnection* conn=new iPediaConnection(*this);
    conn->setTerm(lastInputTerm_=expression);
    conn->setPerformFullTextSearch(true);
    conn->setAddress(iPediaApplication::instance().server());
    conn->enqueue();
}


void LookupManager::moveHistory(bool forward)
{
    if ((forward && history_.hasNext()) || (!forward && history_.hasPrevious()))
    {
        historyChange_=(forward?historyMoveForward:historyMoveBack);
        iPediaConnection* conn=new iPediaConnection(*this);
        conn->setTerm(lastInputTerm_=(forward?history_.nextTerm():history_.previousTerm()));
        conn->setAddress(iPediaApplication::instance().server());
        conn->enqueue();
    }
}

// send a Verify-Registration-Code query to the server with value being
// registration code. Server responds with Registration-Code-Valid whose value
// is 1 (reg code valid) or 0 (reg code invalid)
void LookupManager::verifyRegistrationCode(const ArsLexis::String& regCode)
{
    iPediaConnection* conn=new iPediaConnection(*this);
    conn->regCodeToVerify = regCode;
    conn->setAddress(iPediaApplication::instance().server());
    conn->enqueue();
}

bool LookupManager::hasPreviousHistoryTerm() const
{ return  history_.hasPrevious(); }

bool LookupManager::hasNextHistoryTerm() const 
{ return history_.hasNext(); }
