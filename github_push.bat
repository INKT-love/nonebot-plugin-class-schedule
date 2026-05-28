@echo off
cd /d "e:\Program\class_schedule_plugin"

echo === 初始化 Git 仓库 ===
git init
git add .
git commit -m "feat: 初始版本 - 功能完善的 NoneBot2 课程表插件"

echo.
echo === 添加远程仓库 ===
git remote add origin https://github.com/INKT-love/nonebot-plugin-class-schedule.git

echo.
echo === 推送到 GitHub ===
git branch -M main
git push -u origin main

echo.
echo === 完成 ===
pause
