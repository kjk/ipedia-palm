#ifndef __REGISTRATION_FORM_HPP__
#define __REGISTRATION_FORM_HPP__

#include "iPediaForm.hpp"
#include "iPediaApplication.hpp"

class RegistrationForm: public iPediaForm
{
    void handleControlSelect(const EventType& data);

    void handleLookupFinished(const EventType& event);

    ArsLexis::String newRegCode_;

protected:

    void resize(const ArsLexis::Rectangle& screenBounds);

    bool handleEvent(EventType& event);

    bool handleOpen();

public:

    RegistrationForm(iPediaApplication& app):
        iPediaForm(app, registrationForm)
    {}    

};

#endif