/**
 * @file Definition.cpp
 * Implementation of class @c Definition.
 *
 * @author Andrzej Ciarkowski (a.ciarkowski@interia.pl)
 */
#include "Definition.hpp"
#include "DefinitionElement.hpp"
#include "Utility.hpp"
#include "GenericTextElement.hpp"

using ArsLexis::Point;
using ArsLexis::ObjectDeleter;
using ArsLexis::Graphics;

Definition::HotSpot::HotSpot(const ArsLexis::Rectangle& rect, DefinitionElement& element):
    element_(element)
{
    rectangles_.push_back(rect);
}

bool Definition::HotSpot::hitTest(const Point& point) const
{
    bool result=false;
    Rectangles_t::const_iterator it=std::find_if(rectangles_.begin(), rectangles_.end(), ArsLexis::Rectangle::HitTest(point));
    if (it!=rectangles_.end())
        result=true;
    return result;
}

Definition::HotSpot::~HotSpot()
{
    element_.invalidateHotSpot();
}

void Definition::HotSpot::move(const Point& delta, const ArsLexis::Rectangle& validArea)
{
    Rectangles_t::iterator end=rectangles_.end();
    Rectangles_t::iterator it=rectangles_.begin();
    while (it!=end)
    {
        ArsLexis::Rectangle& rect=*it;
        rect+=delta;
        Rectangles_t::iterator next=it;
        ++next;
        if (!(validArea && rect))
            rectangles_.erase(it);
        it=next;
    }
}

Definition::Definition():
    firstLine_(0),
    lastLine_(0),
    hyperlinkHandler_(0)
{}

void Definition::addHotSpot(HotSpot* hotSpot)
{
    hotSpots_.push_front(hotSpot);
}

void Definition::clearHotSpots()
{
    std::for_each(hotSpots_.begin(), hotSpots_.end(), ObjectDeleter<HotSpot>());
    hotSpots_.clear();
}

void Definition::clearLines()
{
    lines_.clear();
    Lines_t tmp;
    lines_.swap(tmp); // Reclaim some memory...
    firstLine_=lastLine_=0;
}

void Definition::clear()
{
    clearHotSpots();
    clearLines();
    std::for_each(elements_.begin(), elements_.end(), ObjectDeleter<DefinitionElement>());
    elements_.clear();
    bounds_.clear();
}

Definition::~Definition()
{
    clear();
}

void Definition::calculateVisibleRange(uint_t& firstLine, uint_t& lastLine, int delta)
{
    if (!lines_.empty())
    {
        uint_t linesCount=lines_.size();
        
        int newFirstLine=firstLine_+delta;
        if (newFirstLine<0)
            newFirstLine=0;
        else if (newFirstLine>=linesCount)
            newFirstLine=linesCount-1;

        uint_t height=0;
        int newLastLine=0;
        for (int lineIndex=newFirstLine; lineIndex<linesCount; ++lineIndex)
        {
            height+=lines_[lineIndex].height;
            if (height>bounds_.height())
            {
                newLastLine=lineIndex;
                break;
            }
        }
        if (!newLastLine)
        {
            newLastLine=linesCount;
            for (int lineIndex=newFirstLine-1; lineIndex>=0; --lineIndex)
            {
                height+=lines_[lineIndex].height;
                if (height<bounds_.height())
                    --newFirstLine;
                else 
                    break;
            }
        }
        firstLine=newFirstLine;
        lastLine=newLastLine;   
    }
    else
        firstLine=lastLine=0;
}

void Definition::moveHotSpots(const Point& delta)
{
    HotSpots_t::iterator end=hotSpots_.end();
    HotSpots_t::iterator it=hotSpots_.begin();
    while (it!=end)
    {
        (*it)->move(delta, bounds_);
        HotSpots_t::iterator next=it;
        ++next;
        if (!(*it)->valid())
        {
            delete *it;
            hotSpots_.erase(it);
        }
        it=next;
    }
}


void Definition::scroll(Graphics& graphics, const RenderingPreferences& prefs, int delta)
{
    uint_t newFirstLine=0;
    uint_t newLastLine=0;
    calculateVisibleRange(newFirstLine, newLastLine, delta);

    uint_t unionFirst=std::max(firstLine_, newFirstLine);
    uint_t unionLast=std::min(lastLine_, newLastLine);
    if (unionFirst<unionLast)
    {
        uint_t unionTop=0;
        {
            for (uint_t index=firstLine_; index<unionFirst; ++index)
                unionTop+=lines_[index].height;
        }
        uint_t unionHeight=0;
        for (uint_t index=unionFirst; index<unionLast; ++index)
            unionHeight+=lines_[index].height;

        ArsLexis::Rectangle unionRect(bounds_.x(), bounds_.y()+unionTop, bounds_.width(), unionHeight);
        Point pointDelta;
        
        Graphics::ColorSetter setBackground(graphics, Graphics::colorBackground, prefs.backgroundColor());
        
        if (delta>0) 
        {
            pointDelta.y=-unionTop;
            graphics.copyArea(unionRect, bounds_.topLeft);
            graphics.erase(ArsLexis::Rectangle(bounds_.x(), bounds_.y()+unionHeight, bounds_.width(), bounds_.height()-unionHeight));
            moveHotSpots(pointDelta);
            renderLineRange(graphics, prefs, lines_.begin()+unionLast, lines_.begin()+newLastLine, unionHeight);
        }
        else
        {
            pointDelta.y=0;
            for (uint_t index=newFirstLine; index<firstLine_; ++index)
                pointDelta.y+=lines_[index].height;
                
            graphics.copyArea(unionRect, bounds_.topLeft + pointDelta);
            graphics.erase(ArsLexis::Rectangle(bounds_.x(), bounds_.y()+unionHeight+pointDelta.y, bounds_.width(), bounds_.height()-unionHeight-pointDelta.y));
            
            moveHotSpots(pointDelta);
            renderLineRange(graphics, prefs, lines_.begin()+newFirstLine, lines_.begin()+unionFirst, 0);
        }
        firstLine_=newFirstLine;
        lastLine_=newLastLine;
    }
    else
    {
        clearHotSpots();
        firstLine_=newFirstLine;
        lastLine_=newLastLine;
        renderLayout(graphics, prefs);
    }
}

void Definition::renderLine(RenderingContext& renderContext, const LinePosition_t& line)
{
    renderContext.usedWidth=0;
    renderContext.usedHeight=line->height;
    
    renderContext.graphics.erase(ArsLexis::Rectangle(bounds_.x(), renderContext.top, bounds_.width(), renderContext.usedHeight));
    
    renderContext.baseLine=line->baseLine;
    renderContext.renderingProgress=line->renderingProgress;
    ElementPosition_t last=elements_.end();
    ElementPosition_t current=line->firstElement;
    bool lineFinished=false;    
    while (!lineFinished && current!=last)
    {
        (*current)->render(renderContext);
        if (renderContext.isElementCompleted())
        {
            ++current;
            renderContext.renderingProgress=0;
            if (renderContext.availableWidth()==0 || current==last || (*current)->requiresNewLine(renderContext.preferences))
                lineFinished=true;
        }
        else
            lineFinished=true;
    }
    renderContext.top+=renderContext.usedHeight;
}

void Definition::renderLineRange(Graphics& graphics, const RenderingPreferences& prefs, const Definition::LinePosition_t& begin, const Definition::LinePosition_t& end, uint_t topOffset)
{
    RenderingContext renderContext(graphics, prefs, *this, bounds_.x(), bounds_.y()+topOffset, bounds_.width());
    for (Lines_t::iterator line=begin; line!=end; ++line)
        renderLine(renderContext, line);
}

void Definition::calculateLayout(Graphics& graphics, const RenderingPreferences& prefs, const ElementPosition_t& firstElement, uint_t renderingProgress)
{
    uint_t topOffset=0;
    ElementPosition_t end(elements_.end());
    ElementPosition_t element(elements_.begin());
    LayoutContext layoutContext(graphics, prefs, bounds_.width());
    LineHeader lastLine;
    lastLine.firstElement=element;
    while (element!=end)
    {
        uint_t progressBefore=layoutContext.renderingProgress;
        (*element)->calculateLayout(layoutContext);
        
        if (element==firstElement && progressBefore<=renderingProgress && layoutContext.renderingProgress>renderingProgress)
            firstLine_=lines_.size();
        
        bool startNewLine=false;    
        if (layoutContext.isElementCompleted())
        {
            ++element;
            layoutContext.renderingProgress=0;
            layoutContext.nextTextElement=0;
            if (element!=end)
            {   
                ElementPosition_t next(element);
                ++next;
                if (next!=end && (*next)->isTextElement())
                    layoutContext.nextTextElement=static_cast<GenericTextElement*>(*next);
            }
            if (layoutContext.availableWidth()==0 || element==end || (*element)->requiresNewLine(prefs))
                startNewLine=true;
        }
        else
            startNewLine=true;
            
        if (startNewLine)
        {
            lastLine.height=layoutContext.usedHeight;
            lastLine.baseLine=layoutContext.baseLine;
            topOffset+=lastLine.height;
            lines_.push_back(lastLine);
            layoutContext.startNewLine();
            lastLine.firstElement=element;
            lastLine.renderingProgress=layoutContext.renderingProgress;
        }
    }
    calculateVisibleRange(firstLine_, lastLine_);
}

void Definition::render(Graphics& graphics, const ArsLexis::Rectangle& bounds, const RenderingPreferences& prefs, bool forceRecalculate)
{
    if (bounds.width()!=bounds_.width() || forceRecalculate)
    {
        ElementPosition_t firstElement=elements_.begin(); // This will be used in calculating first line we should show.
        uint_t renderingProgress=0;
        if (firstLine_!=0) // If there's actually some first line set, use it - it's position won't change if window width remains the same.
        {
            firstElement=lines_[firstLine_].firstElement;  // Store first element and its progress so that we'll restore it as our firstLine_ if we need to recalculate.
            renderingProgress=lines_[firstLine_].renderingProgress;
        }
        clearHotSpots();
        clearLines();
        bounds_=bounds;
        calculateLayout(graphics, prefs, firstElement, renderingProgress);
    }
    else {
        clearHotSpots();
        bool heightChanged=(bounds_.height()!=bounds.height());
        bounds_=bounds;
        if (heightChanged)
            calculateVisibleRange(firstLine_, lastLine_);
    }
    renderLayout(graphics, prefs);
}
 
void Definition::swap(Definition& other)
{
    elements_.swap(other.elements_);
    lines_.swap(other.lines_);
    std::swap(firstLine_, other.firstLine_);
    std::swap(lastLine_, other.lastLine_);
    std::swap(bounds_, other.bounds_);
    hotSpots_.swap(other.hotSpots_);
    std::swap(hyperlinkHandler_, other.hyperlinkHandler_);
}

void Definition::appendElement(DefinitionElement* element)
{
    elements_.push_back(element);
}

void Definition::hitTest(const Point& point)
{
    HotSpots_t::iterator end=hotSpots_.end();
    for (HotSpots_t::iterator it=hotSpots_.begin(); it!=end; ++it)
    {
        if ((*it)->hitTest(point))
        {
            (*it)->element().performAction(*this);
            break;
        }
    }
}

void Definition::renderLayout(Graphics& graphics, const RenderingPreferences& prefs)
{
    Graphics::ColorSetter setBackground(graphics, Graphics::colorBackground, prefs.backgroundColor());
    renderLineRange(graphics, prefs, lines_.begin()+firstLine_, lines_.begin()+lastLine_, 0);
    uint_t rangeHeight=0;
    for (uint_t i=firstLine_; i<lastLine_; ++i)
        rangeHeight+=lines_[i].height;
    graphics.erase(ArsLexis::Rectangle(bounds_.x(), bounds_.y()+rangeHeight, bounds_.width(), bounds_.height()-rangeHeight));        
}

void Definition::selectionToText(ArsLexis::String& out) const
{
    Elements_t::const_iterator end=elements_.end();
    for (Elements_t::const_iterator it=elements_.begin(); it!=end; ++it)
        (*it)->toText(out);
}
