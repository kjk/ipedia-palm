#include "MainForm.hpp"
#include <FormObject.hpp>
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"
#include "LookupHistory.hpp"
#include <SysUtils.hpp>
#include <Text.hpp>
#include <StringListForm.hpp>

#include <FormattedTextElement.hpp>
#include <LineBreakElement.hpp>
#include <ParagraphElement.hpp>

#include <LangNames.hpp>

using namespace ArsLexis;

static char_t** ExtractLinksFromDefinition(Definition& def, int& strListSize)
{
    int       strCount;
    char_t ** strList;
    for (int phase=0; phase<=1; phase++)
    {
        if (1 == phase)
        {
            strListSize = strCount;
            strList = new char_t *[strCount];
        }
        strCount = 0;

        Definition::const_iterator end = def.end();
        for (Definition::const_iterator it = def.begin(); it != end; ++it)
        {
            if ((*it)->isTextElement())
            {
                GenericTextElement* txtEl = static_cast<GenericTextElement*>(*it);
                if ((txtEl->isHyperlink()) &&
                    ((txtEl->hyperlinkProperties()->type==hyperlinkTerm) ||
                     (txtEl->hyperlinkProperties()->type==hyperlinkExternal)))
                {
                    if (1==phase)
                    {
                        strList[strCount] = StringCopy(txtEl->hyperlinkProperties()->resource);
                        replaceCharInString(strList[strCount], _T('_'), _T(' '));
                    }
                    strCount += 1;
                }
            }
        }
    }
    return strList;
}

MainForm::MainForm(iPediaApplication& app):
    iPediaForm(app, mainForm),
    renderingProgressReporter_(*this),
    displayMode_(showAbout),
    lastPenDownTimestamp_(0),
    updateDefinitionOnEntry_(false),
    enableInputFieldAfterUpdate_(false),
    forceAboutRecalculation_(false),
    articleCountElement_(0),
    articleCountSet_(-1),
    penUpsToEat_(0),
    log_(_T("MainForm")),
    ignoreEvents_(false)
{
    articleCountSet_ = app.preferences().articleCount;
    article_.setRenderingProgressReporter(&renderingProgressReporter_);
    article_.setHyperlinkHandler(&app.hyperlinkHandler());

    article_.setInteractionBehavior(Definition::behavMouseSelection);

    /*behavDoubleClickSelection = 1,
    behavMouseSelection = 2,
    behavUpDownScroll = 4,
    behavHyperlinkNavigation = 8*/

    about_.setHyperlinkHandler(&app.hyperlinkHandler());
    tutorial_.setHyperlinkHandler(&app.hyperlinkHandler());
    register_.setHyperlinkHandler(&app.hyperlinkHandler());
    wikipedia_.setHyperlinkHandler(&app.hyperlinkHandler());
    prepareAbout();    
    // TODO: make those on-demand
    prepareHowToRegister();
    prepareTutorial();
    prepareWikipedia();
}

bool MainForm::handleOpen()
{
    bool fOk=iPediaForm::handleOpen();
    updateNavigationButtons();
    // to prevent accidental selection of links in main About page
    penUpsToEat_ = 1;
    return fOk;
}

inline const LookupHistory& MainForm::getHistory() const
{
    return static_cast<const iPediaApplication&>(application()).history();
}

void MainForm::resize(const ArsLexis::Rectangle& screenBounds)
{
    Rectangle bounds(this->bounds());
    if (screenBounds==bounds)
        return;

    setBounds(screenBounds);

    FormObject object(*this, definitionScrollBar);
    object.bounds(bounds);
    bounds.x() = screenBounds.extent.x-8;
    bounds.height() = screenBounds.extent.y-36;
    object.setBounds(bounds);
    
    object.attach(termInputField);
    object.bounds(bounds);
    bounds.y() = screenBounds.extent.y-14;
    bounds.width() = screenBounds.extent.x-63;
    object.setBounds(bounds);

    object.attach(searchButton);
    object.bounds(bounds);
    bounds.x() = screenBounds.extent.x-34;
    bounds.y() = screenBounds.extent.y-14;
    object.setBounds(bounds);
    
    object.attach(backButton);
    object.bounds(bounds);
    bounds.y() = screenBounds.extent.y-14;
    object.setBounds(bounds);

    object.attach(forwardButton);
    object.bounds(bounds);
    bounds.y() = screenBounds.extent.y-14;
    object.setBounds(bounds);
        
    update();    
}

void MainForm::updateScrollBar()
{
    ScrollBar scrollBar(*this, definitionScrollBar);
    if (showAbout==displayMode())
    {
        scrollBar.hide();
    }
    else
    {
        Definition& def = currentDefinition();
        scrollBar.setPosition(def.firstShownLine(), 0, def.totalLinesCount()-def.shownLinesCount(), def.shownLinesCount());
        scrollBar.show();
    }
}

Err MainForm::renderDefinition(Definition& def, ArsLexis::Graphics& graphics, const ArsLexis::Rectangle& rect)
{
    bool         fForceRecalculate = false;
    if ( showAbout==displayMode() )
    {
        fForceRecalculate = forceAboutRecalculation_;
        forceAboutRecalculation_ = false;
    }
    return def.render(graphics, rect, renderingPreferences(), fForceRecalculate);
}

void MainForm::drawDefinition(Graphics& graphics, const ArsLexis::Rectangle& bounds)
{
    Definition& def=currentDefinition();
    assert(!def.empty());
    Graphics::ColorSetter setBackground(graphics, Graphics::colorBackground, renderingPreferences().backgroundColor());
    Rectangle rect(bounds);
    rect.explode(0, 15, 0, -33);
    graphics.erase(rect);
    if (showAbout==displayMode())
    {
        updateScrollBar(); //hide the scrollbar
        rect.explode(2, 2, -4, -4);
    }
    else
        rect.explode(2, 2, -12, -4);
    Err error = errNone;
    bool doubleBuffer = true;
    if (app().romVersionMajor()<5 && app().diaSupport() && app().diaSupport().hasSonySilkLib())
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
        if (showAbout!=displayMode())
        {
            def.clear();
            setTitle(appName);
            setDisplayMode(showAbout);
            update();
        }
        iPediaApplication::sendDisplayAlertEvent(notEnoughMemoryAlert);
    } 
    else
    {
        updateScrollBar();
    }
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

    if (app().fLookupInProgress())
    {
        app().getLookupManager()->showProgress(graphics, progressArea);
    }

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

    if (app().romVersionMajor()<5 && app().diaSupport() && app().diaSupport().hasSonySilkLib())
        doubleBuffer=false;

    if (doubleBuffer)
    {
        Rectangle b = bounds();
        Rectangle rect = b;
        rect.explode(2, 17, -12, -37);
        Err error = errNone;

        WinHandle wh=WinCreateOffscreenWindow(b.width(), b.height(), windowFormat(), &error);
        if (wh!=0)
        {
            Graphics offscreen(wh);
            ActivateGraphics act(offscreen);
            graphics.copyArea(b, offscreen, Point(0, 0));
            def.scroll(offscreen, renderingPreferences(), units);
            offscreen.copyArea(b, graphics, Point(0, 0));
            WinDeleteWindow(wh, false);
        }
        else
            doubleBuffer = false;
    }            
    if (!doubleBuffer)
        def.scroll(graphics, renderingPreferences(), units);

    if (updateScrollbar)
        updateScrollBar();
}

void MainForm::moveHistory(bool forward)
{
    LookupManager* lookupManager=app().getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->moveHistory(forward);
}

void MainForm::handleControlSelect(const EventType& event)
{
    iPediaApplication& app = static_cast<iPediaApplication&>(application());
    bool fFullText = false;
    switch (event.data.ctlSelect.controlID)
    {
        case searchButton:
            // If button held for more than ~300msec, perform full text search.
            if (TimGetTicks()-lastPenDownTimestamp_ > app.ticksPerSecond()/3)
                fFullText = true;
            search(fFullText);
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
        case data.outcomeArticleBody:
            updateAfterLookup();
            break;

        case data.outcomeList:
            Application::popupForm(searchResultsForm);
            break;

        case data.outcomeDatabaseSwitched:
            // recalc about info and show about screen
            setDisplayMode(showAbout);
            updateArticleCountEl(app().preferences().articleCount, app().preferences().databaseTime);
            forceAboutRecalculation_ = true;
            {
                Field field(*this, termInputField);        
                field.replace(_T(""));
            }
            update();
            break;

        case data.outcomeAvailableLangs:
            assert(!app().preferences().availableLangs.empty());
            if (app().preferences().availableLangs.empty())
            {
                // this shouldn't happen but if it does, we want to break
                // to avoid infinite loop (changeDatabase() will issue request
                // to get available langs whose result we handle here
                break;
            }
            changeDatabase();
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
    
    if (app().preferences().articleCount!=articleCountSet_) 
    {
        articleCountSet_ = app().preferences().articleCount;
        updateArticleCountEl(articleCountSet_, app().preferences().databaseTime);
        forceAboutRecalculation_ = true;
    }

    LookupManager* lookupManager=app().getLookupManager();
    assert(lookupManager);
    lookupManager->handleLookupFinishedInForm(data);

    if (app().inStressMode())
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

void MainForm::updateArticleCountEl(long articleCount, ArsLexis::String& dbTime)
{
    assert(NULL!=articleCountElement_);
    assert(-1!=articleCount);
    assert(8==dbTime.length());
    char buffer[32];
    int len = formatNumber(articleCount, buffer, sizeof(buffer));
    assert(len != -1 );
    String articleCountText;
    articleCountText.append(buffer, len);
    articleCountText.append(" articles. ");

    const String& langCode = app().preferences().currentLang;
    const char_t* langName = GetLangNameByLangCode(langCode);
    if (NULL == langName)
        langName = _T("Unknown");
        
    articleCountText.append(langName);

    articleCountText.append(" encyclopedia last updated on ");
    articleCountText.append(dbTime, 0, 4);
    articleCountText.append(1, '-');
    articleCountText.append(dbTime, 4, 2);
    articleCountText.append(1, '-');
    articleCountText.append(dbTime, 6, 2);
    articleCountElement_->setText(articleCountText);
}

void MainForm::handleExtendSelection(const EventType& event)
{
    const LookupManager* lookupManager=app().getLookupManager();
    if (lookupManager && lookupManager->lookupInProgress())
        return;
    Definition& def = currentDefinition();
    if (def.empty())
        return;
    ArsLexis::Point point(event.screenX, event.screenY);
    Graphics graphics(windowHandle());
    uint_t tapCount = 0;
    if (penUpEvent == event.eType)
        tapCount = event.tapCount;
    def.extendSelection(graphics, app().preferences().renderingPreferences, point, tapCount);
}

inline void MainForm::handlePenDown(const EventType& event)
{
    lastPenDownTimestamp_=TimGetTicks();
    handleExtendSelection(event);
}

bool MainForm::handleEvent(EventType& event)
{
    bool handled=false;
    if (ignoreEvents_)
        return false;
    switch (event.eType)
    {
        case keyDownEvent:
            handled=handleKeyPress(event);
            break;
            
        case ctlSelectEvent:
            handleControlSelect(event);
            break;
        
        case penUpEvent:
            if (penUpsToEat_ > 0)
            {
                --penUpsToEat_;
                handled = true;
                break;
            }
            handleExtendSelection(event);
            break;
    
        case penMoveEvent:
            handleExtendSelection(event);
            break;        
                
        case sclRepeatEvent:
            handleScrollRepeat(event);
            break;
            
        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled = true;
            break;     
            
        case LookupManager::lookupStartedEvent:
            setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            handled = true;
            break;

        case iPediaApplication::appRegisterEvent:
            Application::popupForm(registrationForm);
            handled = true;
            break;

        case iPediaApplication::appRegistrationFinished:
            // need to re-create about page just in case registration status
            // has changed
            prepareAbout();
            forceAboutRecalculation_=true;
            update();
            handled = true;
            break;

        case iPediaApplication::appLangNotAvailable:
            // for whatever reason server told us that the language
            // we were using is not available. That shouldn't happen
            // because we only use langauges that server gives us, but
            // it might becaues e.g. we might disable a given language on the
            // server and the client might have outdated list of available
            // languages. In this case we switch to "en" (English) which
            // should always be available
            FrmAlert(langNotAvailableAlert);
            LookupManager* lookupManager = app().getLookupManager(true);
            if (lookupManager && !lookupManager->lookupInProgress())
                lookupManager->switchDatabase("en");
            handled = true;
            break;

        case iPediaApplication::appForceUpgrade:
            {
                UInt16 buttonId = FrmAlert(forceUpgradeAlert);
                if (0==buttonId)
                {
                    // this is "Update" button so take them to a web page
                    if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, "http://www.arslexis.com/updates/palm-ipedia-1-1.html",NULL) )
                        FrmAlert(noWebBrowserAlert);
                }
                handled = true;
            }
            break;

        case iPediaApplication::appRandomWord:
            randomArticle();
            handled = true;
            break;

        case penDownEvent:
            handlePenDown(event);
            break;
    
        default:
            handled = iPediaForm::handleEvent(event);
    }
    return handled;
}

void MainForm::updateNavigationButtons()
{
    const LookupHistory& history=getHistory();

    Control control(*this, backButton);
    bool enabled = history.hasPrevious();
    control.setEnabled(enabled);
    if (enabled)
        control.setGraphics(backBitmap);
    else
        control.setGraphics(backDisabledBitmap);
        
    control.attach(forwardButton);
    enabled = history.hasNext();
    control.setEnabled(enabled);
    if (enabled)
        control.setGraphics(forwardBitmap);
    else
        control.setGraphics(forwardDisabledBitmap);

}

void MainForm::updateAfterLookup()
{
    LookupManager* lookupManager = app().getLookupManager();
    assert(lookupManager!=0);
    if (lookupManager)
    {
        article_.replaceElements(lookupManager->lastDefinitionElements());
        setDisplayMode(showArticle);
        const LookupHistory& history = getHistory();
        if (history.hasCurrentTerm())
            setTitle(history.currentTerm());
        
        update();
        
        Field field(*this, termInputField);        
        field.replace(lookupManager->lastSearchTerm());
        field.select();                    
    }
    updateNavigationButtons();
}

bool MainForm::handleKeyPress(const EventType& event)
{
    bool handled = false;

    switch (event.data.keyDown.chr)
    {
        case chrPageDown:
            if (fCanScrollDef())
            {
                scrollDefinition(1, scrollPage);
                handled = true;
            }
            break;
            
        case chrPageUp:
            if (fCanScrollDef())
            {
                scrollDefinition(-1, scrollPage);
                handled = true;
            }
            break;
        
        case chrDownArrow:
            if (fCanScrollDef())
            {
                scrollDefinition(1, scrollLine);
                handled = true;
            }
            break;

        case chrUpArrow:
            if (fCanScrollDef())
            {
                scrollDefinition(-1, scrollLine);
                handled = true;
            }
            break;
            
        case vchrRockerCenter:
        case chrLineFeed:
        case chrCarriageReturn:
            {
                lastPenDownTimestamp_ = TimGetTicks();
                Control control(*this, searchButton);
                control.hit();
            }                
            handled = true;
            break;
    }
    return handled;
}

void MainForm::switchServer(const char* server)
{
    app().setServer(server);    
}

bool MainForm::handleMenuCommand(UInt16 itemId)
{
    bool handled = false;

    switch (itemId)
    {
#ifdef  INTERNAL_BUILD    
        case useDictPcMenuItem:
            switchServer(SERVER_OFFICIAL);
            handled = true;
            break;
            
        case useLocalhostMenuItem:
            switchServer(SERVER_LOCALHOST);
            handled = true;
            break;

        case toggleStressModeMenuItem:
            handleToggleStressMode();
            handled = true;
            break;
#endif
            
        case registerMenuItem:
#ifdef UNLOCKED
            FrmAlert(alreadyRegisteredAlert);
#else
            Application::popupForm(registrationForm);
#endif
            handled = true;
            break;
            
        case copyMenuItem:
            copySelectionToClipboard();
            handled = true;
            break;
            
        case searchResultsMenuItem:
            Application::popupForm(searchResultsForm);
            handled = true;
            break;

        case randomMenuItem:
            randomArticle();
            handled = true;
            break;

        case changeDatabaseMenuItem:
            changeDatabase();
            handled = true;
            break;

        case arslexisWebsiteMenuItem:
            if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, "http://www.arslexis.com/pda/palm.html",NULL) )
                FrmAlert(noWebBrowserAlert);
            handled = true;
            break;

        case checkUpdatesMenuItem:
            if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, "http://www.arslexis.com/updates/palm-ipedia-1-1.html",NULL) )
                FrmAlert(noWebBrowserAlert);
            handled = true;
            break;

        case aboutMenuItem:
            if (showAbout!=displayMode())
            {
                setDisplayMode(showAbout);
                update();
            }
            handled = true;
            break;

        case tutorialMenuItem:
            if (showTutorial!=displayMode())
            {
                setDisplayMode(showTutorial);
                update();
            }
            handled = true;
            break;

        case searchMenuItem:
            search();
            handled = true;
            break;

        case extendedSearchMenuItem:
            search(true);
            handled = true;
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

        case historyMenuItem:
            doHistory();
            handled = true;
            break;

/*        case linkedArticlesMenuItem:
            doLinkedArticles();
            handled = true;
            break;

        case linkingArticlesMenuItem:
            doLinkingArticles();
            handled = true;
            break;*/

        default:
            handled = iPediaForm::handleMenuCommand(itemId);
    }
    // to prevent accidental selection of links in main About page
    penUpsToEat_ = 1;
    return handled;
}

void MainForm::doHistory()
{
    LookupManager* lookupManager=app().getLookupManager(true);
    if (NULL==lookupManager)
        return;
    LookupHistory& lookupHistory = lookupManager->getHistory();
    if (lookupHistory.empty())
        return;
    const StringList_t& history = lookupHistory.getHistory();
    app().strList = StringListFromStringList(history, app().strListSize);
    ReverseStringList(app().strList, app().strListSize);
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

void MainForm::doLookupSelectedTerm(int selectedStr)
{
    if (NOT_SELECTED==selectedStr)
        goto Exit;

    const char_t* term = app().strList[selectedStr];

    LookupManager* lookupManager=app().getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->lookupIfDifferent(term, app().preferences().currentLang);

Exit:

    FreeStringList(app().strList, app().strListSize);
    app().strList = NULL;
}

void MainForm::doLinkedArticles()
{
    Definition& def = currentDefinition();
    app().strList = ExtractLinksFromDefinition(def, app().strListSize);
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

void MainForm::doLinkingArticles()
{
    LookupManager* lookupManager = app().getLookupManager(true);
    if (NULL==lookupManager)
        return;

    const String& reverseLinks = lookupManager->lastReverseLinks();
    app().strList = StringListFromString(reverseLinks, "\n", app().strListSize);
    for (int i=0; i<app().strListSize; i++)
    {
        replaceCharInString(app().strList[i], _T('_'), _T(' '));
    }
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

void MainForm::changeDatabase()
{
    String availableLangs = app().preferences().availableLangs;
    if (availableLangs.empty())
    {
        // if we don't have available langs, issue a request asking for it
        LookupManager* lookupManager=app().getLookupManager(true);
        if (lookupManager && !lookupManager->lookupInProgress())
            lookupManager->getAvailableLangs();
        return;
    }

    char_t **strList = StringListFromString(availableLangs, " ", app().strListSize);
    const char_t* fullName;
    String nameToDisplay;

    for (int i=0; i<app().strListSize; i++)
    {
        fullName = GetLangNameByLangCode(strList[i]);
        if (NULL != fullName)
            nameToDisplay.assign(fullName);
        else
            nameToDisplay.assign(_T("Unknown"));

        nameToDisplay.append(_T(" ("));
        nameToDisplay.append(strList[i]);
        nameToDisplay.append(_T(")"));

        delete [] strList[i];
        strList[i] = StringCopy(nameToDisplay);
    }

    app().strList = strList;
    int sel = showStringListForm(app().strList, app().strListSize);
    doDbSelected(sel);
}

int MainForm::showStringListForm(char_t* strList[], int strListSize)
{
    StringListForm* form = new StringListForm(app(), stringListForm, stringList, selectButton, cancelButton);
    form->initialize();
    form->SetStringList(app().strListSize, app().strList);
    ignoreEvents_ = true; // Strange things happen here and if we don't prevent MainForm from processing events we'll overflow the stack :-(
    int sel = form->showModalAndGetSelection();
    ignoreEvents_ = false;
    update();
    delete form;
    return sel;    
}

void MainForm::doDbSelected(int selectedStr)
{
    if (NOT_SELECTED == selectedStr)
        goto Exit;

    char_t *fullName = app().strList[selectedStr];
    // a hack: lang is what is inside "(" and ")"
    while (*fullName && (*fullName!='('))
        ++fullName;
    assert(*fullName);
    char_t *langName = fullName+1;
    langName[2] = '\0';

    LookupManager* lookupManager=app().getLookupManager(true);
    assert(NULL != lookupManager);

    if (lookupManager && !lookupManager->lookupInProgress())
    {
        lookupManager->switchDatabase(langName);
    }

Exit:
    FreeStringList(app().strList, app().strListSize);
    app().strList = NULL;
}

void MainForm::randomArticle()
{
    LookupManager* lookupManager=app().getLookupManager(true);
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
    const FormType* form = *this;
    if (data.enterWindow==static_cast<const void*>(form))
    {
        FormObject object(*this, termInputField);
        object.focus();
        
        LookupManager* lookupManager = app().getLookupManager();
        if (lookupManager)
        {
            if (updateDefinitionOnEntry_)
            {
                updateDefinitionOnEntry_ = false;
                updateAfterLookup();
            }
            setControlsState(!lookupManager->lookupInProgress());
        }
    }
    return iPediaForm::handleWindowEnter(data);
}

void MainForm::handleToggleStressMode()
{
    if (app().inStressMode())
        app().toggleStressMode(false);
    else
    {
        app().toggleStressMode(true);
        randomArticle();
    }        
}

void MainForm::search(bool fullText)
{
    Field field(*this, termInputField);
    const char* text = field.text();
    uint_t textLen;
    if (0==text || 0==(textLen=StrLen(text)))
        return;
        
    LookupManager* lookupManager=app().getLookupManager(true);
    if (!lookupManager || lookupManager->lookupInProgress())
        return;

    String term(text, textLen);
    if (!fullText)
    {
        if (!lookupManager->lookupIfDifferent(term, app().preferences().currentLang) && showArticle!=displayMode())
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

    lastPercent_ = percent;
    if (0==percent)
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
        UInt32 ticksDiff = TimGetTicks()-ticksAtStart_;
        iPediaApplication& app=static_cast<iPediaApplication&>(form_.application());
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
    Rectangle bounds = form_.bounds();
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
    Rectangle rect(bounds.x()+16, bounds.y()+(bounds.height()-height)/2, bounds.width()-22, height);
    PatternType oldPattern = WinGetPatternType();
    WinSetPatternType(blackPattern);
    RectangleType nativeRec=toNative(rect);
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

static void wikipediaActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);
    assert(MainForm::showWikipedia!=mf->displayMode());
    mf->setDisplayMode(MainForm::showWikipedia);
    mf->update();
}

static void tutorialActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);
    assert(MainForm::showTutorial!=mf->displayMode());
    mf->setDisplayMode(MainForm::showTutorial);
    mf->update();
}

static void unregisteredActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);
    assert(MainForm::showRegister!=mf->displayMode());
    mf->setDisplayMode(MainForm::showRegister);
    mf->update();
}

static void aboutActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);
    assert(MainForm::showAbout!=mf->displayMode());
    mf->setDisplayMode(MainForm::showAbout);
    mf->update();
}

static void randomArticleActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);
    assert(MainForm::showTutorial==mf->displayMode());
    sendEvent(iPediaApplication::appRandomWord);
}

Definition& MainForm::currentDefinition()
{
    switch( displayMode() )
    {
        case showArticle:
            return article_;
        case showAbout:
            return about_;
        case showRegister:
            return register_;
        case showTutorial:
            return tutorial_;
        case showWikipedia:
            return wikipedia_;
        default:
            // shouldn't happen
            assert(0);
            break;
    }
    return about_;
}

void MainForm::prepareAbout()
{
    Definition::Elements_t elems;
    FormattedTextElement* text;

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(new LineBreakElement(1,10));

    elems.push_back(text=new FormattedTextElement("ArsLexis iPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setStyle(styleHeader);
    text->setEffects(fxBold);

    elems.push_back(new LineBreakElement(1,3));

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
    elems.push_back(new LineBreakElement(1,4));

#ifdef UNLOCKED
    elems.push_back(text=new FormattedTextElement("Registered PalmSource version"));
    text->setJustification(DefinitionElement::justifyCenter);
    elems.push_back(new LineBreakElement(1,2));
#else
    if (app().preferences().regCode.empty())
    {
        elems.push_back(text=new FormattedTextElement("Unregistered ("));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(text=new FormattedTextElement("how to register"));
        text->setJustification(DefinitionElement::justifyCenter);
        // url doesn't really matter, it's only to establish a hotspot
        text->setHyperlink("", hyperlinkTerm);
        text->setActionCallback( unregisteredActionCallback, static_cast<void*>(this) );
        elems.push_back(text=new FormattedTextElement(")"));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(new LineBreakElement(1,2));
    }
    else
    {
        elems.push_back(text=new FormattedTextElement("Registered"));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(new LineBreakElement(1,2));
    }
#endif

    elems.push_back(text=new FormattedTextElement("Software \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new FormattedTextElement("ArsLexis"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);

    elems.push_back(new LineBreakElement(1,4));
    elems.push_back(text=new FormattedTextElement("Data \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new FormattedTextElement("WikiPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(wikipediaActionCallback, static_cast<void*>(this) );

    elems.push_back(new LineBreakElement(1,2));

    elems.push_back(articleCountElement_=new FormattedTextElement(" "));
    if (-1!=articleCountSet_)    
    {
        updateArticleCountEl(articleCountSet_,app().preferences().databaseTime);
    }
    articleCountElement_->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(new LineBreakElement(1, 2));
    elems.push_back(text=new FormattedTextElement("Using iPedia: "));
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new FormattedTextElement("tutorial"));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( tutorialActionCallback, static_cast<void*>(this) );

    about_.replaceElements(elems);    
}

// TODO: make those on-demand only to save memory
void MainForm::prepareTutorial()
{
    tutorial_.setInteractionBehavior(
            Definition::behavDoubleClickSelection | Definition::behavMouseSelection | 
            Definition::behavUpDownScroll | Definition::behavHyperlinkNavigation
        );
    Definition::Elements_t elems;
    FormattedTextElement* text;

    assert( tutorial_.empty() );

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new FormattedTextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( aboutActionCallback, static_cast<void*>(this) );
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("iPedia is a wireless encyclopedia. Use it to get information and facts on just about anything."));
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Finding an encyclopedia article."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" Let's assume you want to read an encyclopedia article on Seattle. Enter 'Seattle' in the text field at the bottom of the screen and press 'Search' (or center button on Treo's 5-way navigator)."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Finding all articles with a given word."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" Let's assume you want to find all articles that mention Seattle. Enter 'Seattle' in the text field and use 'Main/Extended search' menu item. In response you'll receive a list of articles that contain word 'Seattle'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Refining the search."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" If there are too many results, you can refine (narrow) the search results by adding additional terms e.g. type 'museum' and press 'Refine' button. You'll get a smaller list of articles that contain both 'Seattle' and 'museum'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Results of last extended search."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" At any time you can get a list of results from last extended search by using menu item 'Main/Extended search results'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Random article."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" You can use menu 'Main/Random article' (or "));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(text=new FormattedTextElement("click here"));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( randomArticleActionCallback, static_cast<void*>(this) );
    elems.push_back(text=new FormattedTextElement(") to get a random article."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("More information."));
    text->setEffects(fxBold);
    elems.push_back(text=new FormattedTextElement(" Please visit our website "));
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new FormattedTextElement("arslexis.com"));
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new FormattedTextElement(" for more information about iPedia."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new FormattedTextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( aboutActionCallback, static_cast<void*>(this) );

    tutorial_.replaceElements(elems);
}

static void registerActionCallback(void *data)
{
    assert(NULL!=data);
    MainForm * mf = static_cast<MainForm*>(data);   
    sendEvent(iPediaApplication::appRegisterEvent);
}

// TODO: make those on-demand only to save memory
void MainForm::prepareHowToRegister()
{
    Definition::Elements_t elems;
    FormattedTextElement* text;

    assert( register_.empty() );

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new FormattedTextElement("Unregistered version of iPedia limits how many articles can be viewed in one day (there are no limits on random articles.)"));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new FormattedTextElement("In order to register iPedia you need to purchase registration code at "));

// those 3 #defines should be mutually exclusive
#ifdef PALMGEAR
    elems.push_back(text=new FormattedTextElement("palmgear.com?67708"));
#endif

#ifdef HANDANGO
    elems.push_back(text=new FormattedTextElement("handango.com/purchase, product id: 128991"));
#endif

#ifdef ARSLEXIS_VERSION
    elems.push_back(text=new FormattedTextElement("our website "));
    elems.push_back(text=new FormattedTextElement("http://www.arslexis.com"));
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);
#endif
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new FormattedTextElement("After obtaining registration code use menu item 'Options/Register' (or "));
    elems.push_back(text=new FormattedTextElement("click here"));
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( registerActionCallback, static_cast<void*>(this) );
    elems.push_back(text=new FormattedTextElement(") to enter registration code. "));

    elems.push_back(text=new FormattedTextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( aboutActionCallback, static_cast<void*>(this) );

    register_.replaceElements(elems);
}

void MainForm::prepareWikipedia()
{
    Definition::Elements_t elems;
    FormattedTextElement* text;

    assert( wikipedia_.empty() );

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new FormattedTextElement("All the articles in iPedia come from WikiPedia project and are licensed under "));
    elems.push_back(text=new FormattedTextElement("GNU Free Documentation License"));
    text->setHyperlink("http://www.gnu.org/copyleft/fdl.html", hyperlinkExternal);
    elems.push_back(text=new FormattedTextElement("."));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new FormattedTextElement("To find out more about WikiPedia project, visit "));
    elems.push_back(text=new FormattedTextElement("wikipedia.org"));
    text->setHyperlink("http://www.wikipedia.org", hyperlinkExternal);
    elems.push_back(text=new FormattedTextElement(" website. "));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new FormattedTextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( aboutActionCallback, static_cast<void*>(this) );

    wikipedia_.replaceElements(elems);
}    
