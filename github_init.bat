@echo off
cd /d "e:\Program\class_schedule_plugin"

REM 设置 Git 用户信息
git config user.email "inkt@inkt.love"
git config user.name "INKT-love"

REM 初始化 Git
echo === 初始化 Git 仓库 ===
git init
git add .
git commit -m "feat: 初始版本 - 功能完善的 NoneBot2 课程表插件

- 课程查询（现在什么课、等会什么课等）
- 课前提醒和假期订阅
- 节假日识别（2026-2027年数据）
- 自定义作息表
- 文字/图片双模式输出"

REM 添加远程仓库
echo === 添加远程仓库 ===
git remote add origin https://github.com/INKT-love/nonebot-plugin-class-schedule.git

REM 推送
echo === 推送到 GitHub ===
git branch -M main
git push -u origin main --force

echo.
echo === 完成 ===
pause
