#ifndef __LOOKUP_MANAGER_HPP__
#define __LOOKUP_MANAGER_HPP__

#include <LookupManagerBase.hpp>
#include <iPediaApplication.hpp>
#include "Definition.hpp"

class LookupHistory;

// For description of errors, see iPediaServer.py, class iPediaServerError
// When adding new errors, don't forget to update serverErrorToAlertMap
// in LookupManager.cpp
enum iPediaServerError
{
    serverErrorNone,
    serverErrorFailure              = 1,
    serverErrorFirst                = serverErrorFailure,
    serverErrorUnsupportedDevice    = 2,
    serverErrorInvalidRegCode       = 3,
    serverErrorMalformedRequest     = 4,    
    serverErrorLookupLimitReached   = 5,
    serverErrorInvalidRequest       = 6,
    serverErrorUnexpectedRequestArgument= 7,
    serverErrorRequestArgumentMissing   = 8,
    serverErrorInvalidProtocolVersion   = 9,
    serverErrorInvalidCookie    = 10,
    serverErrorUserDisabled     = 11,
    serverErrorForceUpgrade     = 12,
    serverErrorLangNotAvailable = 13,
    serverErrorLast=serverErrorLangNotAvailable // WATCH THIS WHEN ADDING NEW ERRORS!
};

struct LookupFinishedEventData
{
    enum Outcome
    {
        outcomeNothing,
        outcomeArticleBody,
        outcomeList,
        outcomeError,
        outcomeServerError,
        outcomeNotFound,
        outcomeRegCodeValid, // set if server sends Registration-Code-Valid with value "1"
        outcomeRegCodeInvalid, // set if server sends Registratoin-Code-Valid with value "0"
        outcomeDatabaseSwitched,
        outcomeAvailableLangs
    } outcome;
    
    union
    {
        status_t error;
        iPediaServerError  serverError;
    };        
    
    LookupFinishedEventData(Outcome o=outcomeNothing, status_t err=errNone):
        outcome(o),
        error(err)
    {}
    
};

class LookupManager: public LookupManagerBase<iPediaApplication::appLookupEventFirst, LookupFinishedEventData>
{
    LookupHistory& history_;

    Definition::Elements_t lastDefinitionElements_;

    String lastSearchTerm_;
    String lastFoundTerm_;
    String lastExtendedSearchTerm_;
    String lastExtendedSearchResults_;
    String lastReverseLinks_;
    
    String lastSearchLang_;
    String lastFoundLang_;

    enum HistoryChange
    {
        historyMoveBack,
        historyMoveForward,
        historyReplaceForward
    };
    
protected:

    void handleLookupFinished(const LookupFinishedEventData& data);

public:

    LookupManager(LookupHistory& history);

    ~LookupManager();

    const String& lastExtendedSearchResults() const
    {return lastExtendedSearchResults_;}
    
    Definition::Elements_t& lastDefinitionElements() 
    {return lastDefinitionElements_;}
    
    void search(const String& expression);

    void lookupTerm(const String& term, const String& lang = String());

    void lookupRandomTerm();

    bool lastSearchTermDifferent(const String& term, const String& lang = String());

    bool lookupIfDifferent(const String& term, const String& lang = String());

    void moveHistory(bool forward=false);
    
    bool hasPreviousHistoryTerm() const;
    
    bool hasNextHistoryTerm() const;    
    
    const String& lastExtendedSearchTerm() const
    {return lastExtendedSearchTerm_;}

    const String& lastSearchTerm() const
    {return lastSearchTerm_;}

    String& lastReverseLinks()
    {return lastReverseLinks_;}

    void handleLookupFinishedInForm(const LookupFinishedEventData& data);

    void verifyRegistrationCode(const String& regCode);

    void switchDatabase(const char_t* langCode);

    void getAvailableLangs();

    LookupHistory& getHistory()
    {
        return history_;
    }

private:
    
    void handleServerError(iPediaServerError serverError);
    
    void handleDefinitionMissing();
    
    void handleConnectionError(status_t error);
    
    void handleDefinition();
    
    void handleList();

    void setLastExtendedSearchResults(const String& sr)
    {lastExtendedSearchResults_ = sr;}
    
    void setLastSearchTerm(const String& term)
    {lastSearchTerm_ = term;}

    void setLastFoundTerm(const String& term)
    {lastFoundTerm_ = term;}

    void setLastExtendedSearchTerm(const String& term)
    {lastExtendedSearchTerm_ = term;}

    void setLastReverseLinks(const String& reverseLinks)
    {lastReverseLinks_ = reverseLinks;}

    friend class iPediaConnection;

    HistoryChange historyChange_;
    
};

#endif
