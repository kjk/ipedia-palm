#ifndef __SEARCH_RESULTS_FORM_HPP__
#define __SEARCH_RESULTS_FORM_HPP__

#include "iPediaForm.hpp"
#include <vector>

class SearchResultsForm: public iPediaForm
{
    String listPositionsString_;

    std::vector<const char*> listPositions_;

    void updateSearchResults();

    void handleControlSelect(const EventType& data);

    void setControlsState(bool enabled);

    void handleListSelect(const EventType& event);

    void refineSearch();

    bool handleKeyPress(const EventType& event);

    void handleLookupFinished(const EventType& event);

protected:

    bool handleEvent(EventType& event);

    bool handleOpen();

    void resize(const ArsRectangle& screenBounds);

    bool handleMenuCommand(UInt16 menuItem);

    bool handleWindowEnter(const struct _WinEnterEventType& data);

    void draw(UInt16 updateCode);

public:

    explicit SearchResultsForm(iPediaApplication& app);
    
    ~SearchResultsForm();
    
};

#endif