#ifndef __ARSLEXIS_NATIVE_GRAPHICS_HPP__
#define __ARSLEXIS_NATIVE_GRAPHICS_HPP__

namespace ArsLexis 
{

#if defined(__PALMOS_H__)

}

#include "PalmFont.hpp"

namespace ArsLexis
{

    typedef PalmFont NativeFont_t;

    typedef IndexedColorType NativeColor_t;
    
    typedef WinHandle NativeGraphicsHandle_t;
    
    #define USE_DEFAULT_NATIVE_GRAPHICS_HANDLE 1    

    typedef NativeFont_t NativeGraphicsState_t;
    
    struct NativeGraphicsSupport
    {
        NativeFont_t font;
    };

#elif defined(_WIN32_WCE)

    typedef COLORREF NativeColor_t;

    typedef HDC NativeGraphicsHandle_t;
    
    typedef int NativeGraphicsState_t;
    
}    
// What we need to do here is to include header implementing HFONT wrapper for Windows CE. 
// I assume that this wrapper class will be called WinFont and reside in file WinFont.hpp
// Font *must* be copyable, so it should be reference-counted internally (we discussed these matters 
// with Marek and it seems it's the easiest way to ensure proper HDC behavior. Of course you don't
// have to use the proposed names as long as typedefs are set correctly.
//#include "WinFont.hpp"

namespace ArsLexis 
{ 

 //   typedef WinFont NativeFont_t;

	typedef int NativeFont_t;
    
    struct NativeGraphicsSupport
    {
    };

#else

#error "Define native graphics counterparts in NativeGraphics.hpp before including Graphics.hpp"

#endif

}


#endif