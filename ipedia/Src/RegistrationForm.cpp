#include "RegistrationForm.hpp"
#include <FormObject.hpp>
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"

using ArsLexis::Rectangle;
using ArsLexis::FormObject;
using ArsLexis::Field;
using ArsLexis::Control;
using ArsLexis::String;

void RegistrationForm::resize(const ArsLexis::Rectangle& screenBounds)
{
    Rectangle rect(2, screenBounds.height()-70, screenBounds.width()-4, 68);
    setBounds(rect);
    
    FormObject object(*this, serialNumberField);
    object.bounds(rect);
    rect.width()=screenBounds.width()-14;
    object.setBounds(rect);
    
    update();
}

bool RegistrationForm::handleOpen()
{
    bool handled=iPediaForm::handleOpen();
    Field field(*this, serialNumberField);

    iPediaApplication::Preferences& prefs=static_cast<iPediaApplication&>(application()).preferences();
    MemHandle handle=MemHandleNew(prefs.serialNumberLength+1);
    if (!handle)
        return handled;

    char* text=static_cast<char*>(MemHandleLock(handle));
    if (text)
    {
        assert(prefs.serialNumber.length()<=prefs.serialNumberLength);
        StrNCopy(text, prefs.serialNumber.data(), prefs.serialNumber.length());
        text[prefs.serialNumber.length()]=chrNull;
        MemHandleUnlock(handle);
    }
    field.setText(handle);        
    
    field.focus();
    return handled;
}

void RegistrationForm::handleControlSelect(const EventType& event)
{
    if (okButton!=event.data.ctlSelect.controlID)
    {
        closePopup();
        return;
    }

    iPediaApplication& app=static_cast<iPediaApplication&>(application());

    // verify that reg code is correct with Verify-Registration-Code request
    Field field(*this, serialNumberField);
    const char* text=field.text();
    if ( (NULL==text) || ('\0'==*text))
    {
        // TODO: don't even bother asking the server, it must be wrong
        text="";
    }

    LookupManager* lookupManager=app.getLookupManager();
    if (NULL==lookupManager)
    {
        // TODO: is this really good? Should it ever happen?
        return;
    }

    // TODO: remove non-digits from reg code
    String regCode(text);
    lookupManager->verifyRegistrationCode(regCode);
}

static bool isDigit(char c)
{
    if (c>='0' && c<='9')
        return true;
    return false;
}

// remove in-place all non-digits from buf. buf must be null-terminated.
static void RemoveNonDigits(char *buf)
{
    char *tmp = buf;
    while (*buf)
    {
        if (isDigit(*buf))
            *tmp++ = *buf;
        buf++;
    }
    *tmp = '\0';
}


void RegistrationForm::handleLookupFinished(const EventType& event)
{
    // setControlsState(true);
    const LookupFinishedEventData& data=reinterpret_cast<const LookupFinishedEventData&>(event.data);
    if (data.outcomeRegCodeValid==data.outcome)
    {
        iPediaApplication::Preferences& prefs=static_cast<iPediaApplication&>(application()).preferences();
        // TODO: probably need to store the reg number somewhere instead of
        // re-getting it from the server
        Field field(*this, serialNumberField);
        const char* text=field.text();
        assert( (NULL!=text) && ('\0'!=*text));
        // TODO: assert that consists of digits only
        String newSn(text);
        if (newSn!=prefs.serialNumber)
        {
            assert(newSn.length()<=prefs.serialNumberLength);
            prefs.serialNumber=newSn;
            // TODO: get rid of serialNumberRegistered
            prefs.serialNumberRegistered=false;
        }
        closePopup();
    }
    else if (data.outcomeRegCodeInvalid==data.outcome)
    {
        // TODO: should it be done as a message to ourselves?
        UInt16 buttonId;
        
        buttonId = FrmAlert(alertRegistrationFailed);
        
        if (0==buttonId)
        {
            // this is "Ok" button. Clear-out registration code (since it was invalid)
            // TODO:
            //MemSet(appContext->prefs.regCode, sizeof(appContext->prefs.regCode), 0);
            //SavePreferencesInoah(appContext);
            return;
        }
        assert(1==buttonId);
        // this must be "Re-enter registration code" button
        // TODO: show the dialog box again
    }
    else
    {
        // TODO: not sure what to do. this must mean an error
        update();
    }

    LookupManager* lookupManager=static_cast<iPediaApplication&>(application()).getLookupManager();
    assert(lookupManager);
    lookupManager->handleLookupFinishedInForm(data);
}

bool RegistrationForm::handleEvent(EventType& event)
{
    bool handled=false;
    switch (event.eType)
    {
        case ctlSelectEvent:
            handleControlSelect(event);
            handled=true;
            break;
            
        case keyDownEvent:
            if (chrCarriageReturn==event.data.keyDown.chr || chrLineFeed==event.data.keyDown.chr)
            {
                Control control(*this, okButton);
                control.hit();
            }
            break;

        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled=true;
            break;
            
        case LookupManager::lookupStartedEvent:
            //setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            break;
    
        default:
            handled=iPediaForm::handleEvent(event);
    }
    return handled;
}
