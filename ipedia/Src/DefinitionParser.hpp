#ifndef __DEFINITION_PARSER_HPP__
#define __DEFINITION_PARSER_HPP__

#include "Debug.hpp"
#include "RenderingPreferences.hpp"
#include "Definition.hpp"
#include "HTMLCharacterEntityReferenceDecoder.hpp"
#include <list>
#include <vector>

class Definition;

class DefinitionElement;

class GenericTextElement;

class FormattedTextElement;

class ListNumberElement;

/**
 * Transforms textual definition representation into Definition object.
 * Parser should be initiaited with reference to @c String that acts as a response
 * buffer. After each update to buffer's content @c parseIncrement() should be called.
 * When all data is received @c parseIncrement(true) should be called to parse all the
 * remeining lines.
 */
class DefinitionParser
{
    bool openEmphasize_;
    bool openStrong_;
    bool openVeryStrong_;
    uint_t openTypewriter_;
    uint_t openSmall_;
    uint_t openStrikeout_;
    uint_t openUnderline_;
    uint_t openNowiki_;
    uint_t openSuperscript_;
    uint_t openSubscript_;
    
    void reset();
    
    bool isPlainText() const;
    
    /**
     * @internal
     * Transforms current settings in open* variables into settings of @c FormattedTextElement.
     */
    void applyCurrentFormatting(FormattedTextElement* element);
    
    typedef std::list<DefinitionElement*> ParentsStack_t;
    ParentsStack_t parentsStack_;
    
    DefinitionElement* currentParent();
    
    void pushParent(DefinitionElement* parent);
    
    void popParent();
    
    void popAvailableParent();

    /**
     * @internal
     * Holds text that specifies what was nesting level of last parsed list element 
     * in the standard form (the "*#" texts). This way we know whether currently
     * parsed list element is continuation of previous list or start of a new one.
     * Therefore this variable should be cleared when we get outside of any list.
     */
    ArsLexis::String lastListNesting_;

    /**
     * @internal
     * For purpose of setting ListNumberElement's totalCount member we need collection
     * that has cheap size() implementation, and list typically doesn't. 
     */
    typedef std::vector<ListNumberElement*> NumberedList_t;
    typedef std::list<NumberedList_t> NumberedListsStack_t;
    
    /**
     * @internal
     * 
     */
    NumberedListsStack_t numListsStack_;
    NumberedList_t currentNumberedList_;
    
    /**
     * @internal 
     * Pushes on stack current numbered list (if there is one) and starts a new one 
     * with @c firstElement.
     */
    void startNewNumberedList(ListNumberElement* firstElement);
    
    /**
     * @internal 
     * Sets totalCount of elements of current numbered list, and pops previous one
     * in its place from the stack (if there is one).
     */
    void finishCurrentNumberedList();

    /**
     * @internal 
     * Compares @c lastListNesting_ with @c newNesting and finishes/creates all
     * lists that stand in a way from previous to current one (this involves 
     * popping/pushing parents from/to parents stack). Creates appropriate
     * ListNumberElement or BulletElement afterwards and pushes it as current parent
     * (if newNesting isn't empty, which means that we want simply to finish all currently
     * opened lists and parse non-list element.
     */
    void manageListNesting(const ArsLexis::String& newNesting);
    
    Definition definition_;
    const ArsLexis::String& text_;
    uint_t parsePosition_;
    uint_t lineEnd_;
    uint_t lastElementStart_;
    uint_t lastElementEnd_;
    uint_t unnamedLinksCount_;
    
    void parseText(uint_t end, ElementStyle style);
    
    void parse();
    
    ArsLexis::HTMLCharacterEntityReferenceDecoder decoder_;

    void decodeHTMLCharacterEntityRefs(ArsLexis::String& text) const;
    
    void appendElement(DefinitionElement* element);
    
    enum LineType
    {
        emptyLine,
        headerLine,
        listElementLine,
        textLine,
        horizontalBreakLine,
        definitionListLine
    };
    
    LineType lineType_;
    LineType previousLineType_;

    ElementStyle currentStyle_;
    
    static bool lineAllowsContinuation(LineType lineType)
    {
        return textLine==lineType;
    }

    void parseHeaderLine();
    
    void parseDefinitionListLine();
    
    void parseTextLine();
    
    void parseListElementLine();
    
    bool detectNextLine(uint_t end, bool finish);
    
    bool detectHTMLTag(uint_t textEnd);
    
    bool detectStrongTag(uint_t textEnd);
    
    bool detectHyperlink(uint_t textEnd);
    
    GenericTextElement* createTextElement();
    
public:

    DefinitionParser(const ArsLexis::String& text, uint_t initialOffset=0);

    void parseIncrement(uint_t end, bool finish=false);
    
    void updateDefinition(Definition& definition);
    
    ~DefinitionParser();

};

#endif