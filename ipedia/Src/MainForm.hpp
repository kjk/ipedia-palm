#ifndef __MAINFORM_HPP__
#define __MAINFORM_HPP__

#include <Logging.hpp>

#include "iPediaForm.hpp"
#include <TextRenderer.hpp>
#include "iPediaApplication.hpp"

class LookupHistory;
class RenderingPreferences;


class MainForm: public iPediaForm
{

    ArsLexis::FormObject graffiti_;
    ArsLexis::Field termInputField_;
    ArsLexis::ScrollBar scrollBar_;
    ArsLexis::Control backButton_;
    ArsLexis::Control forwardButton_;
    ArsLexis::Control searchButton_;

    ArsLexis::TextRenderer articleRenderer_;
    ArsLexis::TextRenderer infoRenderer_;

    long articleCountSet_;
    int  penUpsToEat_;
    bool ignoreEvents_;

    int showStringListForm(char_t* strList[], int strListSize);

    const LookupHistory& getHistory() const;
    
    const RenderingPreferences& renderingPreferences() const
    {
        return static_cast<const iPediaApplication&>(application()).renderingPreferences();
    }
    
    void handleControlSelect(const EventType& data);
    
    bool handleKeyPress(const EventType& event);
    
    void randomArticle();
    
    void copySelectionToClipboard();

    void updateAfterLookup();
    
    void moveHistory(bool forward);
    
    void switchServer(const char* server);
    
    void setControlsState(bool enabled);
    
    void handleToggleStressMode();
    
    void search(bool fullText=false);
    
    void handlePenDown(const EventType& event);
    
    void handleLookupFinished(const EventType& event);
    
    void updateNavigationButtons();
    
    class RenderingProgressReporter: public Definition::RenderingProgressReporter
    {
        MainForm& form_;
        UInt32 ticksAtStart_;
        uint_t lastPercent_;
        bool showProgress_:1;
        bool afterTrigger_:1;
        ArsLexis::String waitText_;
        
    public:
        
        RenderingProgressReporter(MainForm& form);
        
        virtual void reportProgress(uint_t percent);

    };
    
    friend class RenderingProgressReporter;
    
    RenderingProgressReporter renderingProgressReporter_;
    
    void prepareAbout();

    void doLookupSelectedTerm(int sel);

    void doHistory();

    void doLinkedArticles();

    void doLinkingArticles();

    void changeDatabase();

    void doDbSelected(int sel);

protected:

    mutable ArsLexis::ChildLogger log_;

    ArsLexis::Logger& log() const
    {return log_;}

    void resize(const ArsLexis::Rectangle& screenBounds);
    
    void draw(UInt16 updateCode = frmRedrawUpdateCode);
    
    bool handleWindowEnter(const struct _WinEnterEventType& data);
    
    bool handleEvent(EventType& event);
    
    bool handleMenuCommand(UInt16 itemId);
    
    bool handleOpen();
    
    void attachControls();
    
public:

    MainForm(iPediaApplication& app);
    
    enum DisplayMode
    {
        showAbout,
        showTutorial,
        showRegister,
        showArticle,
        showWikipedia
    };
    
    DisplayMode displayMode() const {return displayMode_;}

    void setDisplayMode(DisplayMode displayMode);

    void setUpdateDefinitionOnEntry(bool val = true) {updateDefinitionOnEntry_=val;}

    void prepareTutorial();    

    void prepareHowToRegister();

    void prepareWikipedia();

    iPediaApplication& app() { return static_cast<iPediaApplication&>(application()); }

private:
    
    UInt32      lastPenDownTimestamp_;
    DisplayMode displayMode_;
    bool        updateDefinitionOnEntry_;
    bool        enableInputFieldAfterUpdate_;
    
};

#endif
