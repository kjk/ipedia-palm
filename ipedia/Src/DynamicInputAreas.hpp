/**
 * @file DynamicInputAreas.hpp
 * Generic interface to DynamicInputAreas features present on some new PalmOS 5 devices.
 * @author Andrzej Ciarkowski (a.ciarkowski@interia.pl)
 */
#ifndef __ARSLEXIS_DYNAMIC_INPUT_AREAS_HPP__
#define __ARSLEXIS_DYNAMIC_INPUT_AREAS_HPP__

#include "Debug.hpp"
#include "Library.hpp"

#include <PalmOS.h>

#ifndef SetBits
#define SetBits( b, len )      ( ( ( 1U << ( ( len ) - 1 ) ) - 1U + ( 1U << ( ( len ) - 1 ) ) ) << ( b ) )
#endif

#ifndef pinMaxConstraintSize
#define pinMaxConstraintSize 	SetBits( 0, ( sizeof( Coord) * 8 ) - 1 )
#endif

namespace ArsLexis 
{

    class Form;
    
    class DIA_Support
    {
        
        UInt16 hasPenInputMgr_:1;
        UInt16 hasSonySilkLib_:1;
        UInt16 sonyLibIsVsk_:1;
        UInt16 notUsed_:13;

        Library sonySilkLib_;
                        
        DIA_Support(const DIA_Support&) throw();
        DIA_Support& operator=(const DIA_Support&) throw();
        
        Boolean tryInitSonySilkLib() throw();
        void sonySilkLibDispose() throw();
        
    public:
        
        DIA_Support() throw();
        ~DIA_Support() throw();

        Boolean hasPenInputManager() const  throw()
        {return hasPenInputMgr_;}
        
        Boolean hasSonySilkLib() const  throw()
        {return hasSonySilkLib_;}
        
        Boolean available() const  throw()
        {return hasPenInputManager()||hasSonySilkLib();}

        UInt32 notifyType() const  throw()
        {return hasPenInputManager()?sysNotifyDisplayResizedEvent:sysNotifyDisplayChangeEvent;}        
       
        void handleNotify() const throw();
        
        Err configureForm(Form& form, Coord minH, Coord prefH, Coord maxH, Coord minW, Coord prefW, Coord maxW) const throw();
        
    };
    
}    

#endif