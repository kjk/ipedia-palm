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
    historyPosition_(termHistory_.end()),
    langPosition_(langHistory_.end())
{
}

LookupHistory::~LookupHistory()
{}

void LookupHistory::replaceAllNext(const String& term, const String& lang)
{
    if (historyPosition_!=termHistory_.end() && !termHistory_.empty())
    {
        termHistory_.erase(++historyPosition_, termHistory_.end());
        langHistory_.erase(++langPosition_, langHistory_.end());
    }
    termHistory_.push_back(term);
    langHistory_.push_back(lang);
    historyPosition_ = termHistory_.end();
    langPosition_ = langHistory_.end();
    --historyPosition_;
    --langPosition_;
    while (termHistory_.size() > maxLength)
    {
        termHistory_.pop_front();
        langHistory_.pop_front();
    }
}

void LookupHistory::moveNext(const String& term, const String& lang)
{
    if (hasNext()) 
    {
        *(++historyPosition_)=term;
        *(++langPosition_)=lang;
    }
}

void LookupHistory::movePrevious(const ArsLexis::String& term, const ArsLexis::String& lang)
{
    if (hasPrevious())
    {
        *(--historyPosition_)=term;
        *(--langPosition_)=lang;
    }
}

const String& LookupHistory::currentTerm() const
{
    assert(!termHistory_.empty());
    return *historyPosition_;
}

const String& LookupHistory::previousTerm() const
{
    assert(hasPrevious());
    StringList_t::const_iterator it = historyPosition_;
    return *(--it);
}

const String& LookupHistory::previousLang() const
{
    assert(hasPrevious());
    StringList_t::const_iterator it = langPosition_;
    return *(--it);
}

const String& LookupHistory::nextTerm() const
{
    assert(hasNext());
    StringList_t::const_iterator it = historyPosition_;
    return *(++it);
}

const String& LookupHistory::nextLang() const
{
    assert(hasNext());
    StringList_t::const_iterator it = langPosition_;
    return *(++it);
}

void LookupHistory::clearPast()
{
    termHistory_.erase(termHistory_.begin(), historyPosition_);
    langHistory_.erase(langHistory_.begin(), langPosition_);
}

const String& LookupHistory::currentLang() const
{
    assert(!langHistory_.empty());
    return *langPosition_;
}        


status_t LookupHistory::serializeOut(ArsLexis::PrefsStoreWriter& writer, int uniqueId) const
{
    status_t error;
    StringList_t::const_iterator end;
    StringList_t::const_iterator lit;
    StringList_t::const_iterator it;
    ushort_t currentItem = 0;

    ushort_t itemCount = termHistory_.size(); 
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, itemCount)))
        goto OnError;
    end = termHistory_.end();
    lit = langHistory_.begin();    
    for (it = termHistory_.begin(); it!=end; ++it, ++lit)
    {
        if (historyPosition_ != it)
            ++currentItem;
        if (errNone!=(error=writer.ErrSetStr(uniqueId++, (*it).c_str())))
            goto OnError;
        if (errNone!=(error=writer.ErrSetStr(uniqueId++, (*lit).c_str())))
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
    ushort_t i;

    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &itemCount)))
        goto OnError;
    if (maxLength<itemCount)
    {
        error=psErrDatabaseCorrupted;
        goto OnError;
    }
    for (i=0; i<itemCount; ++i)
    {
        const ArsLexis::char_t* p=0;
        if (errNone!=(error=reader.ErrGetStr(uniqueId++, &p)))
            goto OnError;
        tmp.termHistory_.push_back(p);
        if (errNone!=(error=reader.ErrGetStr(uniqueId++, &p)))
            goto OnError;
        tmp.langHistory_.push_back(p);
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
        tmp.historyPosition_ = tmp.termHistory_.begin();
        tmp.langPosition_ = tmp.langHistory_.begin();
        do 
        {
            ++tmp.historyPosition_;
            ++tmp.langPosition_;
        } while (--itemCount);
        tmp.termHistory_.erase(tmp.historyPosition_, tmp.termHistory_.end());           
        tmp.langHistory_.erase(tmp.langPosition_, tmp.langHistory_.end());
    }        
    std::swap(termHistory_, tmp.termHistory_);
    std::swap(langHistory_, tmp.langHistory_);
    historyPosition_ = termHistory_.end();
    langPosition_ = langHistory_.end();
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
    
