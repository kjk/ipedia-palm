#ifndef __LOOKUP_HISTORY_HPP__
#define __LOOKUP_HISTORY_HPP__

#include <Debug.hpp>
#include <BaseTypes.hpp>
#include <Text.hpp>
#include <list>

namespace ArsLexis
{
    class PrefsStoreReader;
    class PrefsStoreWriter;
}    

class LookupHistory
{
    // Not quite effective. But using std::deque for this purpose would increase code size significantly.
    StringList_t termHistory_;
    StringList_t langHistory_;
    StringList_t::iterator historyPosition_;
    StringList_t::iterator langPosition_;

public:

    enum {
        maxLength=25, 
        // Ugly.
        reservedPrefIdCount=maxLength*2+2
    };
    
    ArsLexis::status_t serializeOut(ArsLexis::PrefsStoreWriter& writer, int uniqueId) const;
    ArsLexis::status_t serializeIn(ArsLexis::PrefsStoreReader& reader, int uniqueId);

    LookupHistory();
    
    ~LookupHistory();
    
    bool hasPrevious() const {return historyPosition_!=termHistory_.begin();}
    
    bool hasNext() const;
    
    void replaceAllNext(const ArsLexis::String& term, const ArsLexis::String& lang);
    
    void moveNext(const ArsLexis::String& term, const ArsLexis::String& lang);
    
    void movePrevious(const ArsLexis::String& term, const ArsLexis::String& lang);
    
    const ArsLexis::String& currentTerm() const;
    
    const ArsLexis::String& currentLang() const;
    
    const ArsLexis::String& previousTerm() const;
    
    const ArsLexis::String& previousLang() const;
    
    const ArsLexis::String& nextTerm() const;

    const ArsLexis::String& nextLang() const;
    
    void clearPast();
    
    bool hasCurrentTerm() const {return historyPosition_!=termHistory_.end();}

    const StringList_t& getHistory() const {return termHistory_;}
    
};

#endif