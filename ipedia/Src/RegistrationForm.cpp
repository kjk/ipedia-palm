#include "RegistrationForm.hpp"
#include <FormObject.hpp>
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"
#include "Text.hpp"

void RegistrationForm::resize(const Rectangle& screenBounds)
{
    Rectangle rect(2, screenBounds.height()-70, screenBounds.width()-4, 68);
    setBounds(rect);
    
    FormObject object(*this, regCodeFormField);
    object.bounds(rect);
    rect.width()=screenBounds.width()-14;
    object.setBounds(rect);
    
    update();
}

bool RegistrationForm::handleOpen()
{
    bool handled=iPediaForm::handleOpen();
    Field field(*this, regCodeFormField);

    iPediaApplication::Preferences& prefs=static_cast<iPediaApplication&>(application()).preferences();
    MemHandle handle=MemHandleNew(prefs.regCodeLength+1);
    if (!handle)
        return handled;

    char* text=static_cast<char*>(MemHandleLock(handle));
    if (text)
    {
        assert(prefs.regCode.length()<=prefs.regCodeLength);
        StrNCopy(text, prefs.regCode.data(), prefs.regCode.length());
        text[prefs.regCode.length()]=chrNull;
        MemHandleUnlock(handle);
    }
    field.setText(handle);        
    
    field.focus();
    return handled;
}

void RegistrationForm::handleControlSelect(const EventType& event)
{
    if (registerButton!=event.data.ctlSelect.controlID)
    {
        assert(laterButton==event.data.ctlSelect.controlID);
        closePopup();
        return;
    }

    iPediaApplication& app=static_cast<iPediaApplication&>(application());

    // verify that reg code is correct using Verify-Registration-Code request
    Field field(*this, regCodeFormField);
    const char* text=field.text();
    if ( (NULL==text) || ('\0'==*text))
    {
        // don't even bother asking the server, it must be wrong
        return;
    }

    // get lookup manager, create if doesn't exist. We might not have lookupManager
    // at this point (if we didn't do any query before registration query)
    LookupManager* lookupManager=app.getLookupManager(true);
    assert(lookupManager);
    if (NULL==lookupManager)
    {
        // shouldn't happen, but just in case
        return;
    }

    removeNonDigits(text,newRegCode_);
    lookupManager->verifyRegistrationCode(newRegCode_);
}

void RegistrationForm::handleLookupFinished(const EventType& event)
{
    // setControlsState(true);
    iPediaApplication& app = iPediaApplication::instance();
    iPediaApplication::Preferences& prefs=app.preferences();

    const LookupFinishedEventData& data=reinterpret_cast<const LookupFinishedEventData&>(event.data);
    if (data.outcomeRegCodeValid==data.outcome)
    {
        assert(!newRegCode_.empty());
        // TODO: assert that it consists of numbers only
        if (newRegCode_ != prefs.regCode)
        {
            assert(newRegCode_.length()<=prefs.regCodeLength);
            prefs.regCode = newRegCode_;
            app.savePreferences();
        }

        FrmAlert(alertRegistrationOk);
        sendEvent(iPediaApplication::appRegistrationFinished);
        closePopup();
    }
    else if (data.outcomeRegCodeInvalid==data.outcome)
    {
        UInt16 buttonId = FrmAlert(alertRegistrationFailed);
        
        if (0==buttonId)
        {
            // this is "Ok" button. Clear-out registration code (since it was invalid)
            prefs.regCode = "";
            app.savePreferences();
            closePopup();
            return;
        }
        // this must be "Re-enter registration code" button
        assert(1==buttonId);
        Field field(*this, regCodeFormField);
        field.focus();
    }
    else
    {
        assert((data.outcomeServerError==data.outcome) || (data.outcomeError==data.outcome));
        // an alert will be shown for server errors
        update();
        LookupManager* lookupManager=app.getLookupManager();
        assert(lookupManager);
        lookupManager->handleLookupFinishedInForm(data);
    }
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
                Control control(*this, registerButton);
                control.hit();
            }
            break;

        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled=true;
            break;
            
        case LookupManager::lookupStartedEvent:
            //TODO: disable controls during lookup
            //setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            break;
    
        default:
            handled=iPediaForm::handleEvent(event);
    }
    return handled;
}
