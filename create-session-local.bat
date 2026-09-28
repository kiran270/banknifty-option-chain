@echo off
echo ============================================
echo Creating GoCharting Session Locally
echo ============================================
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt
echo.

echo Starting Chrome for GoCharting login...
echo Please login to GoCharting in the browser window.
echo After logging in, press ENTER in this window.
echo.

python login.py

echo.
echo ============================================
echo Session created at: data\session.json
echo ============================================
echo.
echo Next steps:
echo 1. Upload to server: scp data\session.json ubuntu@52.5.107.23:~/session.json
echo 2. Copy to container: docker cp ~/session.json b9aa54167cb2:/app/data/session.json
echo.
pause
