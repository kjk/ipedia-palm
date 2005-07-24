if %computername%==DVD goto SetDVD
if %computername%==DVD2 goto SetDVD2
if %computername%==TLAP goto SetTlap
if %computername%==KJKLAP1 goto SetKjklap1
if %computername%==MAGG goto SetSzymon
if %computername%==GIZMO goto SetAndrzejLap
if %computername%==RABBAN goto SetAndrzejDVD

echo "Don't know the setup for computer %computername%"
exit

:SetDVD
:SetDVD2
:SetTlap
:SetKjklap1
SET DIR=c:\kjk\src\mine\ipedia
goto Done

:SetSzymon
SET DIR=l:\moriarty_palm
goto Done

:SetAndrzejLap
SET DIR=c:\ArsLexis\moriarty
goto Done

:SetAndrzejDVD
SET DIR=c:\ArsLexis\moriarty_palm
goto Done

:Done
set PYTHONPATH=%DIR%\scripts;%DIR%\server

