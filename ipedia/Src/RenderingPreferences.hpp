#ifndef __RENDERING_PREFERENCES_HPP__
#define __RENDERING_PREFERENCES_HPP__

#include <Debug.hpp>
#include <BaseTypes.hpp>
#include <Graphics.hpp>

enum HyperlinkType
{
    hyperlinkBookmark,
    hyperlinkTerm,
    hyperlinkExternal,
    hyperlinkUrl,
    hyperlinkDefault = hyperlinkBookmark
};

enum ElementStyle
{
    styleDefault,
    styleHeader
};

class PrefsStoreReader;
class PrefsStoreWriter;

class RenderingPreferences
{

    enum {
        stylesCount_=2,
        hyperlinkTypesCount_=3,
    };        
    
    uint_t standardIndentation_;
    uint_t bulletIndentation_;
    
    void calculateIndentation();
    
public:

    RenderingPreferences();
    
    enum SynchronizationResult 
    {
        noChange,
        repaint,
        recalculateLayout
    };

    /**
     * @todo Implement RenderingPreferences::synchronize()
     */
    SynchronizationResult synchronize(const RenderingPreferences&)
    {return noChange;}
    
    struct StyleFormatting
    {
        Font font;
        Color textColor;
        
        StyleFormatting():
            textColor(1)
        {}
        
        enum {reservedPrefIdCount=3};
        Err serializeOut(PrefsStoreWriter& writer, int uniqueId) const;
        Err serializeIn(PrefsStoreReader& reader, int uniqueId);
        
    };
    
    const StyleFormatting& hyperlinkDecoration(HyperlinkType hyperlinkType) const
    {
        assert(hyperlinkType<hyperlinkTypesCount_);
        return hyperlinkDecorations_[hyperlinkType];
    }
    
    const StyleFormatting& styleFormatting(ElementStyle style) const
    {
        assert(style<stylesCount_);
        return styles_[style];
    }
    
    uint_t standardIndentation() const
    {return standardIndentation_;}
    
    uint_t bulletIndentation() const
    {return bulletIndentation_;}

    void setBulletIndentation(uint_t bulletIndentation)
    {bulletIndentation_=bulletIndentation;}

    Color backgroundColor() const
    {return backgroundColor_;}
    
    void setBackgroundColor(Color color)
    {backgroundColor_=color;}
    
    enum {reservedPrefIdCount=2+(hyperlinkTypesCount_+stylesCount_)*StyleFormatting::reservedPrefIdCount};
    Err serializeOut(PrefsStoreWriter& writer, int uniqueId) const;
    Err serializeIn(PrefsStoreReader& reader, int uniqueId);

private:
    
    Color backgroundColor_;
    StyleFormatting hyperlinkDecorations_[hyperlinkTypesCount_];
    StyleFormatting styles_[stylesCount_];
};



#endif