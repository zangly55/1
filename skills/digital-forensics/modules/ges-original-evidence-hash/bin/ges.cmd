@echo off
setlocal EnableExtensions
if not defined GES_CLI_APP set "GES_CLI_APP=goldeneyes"

set "SCRIPT_DIR=%~dp0"

set "WINDOWS_ROOT=%SystemRoot%"
if not defined WINDOWS_ROOT set "WINDOWS_ROOT=%WINDIR%"
if not defined WINDOWS_ROOT set "WINDOWS_ROOT=C:\Windows"
set "PATH=%WINDOWS_ROOT%\System32\WindowsPowerShell\v1.0;%WINDOWS_ROOT%\System32;%WINDOWS_ROOT%\System32\Wbem;%PATH%"

set "GE_HOME_TEMPLATE=__GOLDENEYES_HOME__"

set "GE_HOME_RESOLVED=%GOLDENEYES_HOME%"
set "GE_PYTHON_RESOLVED=%GOLDENEYES_PYTHON%"
set "GE_PYPLUGIN_RESOLVED=%GOLDENEYES_PYPLUGIN%"

if not defined GE_HOME_RESOLVED if defined GE_HOME set "GE_HOME_RESOLVED=%GE_HOME%"
if not defined GE_HOME_RESOLVED if not "%GE_HOME_TEMPLATE%"=="__GOLDENEYES_HOME__" set "GE_HOME_RESOLVED=%GE_HOME_TEMPLATE%"
if defined GE_HOME_RESOLVED goto have_home
if defined GE_PYTHON_RESOLVED if defined GE_PYPLUGIN_RESOLVED goto have_home

for %%I in ("%SCRIPT_DIR%..\..\..") do set "CANDIDATE_HOME=%%~fI"
if exist "%CANDIDATE_HOME%\Python311\python.exe" set "GE_HOME_RESOLVED=%CANDIDATE_HOME%"
if defined GE_HOME_RESOLVED goto have_home

for %%I in ("%SCRIPT_DIR%..\..\..\..\..\..") do set "CANDIDATE_HOME=%%~fI"
if exist "%CANDIDATE_HOME%\Python311\python.exe" set "GE_HOME_RESOLVED=%CANDIDATE_HOME%"
if defined GE_HOME_RESOLVED goto have_home

call :find_registry_home
if defined GE_HOME_RESOLVED goto have_home

if exist "%ProgramFiles%\Honglian\GoldenEyesV4\Python311\python.exe" set "GE_HOME_RESOLVED=%ProgramFiles%\Honglian\GoldenEyesV4"
if defined GE_HOME_RESOLVED goto have_home

set "PROGRAM_FILES_X86=%ProgramFiles(x86)%"
if defined PROGRAM_FILES_X86 if exist "%PROGRAM_FILES_X86%\Honglian\GoldenEyesV4\Python311\python.exe" set "GE_HOME_RESOLVED=%PROGRAM_FILES_X86%\Honglian\GoldenEyesV4"
if defined GE_HOME_RESOLVED goto have_home

echo ERROR: GoldenEyes home was not found. Set GOLDENEYES_HOME to the GoldenEyesV4 install directory. 1>&2
exit /b 1

:have_home

if not defined GE_PYTHON_RESOLVED set "GE_PYTHON_RESOLVED=%GE_HOME_RESOLVED%\Python311\python.exe"
if not defined GE_PYPLUGIN_RESOLVED set "GE_PYPLUGIN_RESOLVED=%GE_HOME_RESOLVED%\pyplugin"

set "GE_PYTHON=%GE_PYTHON_RESOLVED%"
set "GE_PYPLUGIN=%GE_PYPLUGIN_RESOLVED%"
set "GE_HOME_RESOLVED=%GE_HOME_RESOLVED%"

if not exist "%GE_PYTHON%" (
    echo ERROR: GoldenEyes Python was not found: %GE_PYTHON% 1>&2
    exit /b 1
)

if not exist "%GE_PYPLUGIN%\pygesclient" (
    echo ERROR: pygesclient was not found under: %GE_PYPLUGIN% 1>&2
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONWARNINGS=ignore:urllib3"
set "OLD_PYTHONPATH=%PYTHONPATH%"
if defined OLD_PYTHONPATH set "PYTHONPATH=%GE_PYPLUGIN%;%OLD_PYTHONPATH%"
if not defined OLD_PYTHONPATH set "PYTHONPATH=%GE_PYPLUGIN%"

"%GE_PYTHON%" -c "from pygesclient.ges_cli.main import main; raise SystemExit(main())" %*
exit /b %ERRORLEVEL%

:find_registry_home
for %%K in ("HKCU\Software\honglian\GoldenEyesV4" "HKLM\Software\honglian\GoldenEyesV4") do (
    for %%V in (64 32) do (
        for /f "tokens=2,*" %%A in ('reg.exe query "%%~K" /ve /reg:%%V 2^>nul') do if /i "%%A"=="REG_SZ" call :accept_registry_home "%%B"
        if defined GE_HOME_RESOLVED exit /b 0
        for /f "tokens=2,*" %%A in ('reg.exe query "%%~K" /v Path /reg:%%V 2^>nul') do if /i "%%A"=="REG_SZ" for %%I in ("%%B") do call :accept_registry_home "%%~dpI"
        if defined GE_HOME_RESOLVED exit /b 0
    )
)
exit /b 0

:accept_registry_home
if exist "%~1\Python311\python.exe" set "GE_HOME_RESOLVED=%~1"
exit /b 0
