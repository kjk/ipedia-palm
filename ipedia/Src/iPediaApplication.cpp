
#include "iPediaApplication.hpp"
#include "SysUtils.hpp"
#include "MainForm.hpp"
#include "NetLibrary.hpp"
#include "RegistrationForm.hpp"

IMPLEMENT_APPLICATION_INSTANCE(appFileCreator)

using namespace ArsLexis;

iPediaApplication::iPediaApplication():
    diaNotifyRegistered_(false),
    netLib_(0),
    connectionManager_(0),
    ticksPerSecond_(SysTicksPerSecond()),
    resolver_(0)
{
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
    Err error=Application::initialize();
    if (!error)
    {
        if (diaSupport_.available() && isNotifyManager()) 
        {
            error=registerNotify(diaSupport_.notifyType());
            if (!error)
                diaNotifyRegistered_=true;
        }
    }
    
    detectViewer();
       
    return error;
}

iPediaApplication::~iPediaApplication()
{
    if (diaNotifyRegistered_) 
        unregisterNotify(diaSupport_.notifyType());
    
    // Hard to believe, but seems that destructors are in some way accessed even if objects==0. 
    // This causes bus error in non-normal launch (SocketConnectionManager is in 2nd segment).
    // That's why I have to use these ifs below...
    if (connectionManager_)
        delete connectionManager_;
    if (netLib_)        
        delete netLib_;
    if (resolver_)
        delete resolver_;

}


static const UInt32 iPediaRequiredRomVersion=sysMakeROMVersion(3,5,0,sysROMStageDevelopment,0);

Err iPediaApplication::normalLaunch()
{
    gotoForm(mainForm);
    runEventLoop();
    return errNone;
}

Err iPediaApplication::handleSystemNotify(SysNotifyParamType& notify)
{
    const ArsLexis::DIA_Support& dia=getDIASupport();
    if (dia.available() && dia.notifyType()==notify.notifyType)
        dia.handleNotify();
    return errNone;
}

Err iPediaApplication::handleLaunchCode(UInt16 cmd, MemPtr cmdPBP, UInt16 launchFlags)
{
    Err error=checkRomVersion(iPediaRequiredRomVersion, launchFlags, romIncompatibleAlert);
    if (!error)
        error=Application::handleLaunchCode(cmd, cmdPBP, launchFlags);
    return error;
}

Err iPediaApplication::getNetLibrary(NetLibrary*& netLib)
{
    Err error=errNone;
    if (!netLib_)
    {
        std::auto_ptr<NetLibrary> tmp(new NetLibrary);
        UInt16 ifError=0;
        error=tmp->initialize(ifError);
        if (errNone==error && 0==ifError)
        {
            netLib_=tmp.release();
            connectionManager_=new SocketConnectionManager(*netLib_);
            resolver_=new Resolver(*netLib_);
        }
        else {
            if (errNone==error)
                error=netErrDeviceInitFail;
        }
    }
    if (!error)
        netLib=netLib_;
    else
        FrmAlert(networkUnavailableAlert);        
    return error;
}

void iPediaApplication::waitForEvent(EventType& event)
{
    if (connectionManager_ && connectionManager_->active())
    {
        setEventTimeout(0);
        Application::waitForEvent(event);
        if (nilEvent==event.eType)
            connectionManager_->manageConnectionEvents(ticksPerSecond_/20);
    }
    else
    {
        setEventTimeout(evtWaitForever);
        Application::waitForEvent(event);
    }        
}

Form* iPediaApplication::createForm(UInt16 formId)
{
    Form* form=0;
    switch (formId)
    {
        case mainForm:
            form=new MainForm(*this);
            break;
            
        case registrationForm:
            form=new RegistrationForm(*this);
            break;
        
        default:
            assert(false);
    }
    return form;            
}

Err iPediaApplication::getConnectionManager(SocketConnectionManager*& manager)
{
    NetLibrary* netLib=0;
    Err error=getNetLibrary(netLib);
    if (!error)
        assert(connectionManager_!=0);
    manager=connectionManager_;
    return error;
}

Err iPediaApplication::getResolver(Resolver*& resolver)
{
    NetLibrary* netLib=0;
    Err error=getNetLibrary(netLib);
    if (!error)
        assert(resolver_!=0);
    resolver=resolver_;
    return error;
}

void iPediaApplication::sendDisplayAlertEvent(UInt16 alertId)
{
    EventType event;
    MemSet(&event, sizeof(event), 0);    event.eType=static_cast<eventsEnum>(appDisplayAlertEvent);
    DisplayAlertEventData& data=reinterpret_cast<DisplayAlertEventData&>(event.data);
    data.alertId=alertId;
    EvtAddEventToQueue(&event);
}

bool iPediaApplication::handleApplicationEvent(EventType& event)
{
    bool handled=false;
    if (appDisplayAlertEvent==event.eType)
    {
        DisplayAlertEventData& data=reinterpret_cast<DisplayAlertEventData&>(event.data);
        FrmAlert(data.alertId);
    }
    else
        handled=Application::handleApplicationEvent(event);
    return handled;
}
