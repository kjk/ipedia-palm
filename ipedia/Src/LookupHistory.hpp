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
    StringList_t::iterator historyPosition_;

public:

    enum {
        maxLength=25, 
        // Ugly.
        reservedPrefIdCount=maxLength+2
    };
    
    ArsLexis::status_t serializeOut(ArsLexis::PrefsStoreWriter& writer, int uniqueId) const;
    ArsLexis::status_t serializeIn(ArsLexis::PrefsStoreReader& reader, int uniqueId);

    LookupHistory();
    
    ~LookupHistory();
    
    bool hasPrevious() const
    {
        return historyPosition_!=termHistory_.begin();
    }
    
    bool hasNext() const;
    
    void replaceAllNext(const ArsLexis::String& term);
    
    void moveNext(const ArsLexis::String& term)
    {
        if (hasNext()) 
            *(++historyPosition_)=term;
    }
    
    void movePrevious(const ArsLexis::String& term)
    {
        if (hasPrevious())
            *(--historyPosition_)=term;
    }
    
    const ArsLexis::String& currentTerm() const
    {
        assert(!termHistory_.empty());
        return *historyPosition_;
    }
    
    const ArsLexis::String& previousTerm() const
    {
        assert(hasPrevious());
        StringList_t::const_iterator it=historyPosition_;
        return *(--it);
    }
    
    const ArsLexis::String& nextTerm() const
    {
        assert(hasNext());
        StringList_t::const_iterator it=historyPosition_;
        return *(++it);
    }
    
    void clearPast()
    {termHistory_.erase(termHistory_.begin(), historyPosition_);}
    
    bool hasCurrentTerm() const
    {
        return historyPosition_!=termHistory_.end();
    }

    StringList_t getHistory() const
    {
        return termHistory_;
    }
};

#endif