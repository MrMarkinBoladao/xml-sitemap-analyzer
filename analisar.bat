@echo off
REM ==========================================================================
REM  xml-sitemap-analyzer - atalho para Windows (saida em portugues)
REM  Pode dar dois cliques neste arquivo, ou arrastar um dominio para cima.
REM ==========================================================================
REM  Escrito sem blocos ( ) ao redor de leitura de variavel: dentro de um
REM  bloco o cmd expande %var% em tempo de parse, nao de execucao, e a
REM  deteccao do Python abaixo falharia silenciosamente.
REM ==========================================================================

setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title xml-sitemap-analyzer

REM --- Descobre qual comando de Python existe nesta maquina ----------------
set "PY="

python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :temPython

py --version >nul 2>&1
if not errorlevel 1 set "PY=py"
if defined PY goto :temPython

echo.
echo   [ERRO] Python nao encontrado neste computador.
echo.
echo   Para instalar:
echo     1. Abra a Microsoft Store
echo     2. Busque por "Python 3.12"
echo     3. Clique em Instalar
echo.
echo   Ou baixe em https://www.python.org/downloads/
echo   Se usar o instalador do site, marque "Add python.exe to PATH".
echo.
pause
exit /b 1

:temPython

REM --- Pega o dominio: argumento arrastado, ou pergunta -------------------
set "SITE=%~1"
if defined SITE goto :temSite

echo.
echo   ==========================================
echo     xml-sitemap-analyzer
echo   ==========================================
echo.
set /p "SITE=  Digite o site (ex: exemplo.com): "

:temSite
if not defined SITE goto :semSite

echo.
echo   Analisando %SITE% ...
echo.
%PY% sitemap_analyzer.py %SITE% --lang pt
goto :fim

:semSite
echo.
echo   Nenhum site informado.

:fim
echo.
echo   ------------------------------------------
echo    Terminou. Aperte uma tecla para fechar.
echo   ------------------------------------------
pause >nul
endlocal
