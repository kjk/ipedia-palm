#ifndef __RENDERING_PREFERENCES_HPP__
#define __RENDERING_PREFERENCES_HPP__

#include "Debug.hpp"

enum HyperlinkType
{
    hyperlinkBookmark,
    hyperlinkTerm,
    hyperlinkExternal
};

enum ElementStyle
{
    styleDefault,
    styleHeader
};

class RenderingPreferences
{
    
public:

    enum BulletType 
    {
        bulletCircle,
        bulletDiamond
    };
    
    RenderingPreferences();

    /**
     * @return @c true if layout changed and we need to recalculate it.
     * @todo Implement RenderingPreferences::synchronize()
     */
    Boolean synchronize(const RenderingPreferences& preferences)
    {return false;}
    
    BulletType bulletType() const
    {return bulletCircle;}

    struct HyperlinkDecoration
    {
        UnderlineModeType underlineMode;
        IndexedColorType textColor;
        
        HyperlinkDecoration():
            underlineMode(grayUnderline),
            textColor(UIColorGetTableEntryIndex(UIObjectForeground))
        {}
        
        HyperlinkDecoration(UnderlineModeType um, IndexedColorType tc):
            underlineMode(um),
            textColor(tc)
        {}
    };
    
    const HyperlinkDecoration& hyperlinkDecoration(HyperlinkType hyperlinkType) const
    {
        assert(hyperlinkType<3);
        return hyperlinkDecorations_[hyperlinkType];
    }
    
    struct StyleFormatting
    {
        FontID fontId;
        IndexedColorType textColor;
        
        StyleFormatting():
            fontId(stdFont),
            textColor(UIColorGetTableEntryIndex(UIObjectForeground))
        {}
        
    };
    
    const StyleFormatting& styleFormatting(ElementStyle style) const
    {
        assert(style<2);
        return styles_[style];
    }
    
    UInt16 standardIndentation() const
    {return 20;}
    
    UnderlineModeType standardUnderline() const
    {return solidUnderline;}

private:
    
    HyperlinkDecoration hyperlinkDecorations_[3];
    StyleFormatting styles_[2];
};



#endif