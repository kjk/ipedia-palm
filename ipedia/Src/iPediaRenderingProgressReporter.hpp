#ifndef IPEDIA_RENDERING_PROGRESS_REPORTER_HPP__
#define IPEDIA_RENDERING_PROGRESS_REPORTER_HPP__

#include <Definition.hpp>

namespace ArsLexis {class Form;}

class iPediaRenderingProgressReporter: public Definition::RenderingProgressReporter
{
    ArsLexis::Form& form_;
    UInt32 ticksAtStart_;
    uint_t lastPercent_;
    bool showProgress_:1;
    bool afterTrigger_:1;
    ArsLexis::String waitText_;
    
public:
    
    iPediaRenderingProgressReporter(ArsLexis::Form& form);
    
    void reportProgress(uint_t percent);

};
    



#endif // IPEDIA_RENDERING_PROGRESS_REPORTER_HPP__