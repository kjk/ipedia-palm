#include <PalmOS.h>
#include "Graphics.hpp"

namespace ArsLexis
{
    Graphics::Graphics(const NativeGraphicsHandle_t& handle):
        handle_(handle)
    {
        support_.font.setFontId(FntGetFont());
    }

    Graphics::Font_t Graphics::setFont(const Graphics::Font_t& font)
    {
        Font_t oldOne=support_.font;
        support_.font=font;
        FntSetFont(support_.font.withEffects());
        return oldOne;
    }

    Graphics::State_t Graphics::pushState()
    {
        WinPushDrawState();
        return support_.font;
    }

    void Graphics::popState(const Graphics::State_t& state)
    {
        setFont(state);
        WinPopDrawState();
    }
    
    class PalmUnderlineSetter
    {
        UnderlineModeType originalUnderline_;
    public:
        
        explicit PalmUnderlineSetter(UnderlineModeType newMode):
            originalUnderline_(WinSetUnderlineMode(newMode))
        {}
        
        ~PalmUnderlineSetter()
        {WinSetUnderlineMode(originalUnderline_);}
        
    };
    
    inline static UnderlineModeType convertUnderlineMode(FontEffects::Underline underline)
    {
        UnderlineModeType result=noUnderline;
        switch (underline)
        {
            case FontEffects::underlineDotted:
                result=grayUnderline;
                break;
            case FontEffects::underlineSolid:
                result=solidUnderline;
                break;
        }
        return result;                
    }
            
    
    void Graphics::drawText(const char_t* text, uint_t length, const Point& topLeft)
    {
        PalmUnderlineSetter setUnderline(convertUnderlineMode(support_.font.effects().underline()));
        
        uint_t height=fontHeight();
        uint_t top=topLeft.y;
        if (support_.font.effects().subscript())
            top+=(height*0.333);
        WinDrawChars(text, length, topLeft.x, top);
        if (support_.font.effects().strikeOut())
        {
            uint_t baseline=fontBaseline();
            top=topLeft.y+baseline/2;
            uint_t width=FntCharsWidth(text, length);
            drawLine(topLeft.x, top, topLeft.x+width, top);
        }
    }
    

}