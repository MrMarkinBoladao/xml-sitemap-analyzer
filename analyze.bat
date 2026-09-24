@echo off
REM ==========================================================================
REM  xml-sitemap-analyzer - Windows shortcut (English output)
REM  Double-click this file, or drag a domain onto it.
REM ==========================================================================
REM  Written without ( ) blocks around variable reads: inside a block cmd
REM  expands %var% at parse time, not at run time, and the Python detection
REM  below would fail silently.
REM ==========================================================================

setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title xml-sitemap-analyzer

REM --- Find out which Python command exists on this machine ----------------
set "PY="

python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :hasPython

py --version >nul 2>&1
if not errorlevel 1 set "PY=py"
if defined PY goto :hasPython

echo.
echo   [ERROR] Python was not found on this computer.
echo.
echo   To install it:
echo     1. Open the Microsoft Store
echo     2. Search for "Python 3.12"
echo     3. Click Install
echo.
echo   Or download it from https://www.python.org/downloads/
echo   If you use the installer from the site, check "Add python.exe to PATH".
echo.
pause
exit /b 1

:hasPython

REM --- Get the domain: dragged argument, or ask for it ---------------------
set "SITE=%~1"
if defined SITE goto :hasSite

echo.
echo   ==========================================
echo     xml-sitemap-analyzer
echo   ==========================================
echo.
set /p "SITE=  Enter the site (e.g. example.com): "

:hasSite
if not defined SITE goto :noSite

echo.
echo   Analyzing %SITE% ...
echo.
%PY% sitemap_analyzer.py %SITE%
goto :done

:noSite
echo.
echo   No site given.

:done
echo.
echo   ------------------------------------------
echo    Finished. Press any key to close.
echo   ------------------------------------------
pause >nul
endlocal
