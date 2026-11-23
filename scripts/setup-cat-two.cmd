@echo off
setlocal DisableDelayedExpansion

set "CAT_TWO_PLUGIN=%~dp0plugins\cat-two-notes"
set "CAT_TWO_PYTHON=%CAT_TWO_PLUGIN%\runtime\python.exe"
set "CAT_TWO_SERVER=%CAT_TWO_PLUGIN%\scripts\server.py"

if not exist "%CAT_TWO_PYTHON%" goto :missing
if not exist "%CAT_TWO_SERVER%" goto :missing

"%CAT_TWO_PYTHON%" -X utf8 -E -s -B "%CAT_TWO_SERVER%" setup-browser
set "CAT_TWO_EXIT=%ERRORLEVEL%"
if "%CAT_TWO_EXIT%"=="0" exit /b 0

echo.
echo Cat_two setup exited with code %CAT_TWO_EXIT%.
echo Open setup-cat-two.cmd again to retry.
pause
exit /b %CAT_TWO_EXIT%

:missing
echo The bundled Cat_two runtime or setup script is missing.
echo Extract the complete Windows marketplace ZIP and open setup-cat-two.cmd again.
pause
exit /b 1
