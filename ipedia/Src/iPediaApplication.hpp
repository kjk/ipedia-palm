#ifndef __IPEDIA_APPLICATION_HPP__
#define __IPEDIA_APPLICATION_HPP__

#include "ipedia.h"
#include <RichApplication.hpp>
#include <StringListForm.hpp>
#include <SysUtils.hpp>
#include "iPediaHyperlinkHandler.hpp"

class LookupManager;
class LookupHistory;

// rest of the servers is defined in iPediaApplication.cpp
#define SERVER_LOCALHOST     "127.0.0.1:9000"
#define SERVER_OFFICIAL      "ipedia.arslexis.com:9000"

class iPediaApplication: public RichApplication 
{
    iPediaHyperlinkHandler*  hyperlinkHandler_;
    LookupHistory*          history_;
    LookupManager*          lookupManager_;
    
    void detectViewer();
    
    void loadPreferences();

protected:

    Err normalLaunch();

    void waitForEvent(EventType& event);
    
    Form* createForm(UInt16 formId);

    bool handleApplicationEvent(EventType& event);
    
public:

    static const UInt32 requiredRomVersion=sysMakeROMVersion(4,0,0,sysROMStageDevelopment,0);
    static const UInt32 creatorId=appFileCreator;
    static const UInt16 notEnoughMemoryAlertId=notEnoughMemoryAlert;
    static const UInt16 romIncompatibleAlertId=romIncompatibleAlert;
    
    iPediaApplication();
    
    ~iPediaApplication();
    
    Err initialize();

    LookupManager* getLookupManager(bool create=false);
    const LookupManager* getLookupManager() const
    {
        return lookupManager_;
    }

    bool fLookupInProgress() const;

    void savePreferences();

    struct Preferences
    {
        // RenderingPreferences renderingPreferences;

        enum {cookieLength=32};
        ArsLexis::String cookie;

        enum {regCodeLength=32};
        ArsLexis::String regCode;

        long articleCount;

        ArsLexis::String databaseTime;

        ArsLexis::String availableLangs;

        ArsLexis::String currentLang;

        Preferences():
            articleCount(-1)            
        {}

    };

    Preferences& preferences() 
    {
        return preferences_;
    }

    const Preferences& preferences() const
    {
        return preferences_;
    }

#if 0
    const RenderingPreferences& renderingPreferences() const
    {
        return preferences().renderingPreferences;
    }
#endif
    static const uint_t reservedLookupEventsCount=3;

    enum Event
    {
        appLookupEventFirst=appFirstAvailableEvent,
        appLookupEventLast=appLookupEventFirst+reservedLookupEventsCount,
        appRegisterEvent,
        appRandomWord,
        appRegistrationFinished,
        appForceUpgrade,
        appDbnameStringSelected,
        appHistoryStringSelected,
        appLinkedArticlesStringSelected,
        appLinkingArticlesStringSelected,
        appLangNotAvailable,
        appFirstAvailableEvent
    };

    static iPediaApplication& instance()
    {
        return static_cast<iPediaApplication&>(Application::instance());
    }

    bool inStressMode() const
    {
        return stressMode_;
    }

    void toggleStressMode(bool enable)
    {
        toggleShowAlerts(!enable);
        stressMode_ = enable;
    }
    
    const LookupHistory& history() const
    {
        assert(0!=history_);
        return *history_;
    }
    
    iPediaHyperlinkHandler& hyperlinkHandler()
    {
        return *hyperlinkHandler_;
    }

    // intentional lack of accessor functions, treat it like a property
    bool        fArticleCountChecked;

    int         strListSize;
    char_t**    strList;

    char_t *     serverAddress;

private:
    Preferences preferences_;
    bool        stressMode_:1;
};



#endif
