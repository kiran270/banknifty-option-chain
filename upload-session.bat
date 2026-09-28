@echo off
echo Uploading session to Coolify server...
echo.

scp data\session.json ubuntu@52.5.107.23:~/session.json

echo.
echo Session uploaded! Now run this on the server:
echo   docker cp ~/session.json b9aa54167cb2:/app/data/session.json
echo.
pause
