#ifndef __LINE_BREAK_ELEMENT_HPP__
#define __LINE_BREAK_ELEMENT_HPP__

#include "DefinitionElement.hpp"

class LineBreakElement: public DefinitionElement
{
    void calculateOrRender(LayoutContext& layoutContext, bool render=false);

public:
    
    bool requiresNewLine(const RenderingPreferences& preferences) const
    {return true;}

    void calculateLayout(LayoutContext& mc)
    {calculateOrRender(mc);}
    
    void render(RenderingContext& rc)
    {calculateOrRender(rc, true);}

    void toText(ArsLexis::String& appendTo, uint_t from, uint_t to) const
    {
        appendTo.append(1, '\n');
    }

};

#endif