#include "MainForm.hpp"
#include "DefinitionParser.hpp"
#include "iPediaApplication.hpp"
#include "iPediaConnection.hpp"
#include "SocketAddress.hpp"

void MainForm::resize(const RectangleType& screenBounds)
{
    setBounds(screenBounds);

    RectangleType bounds;
    UInt16 index=getObjectIndex(definitionScrollBar);
    getObjectBounds(index, bounds);
    bounds.topLeft.x=screenBounds.extent.x-8;
    bounds.extent.y=screenBounds.extent.y-36;
    setObjectBounds(index, bounds);
    
    index=getObjectIndex(termLabel);
    getObjectBounds(index, bounds);
    bounds.topLeft.y=screenBounds.extent.y-14;
    setObjectBounds(index, bounds);

    index=getObjectIndex(termInputField);
    getObjectBounds(index, bounds);
    bounds.topLeft.y=screenBounds.extent.y-14;
    bounds.extent.x=screenBounds.extent.x-60;
    setObjectBounds(index, bounds);

    index=getObjectIndex(goButton);
    getObjectBounds(index, bounds);
    bounds.topLeft.x=screenBounds.extent.x-26;
    bounds.topLeft.y=screenBounds.extent.y-14;
    setObjectBounds(index, bounds);

    update();    
}

void MainForm::draw(UInt16 updateCode)
{
    iPediaForm::draw(updateCode);
    ArsLexis::Rectangle rect=bounds();
    WinPaintLine(rect.x(), rect.height()-18, rect.width(), rect.height()-18);

    rect.explode(2, 18, -12, -36);

    const iPediaApplication& app=static_cast<iPediaApplication&>(application());
    definition_.render(rect, app.renderingPreferences());
    
    UInt16 index=getObjectIndex(definitionScrollBar);
    ScrollBarType* scrollBar=static_cast<ScrollBarType*>(FrmGetObjectPtr(*this, index));
    SclSetScrollBar(scrollBar, definition_.firstShownLine(), 0, definition_.totalLinesCount()-definition_.shownLinesCount(), definition_.shownLinesCount());
}


Err MainForm::initialize()
{
    Err error=iPediaForm::initialize();
    if (!error)
    {
        iPediaApplication& app=static_cast<iPediaApplication&>(application());
        definition_.setHyperlinkHandler(&app.hyperlinkHandler());
    }
    return error;
}

inline void MainForm::handleScrollRepeat(const sclRepeat& data)
{
    definition_.scroll(data.newValue-data.value);
}

void MainForm::handlePenUp(const EventType& event)
{
    PointType point;
    point.x=event.screenX;
    point.y=event.screenY;
    if (definition_.bounds() && point)
        definition_.hitTest(point); 
}

void MainForm::handleControlSelect(const ctlSelect& data)
{
    assert(data.controlID==goButton);
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    using namespace ArsLexis;
    SocketConnectionManager* manager=0;
    Err error=app.getConnectionManager(manager);
    if (!error)
    {
        Resolver* resolver=0;
        error=app.getResolver(resolver);
        assert(manager);
        assert(resolver);
        iPediaConnection* conn=new iPediaConnection(*manager);
        conn->setTransferTimeout(app.ticksPerSecond()*15L);
        conn->setTerm("Science fiction");
        resolver->resolveAndConnect(conn, "localhost:9000");
    }
}


Boolean MainForm::handleEvent(EventType& event)
{
    Boolean handled=false;
    switch (event.eType)
    {
        case ctlSelectEvent:
            handleControlSelect(event.data.ctlSelect);
            break;
        
        case penUpEvent:
            handlePenUp(event);
            break;
            
        case sclRepeatEvent:
            handleScrollRepeat(event.data.sclRepeat);
            break;
    
        default:
            handled=iPediaForm::handleEvent(event);
    }
    return handled;
}