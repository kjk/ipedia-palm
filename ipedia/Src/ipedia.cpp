
#include "iPediaApplication.hpp"

void std::__msl_error(const char* str)
{
    ErrFatalDisplay(str);
    ErrThrow(sysErrParamErr);
}

void ArsLexis::handleBadAlloc()
{
    ErrThrow(memErrNotEnoughSpace);    
}

UInt32 PilotMain(UInt16 cmd, MemPtr cmdPBP, UInt16 launchFlags)
{
    return Application::main<iPediaApplication>(cmd, cmdPBP, launchFlags);
}
