#ifndef __IPEDIA_APPLICATION_HPP__
#define __IPEDIA_APPLICATION_HPP__

#include "ipedia.h"
#include <RichApplication.hpp>
#include "RenderingPreferences.hpp"
#include "iPediaHyperlinkHandler.hpp"
#include <SysUtils.hpp>

class LookupManager;
class LookupHistory;

#define serverLocalhost        "127.0.0.1:9000"
//#define serverLocalhost    "192.168.0.1:9000"
#define serverOfficial   "ipedia.arslexis.com:9000"

#define defaultServer serverOfficial

class iPediaApplication: public ArsLexis::RichApplication 
{
    iPediaHyperlinkHandler  hyperlinkHandler_;
    LookupHistory*          history_;
    LookupManager*          lookupManager_;
    ArsLexis::String        server_;
    
    void detectViewer();
    
    void loadPreferences();

protected:

    Err normalLaunch();

    void waitForEvent(EventType& event);
    
    ArsLexis::Form* createForm(UInt16 formId);

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
    {return lookupManager_;}
    
    void savePreferences();
    
    struct Preferences
    {
        RenderingPreferences renderingPreferences;
        
        enum {cookieLength=32};
        ArsLexis::String cookie;
        
        enum {regCodeLength=32};
        ArsLexis::String regCode;
        
        long articleCount;
        
        ArsLexis::String databaseTime;

        Preferences():
            articleCount(-1)            
        {}
        
    };
    
    Preferences& preferences() 
    {return preferences_;}
    
    const Preferences& preferences() const
    {return preferences_;}
    
    const RenderingPreferences& renderingPreferences() const
    {return preferences().renderingPreferences;}
    
    static const uint_t reservedLookupEventsCount=3;
    
    enum Event
    {
        appLookupEventFirst=appFirstAvailableEvent,
        appLookupEventLast=appLookupEventFirst+reservedLookupEventsCount,
        appRegisterEvent,
        appRandomWord,
        appRegistrationFinished,
        appFirstAvailableEvent
    };
    
    void setServer(const ArsLexis::String& server)
    {server_=server;}
    
    const ArsLexis::String& server() const
    {return server_;}
    
    static iPediaApplication& instance()
    {return static_cast<iPediaApplication&>(Application::instance());}

    bool inStressMode() const
    {return stressMode_;}
    
    void toggleStressMode(bool enable)
    {
        toggleShowAlerts(!enable);
        stressMode_=enable;
    }
    
    const LookupHistory& history() const
    {
        assert(0!=history_);
        return *history_;
    }
    
    iPediaHyperlinkHandler& hyperlinkHandler()
    {return hyperlinkHandler_;}    

    // intentional lack of accessor functions, treat it like a property
    bool fArticleCountChecked;

private:
    
    Preferences preferences_;
    bool stressMode_:1;
    
};



#endif
