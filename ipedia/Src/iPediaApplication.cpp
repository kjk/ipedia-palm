
#include "iPediaApplication.hpp"
#include <SysUtils.hpp>
#include <DeviceInfo.hpp>
#include "MainForm.hpp"
#include "RegistrationForm.hpp"
#include "SearchResultsForm.hpp"
#include "StringListForm.hpp"
#include "LookupManager.hpp"
#include "LookupHistory.hpp"

#include <PrefsStore.hpp>

#define SERVER_DICT_PC       "dict-pc.arslexis.com:9000"
#define SERVER_LOCALHOST_2   "192.168.0.1:9000"

#define SERVER_TO_USE SERVER_LOCALHOST
//#define SERVER_TO_USE SERVER_OFFICIAL

IMPLEMENT_APPLICATION_CREATOR(appFileCreator)

using namespace ArsLexis;

iPediaApplication::iPediaApplication():
    history_(0),
    lookupManager_(0),
    server_(SERVER_TO_USE),
    stressMode_(false),
    fArticleCountChecked(false)
{
#ifdef INTERNAL_BUILD
# ifndef NDEBUG    
    log().addSink(new MemoLogSink(), Logger::logDebug);
    log().addSink(new HostFileLogSink("\\var\\log\\iPedia.log"), Logger::logEverything);
    log().addSink(new DebuggerLogSink(), Logger::logWarning);
# else
    log().addSink(new MemoLogSink(), Logger::logError);
# endif
#endif
}

inline void iPediaApplication::detectViewer()
{
    UInt16  cardNo;
    LocalID dbID;

    if (fDetectViewer(&cardNo,&dbID))
    {
        assert(dbID!=0);
        hyperlinkHandler_.setViewerLocation(cardNo, dbID);
    }
}

Err iPediaApplication::initialize()
{
    Err error=RichApplication::initialize();
    detectViewer();
    return error;
}

iPediaApplication::~iPediaApplication()
{
    if (lookupManager_)
        delete lookupManager_;

    if (history_)
        delete history_;
    server_.clear();
}


Err iPediaApplication::normalLaunch()
{
    history_=new LookupHistory();
    loadPreferences();
#ifdef INTERNAL_BUILD
    // make it easier for me to run the app
    // if running on Treo 600 set the default server to my server
    if (isTreo600())
    {
        server_ = SERVER_OFFICIAL;
    }
#endif
    gotoForm(mainForm);
    runEventLoop();
    savePreferences();
    return errNone;
}

bool iPediaApplication::fLookupInProgress() const
{
    if (NULL==lookupManager_)
        return false;
    return lookupManager_->lookupInProgress();
}

LookupManager* iPediaApplication::getLookupManager(bool create)
{
    if (!lookupManager_ && create)
    {
        assert(0!=history_);
        lookupManager_=new LookupManager(*history_);
    }
    return lookupManager_;
}

void iPediaApplication::waitForEvent(EventType& event)
{
    ArsLexis::SocketConnectionManager* manager=0;
    if (lookupManager_)
        manager=&lookupManager_->connectionManager();
    if (manager && manager->active())
    {
        setEventTimeout(0);
        RichApplication::waitForEvent(event);
        if (nilEvent==event.eType)
            manager->manageConnectionEvents(ticksPerSecond()/20);
    }
    else
    {
        setEventTimeout(evtWaitForever);
        RichApplication::waitForEvent(event);
    }        
}

Form* iPediaApplication::createForm(UInt16 formId)
{
    Form* form=0;
    switch (formId)
    {
        case mainForm:
            form = new MainForm(*this);
            break;
            
        case registrationForm:
            form = new RegistrationForm(*this);
            break;
            
        case searchResultsForm:
            form = new SearchResultsForm(*this);
            break;

        case stringListForm:
            form = new StringListForm(*this);
            break;

        default:
            assert(false);
    }
    return form;            
}

bool iPediaApplication::handleApplicationEvent(EventType& event)
{
    bool handled=false;
    if (lookupManager_ && appLookupEventFirst<=event.eType && appLookupEventLast>=event.eType)
        lookupManager_->handleLookupEvent(event);
    else
        handled=RichApplication::handleApplicationEvent(event);
    return handled;
}

namespace {

    enum PreferenceId 
    {
        cookiePrefId,
        regCodePrefId,
        serialNumberRegFlagPrefId, // unused
        lastArticleCountPrefId,
        databaseTimePrefId,
        lookupHistoryFirstPrefId,
        renderingPrefsFirstPrefId=lookupHistoryFirstPrefId+LookupHistory::reservedPrefIdCount,
        
        availableLangsPrefId = renderingPrefsFirstPrefId+RenderingPreferences::reservedPrefIdCount,
        currentLangPrefId,
        next = currentLangPrefId+1
    };

    // These globals will be removed by dead code elimination.
    ArsLexis::StaticAssert<(sizeof(uint_t) == sizeof(UInt16))> uint_t_the_same_size_as_UInt16;
    ArsLexis::StaticAssert<(sizeof(bool) == sizeof(Boolean))> bool_the_same_size_as_Boolean;
    
}

void iPediaApplication::loadPreferences()
{
    Preferences prefs;
    // PrefsStoreXXXX seem to be rather heavyweight objects (writer is >480kB), so it might be a good idea not to allocate them on stack.
    std::auto_ptr<PrefsStoreReader> reader(new PrefsStoreReader(appPrefDatabase, appFileCreator, sysFileTPreferences));

    Err         error;
    const char* text;

    if (errNone!=(error=reader->ErrGetStr(cookiePrefId, &text))) 
        goto OnError;
    prefs.cookie = text;
    if (errNone!=(error=reader->ErrGetStr(regCodePrefId, &text))) 
        goto OnError;
    prefs.regCode = text;
    if (errNone!=(error=reader->ErrGetLong(lastArticleCountPrefId, &prefs.articleCount))) 
        goto OnError;
    if (errNone!=(error=reader->ErrGetStr(databaseTimePrefId, &text))) 
        goto OnError;
    prefs.databaseTime = text;
    if (errNone!=(error=prefs.renderingPreferences.serializeIn(*reader, renderingPrefsFirstPrefId)))
        goto OnError;
    preferences_=prefs;    
    assert(0!=history_);
    if (errNone!=(error=history_->serializeIn(*reader, lookupHistoryFirstPrefId)))
        goto OnError;

    if (errNone!=(error=reader->ErrGetStr(currentLangPrefId, &text))) 
        goto OnError;
    prefs.currentLang = text;

    if (errNone!=(error=reader->ErrGetStr(availableLangsPrefId, &text))) 
        goto OnError;
    prefs.availableLangs = text;

OnError:
    return;        
}

void iPediaApplication::savePreferences()
{
    Err   error;
    std::auto_ptr<PrefsStoreWriter> writer(new PrefsStoreWriter(appPrefDatabase, appFileCreator, sysFileTPreferences));

    if (errNone!=(error=writer->ErrSetStr(cookiePrefId, preferences_.cookie.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(regCodePrefId, preferences_.regCode.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetLong(lastArticleCountPrefId, preferences_.articleCount))) 
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(databaseTimePrefId, preferences_.databaseTime.c_str())))
        goto OnError;
    if (errNone!=(error=preferences_.renderingPreferences.serializeOut(*writer, renderingPrefsFirstPrefId)))
        goto OnError;
    assert(0!=history_);
    if (errNone!=(error=history_->serializeOut(*writer, lookupHistoryFirstPrefId)))
        goto OnError;

    if (errNone!=(error=writer->ErrSetStr(currentLangPrefId, preferences_.currentLang.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(availableLangsPrefId, preferences_.availableLangs.c_str())))
        goto OnError;

    if (errNone!=(error=writer->ErrSavePreferences()))
        goto OnError;
    return;        
OnError:
    //! @todo Diplay alert that saving failed?
    return;
}
