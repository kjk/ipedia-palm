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

    static const ushort_t serverErrorAlerts[]=
    {   
        serverFailureAlert,
        unsupportedDeviceAlert,
        invalidAuthorizationAlert,
        malformedRequestAlert,
        trialExpiredAlert
    };

}

using ArsLexis::status_t;

void LookupManager::handleServerError(iPediaServerError serverError)
{
    assert(serverErrorNone!=serverError);
    assert(serverErrorLast>=serverError);
    iPediaApplication::sendDisplayAlertEvent(serverErrorAlerts[serverError-1]);
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
    if (data.outcome==data.outcomeDefinition)
        handleDefinition();
}

bool LookupManager::lookupIfDifferent(const ArsLexis::String& term)
{
    using ArsLexis::equalsIgnoreCase;
    bool result=false;
    if (lastDefinitionElements_.empty() || !equalsIgnoreCase(lastInputTerm(), term))
    {
        lookupTerm(term);
        result=true;
    }
    return result;
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
    conn->setTerm(expression);
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

