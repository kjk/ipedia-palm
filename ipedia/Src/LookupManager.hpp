#ifndef __LOOKUP_MANAGER_HPP__
#define __LOOKUP_MANAGER_HPP__

#include <LookupManagerBase.hpp>
#include "iPediaApplication.hpp"
#include "Definition.hpp"

class LookupHistory;

enum iPediaServerError
{
    serverErrorNone,
    serverErrorFailure,
    serverErrorFirst=serverErrorFailure,
    serverErrorUnsupportedDevice,
    serverErrorInvalidAuthorization,
    serverErrorMalformedRequest,
    serverErrorTrialExpired,
    serverErrorLast=serverErrorTrialExpired
};
        
struct LookupFinishedEventData
{
    enum Outcome
    {
        outcomeNothing,
        outcomeDefinition,
        outcomeList,
        outcomeError,
        outcomeServerError,
        outcomeNotFound
    } outcome;
    
    union
    {
        Err error;
        iPediaServerError serverError;
    };        
    
    LookupFinishedEventData(Outcome o=outcomeNothing, Err err=errNone):
        outcome(o),
        error(err)
    {}
    
};

class LookupManager: public ArsLexis::LookupManagerBase<iPediaApplication::appLookupEventFirst, LookupFinishedEventData>
{
    LookupHistory& history_;

    Definition::Elements_t lastDefinitionElements_;

    ArsLexis::String lastInputTerm_;
    ArsLexis::String lastFoundTerm_;
    ArsLexis::String lastSearchExpression_;
    ArsLexis::String lastSearchResults_;
    
    enum HistoryChange
    {
        historyMoveBack,
        historyMoveForward,
        historyReplaceForward
    };
    
protected:

    void handleLookupFinished(const LookupFinishedEventData& data);

public:

    LookupManager(LookupHistory& history):
        history_(history),
        historyChange_(historyMoveForward)
    {}
    
    ~LookupManager();

    const ArsLexis::String& lastSearchResults() const
    {return lastSearchResults_;}
    
    Definition::Elements_t& lastDefinitionElements() 
    {return lastDefinitionElements_;}
    
    void search(const ArsLexis::String& expression);

    void lookupTerm(const ArsLexis::String& term);

    void lookupRandomTerm();

    //! @return @c true if lookup is started, @c false otherwise.
    bool lookupIfDifferent(const ArsLexis::String& term);

    void moveHistory(bool forward=false);

    const ArsLexis::String& lastSearchExpression() const
    {return lastSearchExpression_;}

    const ArsLexis::String& lastInputTerm() const
    {return lastInputTerm_;}
    
    void handleLookupFinishedInForm(const LookupFinishedEventData& data);
    
    void checkArticleCount();
    
private:
    
    void handleServerError(iPediaServerError serverError);
    
    void handleDefinitionMissing();
    
    void handleConnectionError(Err error);
    
    void handleDefinition();
    
    void handleList();
    
    void setLastSearchResults(const ArsLexis::String& sr)
    {lastSearchResults_=sr;}
    
    void setLastInputTerm(const ArsLexis::String& lit)
    {lastInputTerm_=lit;}
    
    void setLastFoundTerm(const ArsLexis::String& t)
    {lastFoundTerm_=t;}
    
    void setLastSearchExpression(const ArsLexis::String& se)
    {lastSearchExpression_=se;}
    
    friend class iPediaConnection;

    HistoryChange historyChange_;
    
};

#endif