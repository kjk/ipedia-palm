#ifndef __IPEDIAFORM_HPP__
#define __IPEDIAFORM_HPP__

#include <RichForm.hpp>

class iPediaApplication;

class iPediaForm: public RichForm
{
public:

    enum RedrawCode
    {
        redrawAll=frmRedrawUpdateCode,
        redrawProgressIndicator,
        redrawFirstAvailable
    };
    
    iPediaForm(iPediaApplication& app, uint_t formId);

    ~iPediaForm();    
};

#endif
