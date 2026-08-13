@echo off
if "%DEVCORE_PLATFORM_ROOT%"=="" set "DEVCORE_PLATFORM_ROOT=%~dp0.."
if "%GEMINI_API_KEY%"=="" if exist "%DEVCORE_PLATFORM_ROOT%\Config\gemini_api_key.txt" set /p GEMINI_API_KEY=<"%DEVCORE_PLATFORM_ROOT%\Config\gemini_api_key.txt"
echo. | repowise serve --host 127.0.0.1 --port 7337 --no-ui > "%USERPROFILE%\repowise_serve.log" 2>&1
