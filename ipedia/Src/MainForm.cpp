#include "MainForm.hpp"
#include <FormObject.hpp>
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"
#include "LookupHistory.hpp"
#include <SysUtils.hpp>

#include <FormattedTextElement.hpp>
#include <LineBreakElement.hpp>
#include <ParagraphElement.hpp>


using namespace ArsLexis;

MainForm::MainForm(iPediaApplication& app):
    iPediaForm(app, mainForm),
    renderingProgressReporter_(*this),
    displayMode_(showSplashScreen),
    lastPenDownTimestamp_(0),
    updateDefinitionOnEntry_(false),
    enableInputFieldAfterUpdate_(false),
    forceSplashRecalculation_(false),
    articleCountElement_(0),
    articleCountSet_(-1)
{
    articleCountSet_ = app.preferences().articleCount;
    article_.setRenderingProgressReporter(&renderingProgressReporter_);
    article_.setHyperlinkHandler(&app.hyperlinkHandler());
    about_.setHyperlinkHandler(&app.hyperlinkHandler());
    prepareSplashScreen();
}

bool MainForm::handleOpen()
{
    bool result=iPediaForm::handleOpen();
    updateNavigationButtons();
    return result;
}

inline const LookupHistory& MainForm::getHistory() const
{
    return static_cast<const iPediaApplication&>(application()).history();
}

void MainForm::resize(const ArsLexis::Rectangle& screenBounds)
{
    Rectangle bounds(this->bounds());
    if (screenBounds!=bounds)
    {
        setBounds(screenBounds);

        FormObject object(*this, definitionScrollBar);
        object.bounds(bounds);
        bounds.x()=screenBounds.extent.x-8;
        bounds.height()=screenBounds.extent.y-36;
        object.setBounds(bounds);
        
        object.attach(termInputField);
        object.bounds(bounds);
        bounds.y()=screenBounds.extent.y-14;
        bounds.width()=screenBounds.extent.x-63;
        object.setBounds(bounds);

        object.attach(searchButton);
        object.bounds(bounds);
        bounds.x()=screenBounds.extent.x-34;
        bounds.y()=screenBounds.extent.y-14;
        object.setBounds(bounds);
        
        object.attach(backButton);
        object.bounds(bounds);
        bounds.y()=screenBounds.extent.y-14;
        object.setBounds(bounds);

        object.attach(forwardButton);
        object.bounds(bounds);
        bounds.y()=screenBounds.extent.y-14;
        object.setBounds(bounds);
            
        update();    
    }        
}

void MainForm::updateScrollBar()
{
    ScrollBar scrollBar(*this, definitionScrollBar);
    if (showArticle==displayMode())
    {
        scrollBar.setPosition(article_.firstShownLine(), 0, article_.totalLinesCount()-article_.shownLinesCount(), article_.shownLinesCount());
        scrollBar.show();
    }
    else
        scrollBar.hide();
}

Err MainForm::renderDefinition(Definition& def, ArsLexis::Graphics& graphics, const ArsLexis::Rectangle& rect)
{
    volatile Err error=errNone;
    bool  fForceRecalculate = false;
    if ( showSplashScreen==displayMode() )
    {
        fForceRecalculate = forceSplashRecalculation_;
        forceSplashRecalculation_ = false;
    }
    ErrTry {
        def.render(graphics, rect, renderingPreferences(), fForceRecalculate);
    }
    ErrCatch (ex) {
        error=ex;
    } ErrEndCatch
    return error;
}


void MainForm::drawDefinition(Graphics& graphics, const ArsLexis::Rectangle& bounds)
{
    Definition& def=currentDefinition();
    assert(!def.empty());
    if (showSplashScreen==displayMode())
        updateScrollBar();
    Graphics::ColorSetter setBackground(graphics, Graphics::colorBackground, renderingPreferences().backgroundColor());
    Rectangle rect(bounds);
    rect.explode(0, 15, 0, -33);
    graphics.erase(rect);
    if (showArticle==displayMode())
        rect.explode(2, 2, -12, -4);
    else
        rect.explode(2, 2, -4, -4);
    Err error=errNone;
    bool doubleBuffer=true;
    const iPediaApplication& app=static_cast<const iPediaApplication&>(application());
    if (app.romVersionMajor()<5 && app.diaSupport() && app.diaSupport().hasSonySilkLib())
        doubleBuffer=false;
        
    if (doubleBuffer)
    {
        WinHandle wh=WinCreateOffscreenWindow(bounds.width(), bounds.height(), windowFormat(), &error);
        if (wh!=0)
        {
            {
            Graphics offscreen(wh);
            ActivateGraphics act(offscreen);
            error=renderDefinition(def, offscreen, rect);
            if (!error)
                offscreen.copyArea(rect, graphics, rect.topLeft);
            }
            WinDeleteWindow(wh, false);
        }
        else 
            doubleBuffer=false;
    }
    if (!doubleBuffer)
        error=renderDefinition(def, graphics, rect);
    if (errNone!=error) 
    {
        def.clear();
        setTitle(appName);
        setDisplayMode(showSplashScreen);
        update();
        iPediaApplication::sendDisplayAlertEvent(notEnoughMemoryAlert);
    }
    else if (showArticle==displayMode())            
        updateScrollBar();    
}

void MainForm::draw(UInt16 updateCode)
{
    Graphics graphics(windowHandle());
    Rectangle rect(bounds());
    Rectangle progressArea(rect.x(), rect.height()-17, rect.width(), 17);
    if (redrawAll==updateCode)
    {
        if (visible())
            graphics.erase(progressArea);
        iPediaForm::draw(updateCode);
        graphics.drawLine(rect.x(), rect.height()-18, rect.width(), rect.height()-18);
        drawDefinition(graphics, rect);
    }

    const iPediaApplication& app=static_cast<const iPediaApplication&>(application());
    const LookupManager* lookupManager=app.getLookupManager();
    if (lookupManager && lookupManager->lookupInProgress())
        lookupManager->showProgress(graphics, progressArea);
    if (enableInputFieldAfterUpdate_)
    {
        enableInputFieldAfterUpdate_=false;
        Field field(*this, termInputField);
        field.show();
        field.focus();
    }
}


inline void MainForm::handleScrollRepeat(const EventType& event)
{
    scrollDefinition(event.data.sclRepeat.newValue-event.data.sclRepeat.value, scrollLine, false);
}

void MainForm::scrollDefinition(int units, MainForm::ScrollUnit unit, bool updateScrollbar)
{
    Definition& def=currentDefinition();
    if (def.empty())
        return;
    WinHandle thisWindow=windowHandle();
    Graphics graphics(thisWindow);
    if (scrollPage==unit)
        units*=(def.shownLinesCount());
    
    bool doubleBuffer=true;
    if (-1==units || 1==units)
        doubleBuffer=false;
        
    const iPediaApplication& app=static_cast<const iPediaApplication&>(application());
    if (app.romVersionMajor()<5 && app.diaSupport() && app.diaSupport().hasSonySilkLib())
        doubleBuffer=false;

    if (doubleBuffer)
    {
        Rectangle b=bounds();
        Rectangle rect=b;
        rect.explode(2, 17, -12, -37);
        Err error=errNone;

        WinHandle wh=WinCreateOffscreenWindow(b.width(), b.height(), windowFormat(), &error);
        if (wh!=0)
        {
            {
            Graphics offscreen(wh);
            ActivateGraphics act(offscreen);
            graphics.copyArea(b, offscreen, Point(0, 0));
            def.scroll(offscreen, renderingPreferences(), units);
            offscreen.copyArea(b, graphics, Point(0, 0));
            }
            WinDeleteWindow(wh, false);
        }
        else
            doubleBuffer=false;
    }            
    if (!doubleBuffer)
        def.scroll(graphics, renderingPreferences(), units);
    if (updateScrollbar)
        updateScrollBar();
}

void MainForm::moveHistory(bool forward)
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->moveHistory(forward);
}


void MainForm::handleControlSelect(const EventType& event)
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    switch (event.data.ctlSelect.controlID)
    {
        case searchButton:
             // If button held for more than ~300msec, perform full text search.
            search(TimGetTicks()-lastPenDownTimestamp_>app.ticksPerSecond()/3);
            break;
            
        case backButton:
            moveHistory(false);
            break;
        
        case forwardButton:
            moveHistory(true);
            break;
        
        default:
            assert(false);
    }
}

void MainForm::setControlsState(bool enabled)
{
    {  // Scopes will allow compiler to optimize stack space allocating both form objects in the same place
        Control control(*this, backButton);
        control.setEnabled(enabled);
        control.attach(forwardButton);
        control.setEnabled(enabled);
        control.attach(searchButton);
        control.setEnabled(enabled);
    }

    {        
        if (enabled)
            enableInputFieldAfterUpdate_ =true;
        else
        {
            releaseFocus();
            Field field(*this, termInputField);
            field.hide();
        }
    }
}

void MainForm::handleLookupFinished(const EventType& event)
{
    setControlsState(true);
    const LookupFinishedEventData& data=reinterpret_cast<const LookupFinishedEventData&>(event.data);
    switch (data.outcome)
    {
        case data.outcomeDefinition:
            updateAfterLookup();
            break;
            
        case data.outcomeList:
            Application::popupForm(searchResultsForm);
            break;
            
        case data.outcomeNotFound:
            {
                Field field(*this, termInputField);
                field.select();
            }
            // No break is intentional.
            
        default:
            update();
    }
    
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    if (app.preferences().articleCount!=articleCountSet_) 
    {
        articleCountSet_=app.preferences().articleCount;
        updateArticleCountEl(articleCountSet_,app.preferences().databaseTime);
        forceSplashRecalculation_=true;
    }
    
    LookupManager* lookupManager=app.getLookupManager();
    assert(lookupManager);
    lookupManager->handleLookupFinishedInForm(data);

    if (app.inStressMode())
    {
        EventType event;
        MemSet(&event, sizeof(event), 0);
        event.eType=penDownEvent;
        event.penDown=true;
        event.tapCount=1;
        event.screenX=1;
        event.screenY=50;
        EvtAddEventToQueue(&event);
        MemSet(&event, sizeof(event), 0);
        event.eType=penUpEvent;
        event.penDown=false;
        event.tapCount=1;
        event.screenX=1;
        event.screenY=50;
        EvtAddEventToQueue(&event);
        randomArticle();
    }        
}

static int formatNumber(long num, char *buf, int bufSize)
{
    char buffer[32];
    int len = StrPrintF(buffer,"%ld",num);

    int lenOut = len + ((len-1)/3);  // a dot "." every 3 chars
    assert(bufSize>=lenOut+1);
    // copy str in buffer to output buf from the end, adding "." every 3 chars
    char *tmp = buffer+len;
    assert( '\0' == *tmp );
    char *out = buf+lenOut;
    int toDot = 4; // 3 + 1 for trailing '\0'
    while (true)
    {
        *out = *tmp;
        if (tmp==buffer)
            break;
        --out;
        --tmp;
        --toDot;
        if (0==toDot)
        {
            toDot = 3;
            *out-- = '.';  // don't put "." if this is the last number
        }
    }
    assert(out==buf);
    return lenOut;
}

void MainForm::updateArticleCountEl(long articleCount, ArsLexis::String& dbTime)
{
    assert(NULL!=articleCountElement_);
    assert(-1!=articleCount);
    assert(8==dbTime.length());
    char buffer[32];
    int len = formatNumber(articleCount,(char*)buffer,sizeof(buffer));
    assert(len != -1 );
#ifdef TEST_BAD
    // TODO: BUG: this text shows the problem with rendering of centered text
    // on sim 5.3 the "2" from "273..." is cut and on emu 3.5 the first line
    // is not even visible (I only see 2004-05-22 centered in second line)
    ArsLexis::String articleCountText="273.551 articles, database updated on 2004-05-22";
#else
    ArsLexis::String articleCountText="";
    articleCountText.append(buffer, len);
    articleCountText.append(" articles, database updated on ");
    articleCountText.append(dbTime.substr(0,4));
    articleCountText.append("-");
    articleCountText.append(dbTime.substr(4,2));
    articleCountText.append("-");
    articleCountText.append(dbTime.substr(6,2));
#endif
    articleCountElement_->setText(articleCountText);
}

void MainForm::handleExtendSelection(const EventType& event, bool finish)
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    const LookupManager* lookupManager=app.getLookupManager();
    if (lookupManager && lookupManager->lookupInProgress())
        return;
    Definition& def=currentDefinition();
    if (def.empty())
        return;
    ArsLexis::Point point(event.screenX, event.screenY);
    Graphics graphics(windowHandle());
    def.extendSelection(graphics, app.preferences().renderingPreferences, point, finish);
}

inline void MainForm::handlePenDown(const EventType& event)
{
    lastPenDownTimestamp_=TimGetTicks();
    handleExtendSelection(event);
}

bool MainForm::handleEvent(EventType& event)
{
    bool handled=false;
    switch (event.eType)
    {
        case keyDownEvent:
            handled=handleKeyPress(event);
            break;
            
        case ctlSelectEvent:
            handleControlSelect(event);
            break;
        
        case penUpEvent:
            handleExtendSelection(event, true);
            break;
    
        case penMoveEvent:
            handleExtendSelection(event);
            break;        
                
        case sclRepeatEvent:
            handleScrollRepeat(event);
            break;
            
        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled=true;
            break;     
            
        case LookupManager::lookupStartedEvent:
            setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            handled=true;
            break;

        case penDownEvent:
            handlePenDown(event);
            break;
    
        default:
            handled=iPediaForm::handleEvent(event);
    }
    return handled;
}

void MainForm::updateNavigationButtons()
{
    const LookupHistory& history=getHistory();

    Control control(*this, backButton);
    bool enabled=history.hasPrevious();
    control.setEnabled(enabled);
    control.setGraphics(enabled?backBitmap:backDisabledBitmap);
        
    control.attach(forwardButton);
    enabled=history.hasNext();
    control.setEnabled(enabled);
    control.setGraphics(enabled?forwardBitmap:forwardDisabledBitmap);
}


void MainForm::updateAfterLookup()
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager();
    assert(lookupManager!=0);
    if (lookupManager)
    {
        article_.replaceElements(lookupManager->lastDefinitionElements());
        setDisplayMode(showArticle);
        const LookupHistory& history=getHistory();
        if (history.hasCurrentTerm())
            setTitle(history.currentTerm());
        
        update();
        
        Field field(*this, termInputField);        
        field.replace(lookupManager->lastInputTerm());
        field.select();                    
    }
    updateNavigationButtons();
}

bool MainForm::handleKeyPress(const EventType& event)
{
    bool handled=false;

    switch (event.data.keyDown.chr)
    {
        case chrPageDown:
            if (showArticle==displayMode())
            {
                scrollDefinition(1, scrollPage);
                handled=true;
            }
            break;
            
        case chrPageUp:
            if (showArticle==displayMode())
            {
                scrollDefinition(-1, scrollPage);
                handled=true;
            }
            break;
        
        case chrDownArrow:
            if (showArticle==displayMode())
            {
                scrollDefinition(1, scrollLine);
                handled=true;
            }
            break;

        case chrUpArrow:
            if (showArticle==displayMode())
            {
                scrollDefinition(-1, scrollLine);
                handled=true;
            }
            break;
            
        case vchrRockerCenter:
        case chrLineFeed:
        case chrCarriageReturn:
            {
                lastPenDownTimestamp_=TimGetTicks();
                Control control(*this, searchButton);
                control.hit();
            }                
            handled=true;
            break;
    }
    return handled;
}

void MainForm::switchServer(const char* server)
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    app.setServer(server);    
}


bool MainForm::handleMenuCommand(UInt16 itemId)
{
    bool handled=false;
    switch (itemId)
    {
    
#ifdef  INTERNAL_BUILD    
        case useDictPcMenuItem:
            switchServer(serverOfficial);
            handled=true;
            break;
            
        case useLocalhostMenuItem:
            switchServer(serverLocalhost);
            handled=true;
            break;

        case toggleStressModeMenuItem:
            handleToggleStressMode();
            handled=true;
            break;
#endif
            
        case registerMenuItem:
            Application::popupForm(registrationForm);
            handled=true;
            break;
            
        case copyMenuItem:
            copySelectionToClipboard();
            handled=true;
            break;
            
        case searchResultsMenuItem:
            Application::popupForm(searchResultsForm);
            handled=true;
            break;

        case randomMenuItem:
            randomArticle();
            handled=true;
            break;

        case arslexisWebsiteMenuItem:
            if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, "http://www.arslexis.com/pda/ipedia.html",NULL) )
                FrmAlert(noWebBrowserAlert);
            handled = true;
            break;

        case aboutMenuItem:
            handleAbout();
            handled=true;
            break;

        case searchMenuItem:
            search();
            handled=true;
            break;

        case fullTextSearchMenuItem:
            search(true);
            handled=true;
            break;
            
        case forwardMenuItem:
            {
                Control control(*this, forwardButton);
                if (control.enabled())
                    control.hit();
            }
            break;
            
        case backMenuItem:
            {
                Control control(*this, backButton);
                if (control.enabled())
                    control.hit();
            }
            break;
        
        default:
            handled=iPediaForm::handleMenuCommand(itemId);
    }
    return handled;
}

void MainForm::randomArticle()
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->lookupRandomTerm();
}

void MainForm::copySelectionToClipboard()
{
    Definition& def=currentDefinition();
    if (def.empty())
        return;
    ArsLexis::String text;
    def.selectionToText(text);
    ClipboardAddItem(clipboardText, text.data(), text.length());
}

bool MainForm::handleWindowEnter(const struct _WinEnterEventType& data)
{
    const FormType* form=*this;
    if (data.enterWindow==static_cast<const void*>(form))
    {
        FormObject object(*this, termInputField);
        object.focus();
        
        iPediaApplication& app=static_cast<iPediaApplication&>(application());
        LookupManager* lookupManager=app.getLookupManager();
        if (lookupManager)
        {
            if (updateDefinitionOnEntry_)
            {
                updateDefinitionOnEntry_=false;
                updateAfterLookup();
            }
            setControlsState(!lookupManager->lookupInProgress());
        }
    }
    return iPediaForm::handleWindowEnter(data);
}

void MainForm::handleToggleStressMode()
{
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    if (app.inStressMode())
        app.toggleStressMode(false);
    else
    {
        app.toggleStressMode(true);
        randomArticle();
    }        
}

void MainForm::handleAbout()
{
    if (showSplashScreen!=displayMode())
    {
        setDisplayMode(showSplashScreen);
        update();
    }
    else 
    {
        if (!article_.empty())
        {
            setDisplayMode(showArticle);
            update();
        }
    }                
}

void MainForm::search(bool fullText)
{
    Field field(*this, termInputField);
    const char* text=field.text();
    uint_t textLen;
    if (0==text || 0==(textLen=StrLen(text)))
        return;
        
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager(true);
    if (!lookupManager || lookupManager->lookupInProgress())
        return;

    String term(text, textLen);
    if (!fullText)
    {
        if (!lookupManager->lookupIfDifferent(term) && showArticle!=displayMode())
            updateAfterLookup();
    }
    else
        lookupManager->search(term);
}

MainForm::RenderingProgressReporter::RenderingProgressReporter(MainForm& form):
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

void MainForm::RenderingProgressReporter::reportProgress(uint_t percent) 
{
    if (percent==lastPercent_)
        return;

    if (0==(lastPercent_=percent))
    {
        ticksAtStart_=TimGetTicks();
        showProgress_=false;
        afterTrigger_=false;
        return;
    }
    
    if (!afterTrigger_)
    {
        // Delay before we start displaying progress meter in milliseconds. Timespans < 300ms are typically perceived "instant"
        // so we shouldn't distract user if the time is short enough.
        static const uint_t delay=100; 
        UInt32 ticksDiff=TimGetTicks()-ticksAtStart_;
        iPediaApplication& app=static_cast<iPediaApplication&>(form_.application());
        ticksDiff*=1000;
        ticksDiff/=app.ticksPerSecond();
        if (ticksDiff>=delay)
            afterTrigger_=true;
        if (afterTrigger_ && percent<=20)
            showProgress_=true;
    }
    
    if (!showProgress_)
        return;
        
    Graphics graphics(form_.windowHandle());
    Rectangle bounds=form_.bounds();
    bounds.explode(2, 17, -12, -37);

    ActivateGraphics act(graphics);
#if IPEDIA_USES_TEXT_RENDERING_PROGRESS
    Font f;
    Graphics::FontSetter fset(graphics, f);
    uint_t height=graphics.fontHeight();
    Rectangle rect(bounds.x(), bounds.y()+(bounds.height()-height)/2, bounds.width(), height);
    graphics.erase(rect);
    char buffer[100];
    StrPrintF(buffer, waitText_.c_str(), percent);
    graphics.drawCenteredText(buffer, rect.topLeft, rect.width());
#else
    uint_t height=10;
    Rectangle rect(bounds.x()+16, bounds.y()+(bounds.height()-height)/2, bounds.width()-22, height);
    PatternType oldPattern=WinGetPatternType();
    WinSetPatternType(blackPattern);
    RectangleType nativeRec=toNative(rect);
    nativeRec.extent.x*=percent;
    nativeRec.extent.x/=100;
    WinPaintRectangle(&nativeRec, 0);
    nativeRec.topLeft.x+=nativeRec.extent.x;
    nativeRec.extent.x=rect.width()-nativeRec.extent.x;
    WinSetPatternType(grayPattern);
    WinPaintRectangle(&nativeRec, 0);
    WinSetPatternType(oldPattern);        
#endif    
}

void MainForm::prepareSplashScreen()
{
    Definition::Elements_t elems;

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    FontEffects fxSmall;
    fxSmall.setSmall(true);

    FormattedTextElement* text;
    elems.push_back(new LineBreakElement(1,3));

    elems.push_back(text=new FormattedTextElement("ArsLexis iPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setStyle(styleHeader);
    text->setEffects(fxBold);

    elems.push_back(new LineBreakElement(1,2));

    const char* version="Ver " appVersion
#ifdef INTERNAL_BUILD
    " (internal)"
#endif
/*
#ifdef DEBUG
        " (debug)"
#endif*/
    ;
    elems.push_back(text=new FormattedTextElement(version));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setEffects(fxSmall);
    
    elems.push_back(new LineBreakElement(3,4));
    elems.push_back(text=new FormattedTextElement("Software \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new FormattedTextElement("ArsLexis"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setHyperlink("http://www.arslexis.com/pda/ipedia.html", hyperlinkExternal);

    elems.push_back(new LineBreakElement(1,4));
    elems.push_back(text=new FormattedTextElement("Data \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new FormattedTextElement("WikiPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setHyperlink("http://www.wikipedia.org", hyperlinkExternal);

    elems.push_back(new LineBreakElement());
    elems.push_back(articleCountElement_=new FormattedTextElement(" "));
    if (-1!=articleCountSet_)
    {
        iPediaApplication& app=static_cast<iPediaApplication&>(application());
        updateArticleCountEl(articleCountSet_,app.preferences().databaseTime);
    }
    articleCountElement_->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(new LineBreakElement());
    elems.push_back(new LineBreakElement(3,4));
    elems.push_back(text=new FormattedTextElement("Using iPedia: "));
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new FormattedTextElement("tutorial"));
    text->setJustification(DefinitionElement::justifyLeft);
    /*text->setHyperlink("http://www.arslexis.com/pda/ipedia.html", hyperlinkExternal);*/
    elems.push_back(new LineBreakElement());
    
    about_.replaceElements(elems);    
}
    

