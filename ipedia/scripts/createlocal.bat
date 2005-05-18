@rem set settings based on computer name
@if %computername%==DVD goto SetDVD
@if %computername%==DVD2 goto SetDVD
@if %computername%==KJKLAP1 goto SetDVD
@if %computername%==TLAP goto SetDVD

@echo "Don't know the setup for computer %computername%"
@goto EOF

:SetDVD
@SET DSTDIR=c:\kjk\ipedia\src
@SET SRCDIR=c:\kjk\src\mine\ipedia
@goto SetupDone

:SetupDone

@del /f /s /q %DSTDIR%
@mkdir %DSTDIR%
@copy %SRCDIR%\server\*.py %DSTDIR%
@copy %SRCDIR%\scripts\*.py %DSTDIR%
@copy %SRCDIR%\scripts\reg_codes.csv %DSTDIR%
