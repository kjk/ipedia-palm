#include "iPediaRenderingProgressReporter.hpp"
#include <Application.hpp>
#include <Form.hpp>

iPediaRenderingProgressReporter::iPediaRenderingProgressReporter(Form& form):
    form_(form),
    ticksAtStart_(0),
    lastPercent_(-1),
    showProgress_(false),
    afterTrigger_(false)
{
    waitText_.assign("Wait... %d%%");
    waitText_.c_str(); // We don't want reallocation to occur while rendering...
}
        
#define IPEDIA_USES_TEXT_RENDERING_PROGRESS 0

void iPediaRenderingProgressReporter::reportProgress(uint_t percent) 
{
    if (percent == lastPercent_)
        return;

    lastPercent_ = percent;
    if (0 == percent)
    {
        ticksAtStart_ = TimGetTicks();
        showProgress_ = false;
        afterTrigger_ = false;
        return;
    }
    
    if (!afterTrigger_)
    {
        // Delay before we start displaying progress meter in milliseconds. Timespans < 300ms are typically perceived "instant"
        // so we shouldn't distract user if the time is short enough.
        static const uint_t delay = 100; 
        UInt32 ticksDiff = TimGetTicks() - ticksAtStart_;
        Application& app = form_.application();
        ticksDiff *= 1000;
        ticksDiff /= app.ticksPerSecond();
        if (ticksDiff>=delay)
            afterTrigger_ = true;
        if (afterTrigger_ && percent<=20)
            showProgress_ = true;
    }
    
    if (!showProgress_)
        return;

    Graphics graphics(form_.windowHandle());
    ArsRectangle bounds = form_.bounds();
    bounds.explode(2, 17, -12, -37);

    ActivateGraphics act(graphics);
#if IPEDIA_USES_TEXT_RENDERING_PROGRESS
    Font f;
    Graphics::FontSetter fset(graphics, f);
    uint_t height = graphics.fontHeight();
    Rectangle rect(bounds.x(), bounds.y()+(bounds.height()-height)/2, bounds.width(), height);
    graphics.erase(rect);
    char buffer[100];
    StrPrintF(buffer, waitText_.c_str(), percent);
    graphics.drawCenteredText(buffer, rect.topLeft, rect.width());
#else
    uint_t height = 10;
    ArsRectangle rect(bounds.x()+16, bounds.y()+(bounds.height()-height)/2, bounds.width()-22, height);
    PatternType oldPattern = WinGetPatternType();
    WinSetPatternType(blackPattern);
    RectangleType nativeRec = toNative(rect);
    nativeRec.extent.x *= percent;
    nativeRec.extent.x /= 100;
    WinPaintRectangle(&nativeRec, 0);
    nativeRec.topLeft.x += nativeRec.extent.x;
    nativeRec.extent.x = rect.width()-nativeRec.extent.x;
    WinSetPatternType(grayPattern);
    WinPaintRectangle(&nativeRec, 0);
    WinSetPatternType(oldPattern);        
#endif    
}

