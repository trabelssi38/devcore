@echo off
cd /d C:\src\dashboard_recette_br
if "%GEMINI_API_KEY%"=="" set /p GEMINI_API_KEY=<"C:\devcore\DEV_CORE\Config\gemini_api_key.txt"
echo. | "C:\Program Files\Python313\Scripts\repowise.exe" serve --host 127.0.0.1 --port 7337 --no-ui > "C:\Users\trb_m\repowise_serve.log" 2>&1
