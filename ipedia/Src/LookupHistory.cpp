#include "LookupHistory.hpp"
// TODO: hack, this needs to be done in ars_framework's PrefsStore.hpp
#ifdef _PALM_OS
#include <PrefsStore.hpp>
#else
#include <WinPrefsStore.hpp>
#endif

#include <BaseTypes.hpp>

#ifdef __MWERKS__
# pragma far_code
#endif

using ArsLexis::String;
using ArsLexis::status_t;

LookupHistory::LookupHistory():
    historyPosition_(termHistory_.end())
{
}

LookupHistory::~LookupHistory()
{}

void LookupHistory::replaceAllNext(const ArsLexis::String& term)
{
    if (historyPosition_!=termHistory_.end() && !termHistory_.empty())
        termHistory_.erase(++historyPosition_, termHistory_.end());
    termHistory_.push_back(term);
    historyPosition_=termHistory_.end();
    --historyPosition_;
    while (termHistory_.size()>maxLength)
        termHistory_.pop_front();
}

status_t LookupHistory::serializeOut(ArsLexis::PrefsStoreWriter& writer, int uniqueId) const
{
    status_t error;

    ushort_t itemCount=termHistory_.size(); 
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, itemCount)))
        goto OnError;
    ushort_t currentItem=0;
    StringList_t::const_iterator end(termHistory_.end());
    
    for (StringList_t::const_iterator it(termHistory_.begin()); it!=end; ++it)
    {
        if (historyPosition_!=it)
            ++currentItem;
        if (errNone!=(error=writer.ErrSetStr(uniqueId++, (*it).c_str())))
            goto OnError;
    }
    if (itemCount>=0 && currentItem==itemCount)
        currentItem--;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, currentItem)))
        goto OnError;
OnError:    
    return error;
}

status_t LookupHistory::serializeIn(ArsLexis::PrefsStoreReader& reader, int uniqueId)
{
    status_t error;
    LookupHistory tmp;
    ushort_t itemCount;
    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &itemCount)))
        goto OnError;
    if (maxLength<itemCount)
    {
        error=psErrDatabaseCorrupted;
        goto OnError;
    }
    for (ushort_t i=0; i<itemCount; ++i)
    {
        const ArsLexis::char_t* p=0;
        if (errNone!=(error=reader.ErrGetStr(uniqueId++, &p)))
            goto OnError;
        tmp.termHistory_.push_back(p);
    }
    ushort_t lastItem;
    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &lastItem)))
        goto OnError;
    if (itemCount>0 && lastItem>=itemCount)
    {
        error=psErrDatabaseCorrupted;
        goto OnError;
    }
    if (0!=itemCount)
    {
        tmp.historyPosition_=tmp.termHistory_.begin();
        do 
        {
            ++tmp.historyPosition_;
        } while (--itemCount);
        tmp.termHistory_.erase(tmp.historyPosition_, tmp.termHistory_.end());           
    }        
    std::swap(termHistory_, tmp.termHistory_);
    historyPosition_=termHistory_.end();
OnError:    
    return error;
}

bool LookupHistory::hasNext() const
{
    StringList_t::const_iterator last=termHistory_.end();
    if (historyPosition_==last)
        return false;
    if (!termHistory_.empty())
        --last;
    return historyPosition_!=last;
}
    
