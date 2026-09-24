@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [RESET] Hay dung bot truoc khi reset state.
if exist processed.json del /q processed.json
if exist processed.json.bak del /q processed.json.bak
if exist pending_comments.json del /q pending_comments.json
if exist pending_comments.json.bak del /q pending_comments.json.bak
echo [OK] Da xoa processed state va pending comment state.
echo [NOTE] Neu only_new_posts=true, lan chay sau se tao baseline moi va bo qua cac bai hien co.
pause