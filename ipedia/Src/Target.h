#ifndef _IPEDIA_TARGET_H_
#define _IPEDIA_TARGET_H_

#if __ide_target("Release")
    #include <PalmOS_Headers>
    #ifndef NDEBUG
    #define NDEBUG
    #endif
    #define ARSLEXIS_VERSION 1
#endif

#if __ide_target("Debug")
    #include <PalmOS_Headers_Debug>
    #define INTERNAL_BUILD 1
#endif

#if __ide_target("Palmgear")
    #include <PalmOS_Headers>
    #ifndef NDEBUG
    #define NDEBUG
    #endif
    #define PALMGEAR 1
#endif

#if __ide_target("Handango")
    #include <PalmOS_Headers>
    #ifndef NDEBUG
    #define NDEBUG
    #endif
    #define HANDANGO 1
#endif

// define DETAILED_CONNECTION_STATUS to get more detailed info about the stages
// of retrieving data from the server
//#define DETAILED_CONNECTION_STATUS 1
#define ARSLEXIS_USE_NEW_FRAMEWORK 1
#define _PALM_OS  1

#define ALLOCATION_LOG_PATH "\\var\\log\\ipedia_allocation.log"

#ifndef NDEBUG
//! Some functions depend on this non-standard symbol instead of standard-compliant @c NDEBUG.
#define DEBUG
#endif

#else

#error "You must not include file Target.h directly. You should use it as your prefix file."

#endif // _IPEDIA_TARGET_H_