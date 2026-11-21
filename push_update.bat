@echo off
cd /d C:\myapp
echo ========================================
echo   ChiYu Study - Push Update
echo ========================================
echo.
echo [1/3] Checking changes...
git status --short main.py data/vocabulary.jsonl
echo.
echo [2/3] Committing...
git add main.py data/vocabulary.jsonl
git commit -m "update %date% %time%"
if errorlevel 1 echo (no new changes, skip commit)
echo.
echo [3/3] Pushing to GitHub...
git push origin master
echo.
echo ========================================
echo   Done. Check build at:
echo   https://github.com/huawenxi1219/cuotiben/actions
echo ========================================
pause
