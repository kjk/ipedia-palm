@rem create a local copy 

@rem set settings based on computer name
@if %computername%==DVD goto SetDVD
@if %computername%==DVD2 goto SetDVD
@if %computername%==TLAP goto SetDVD
@if %computername%==KJKLAP1 goto SetDVD

@echo "Don't know the setup for computer %computername%"
@goto EOF

:SetDVD
@SET DSTDIR=c:\kjk\ipedia\src
@SET SRCDIR=c:\kjk\src\mine\ipedia
@goto SetupDone

:SetupDone

@call createlocal.bat

pushd %DSTDIR%
start iPediaServer.py -verbose -disableregcheck %1 %2 %3
popd

:EOF
