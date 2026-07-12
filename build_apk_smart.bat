@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   智能错题笔记助手 - 一键APK打包脚本
echo ============================================
echo.
echo [1/5] 正在自动搜索本机可用的Java...

set "FOUND_JAVA="

:: 直接逐个检查常见JDK安装位置（避免括号等特殊字符解析错误）
set JAVA_CHECK_PATHS[0]=C:\Program Files\Microsoft
set JAVA_CHECK_PATHS[1]=C:\Program Files\Eclipse Adoptium
set JAVA_CHECK_PATHS[2]=C:\jdk-11
set JAVA_CHECK_PATHS[3]=C:\Program Files\Java
set JAVA_CHECK_PATHS[4]=C:\Program Files (x86)\Java

for /L %%i in (0,1,4) do (
    call set "CHECK_DIR=%%JAVA_CHECK_PATHS[%%i]%%"
    if defined CHECK_DIR (
        if exist "!CHECK_DIR!" (
            echo   正在扫描: !CHECK_DIR!
            for /r "!CHECK_DIR!" %%F in (java.exe) do (
                if not defined FOUND_JAVA (
                    set "JAVA_BIN=%%~dpF"
                    set "JAVA_HOME=!JAVA_BIN:\bin\=!"
                    "!JAVA_HOME!\bin\java" -version >nul 2>&1
                    if !errorlevel! == 0 (
                        set "FOUND_JAVA=!JAVA_HOME!"
                        echo   发现可用Java: !JAVA_HOME!
                    )
                )
            )
        )
    )
)

:: 如果自动搜索没找到，再检查几个精确路径
if not defined FOUND_JAVA (
    for %%P in (
        "C:\Program Files\Microsoft\jdk-21.0.10.7-hotspot"
        "C:\Program Files\Microsoft\jdk-17"
        "C:\jdk-11"
    ) do (
        if exist %%P\bin\java.exe (
            set "FOUND_JAVA=%%~P"
            echo   发现可用Java: %%~P
        )
    )
)

if not defined FOUND_JAVA (
    echo.
    echo [错误] 未找到任何可用的Java！
    echo 请下载JDK 11并解压到 C:\jdk-11
    echo 下载地址: https://mirrors.tuna.tsinghua.edu.cn/Adoptium/11/jdk/x64/windows/OpenJDK11U-jdk_x64_windows_hotspot_11.0.20_8.zip
    pause
    exit /b 1
)

echo.
echo [2/5] 设置Java环境...
set "JAVA_HOME=%FOUND_JAVA%"
set "PATH=%JAVA_HOME%\bin;%PATH%"

"%JAVA_HOME%\bin\java" -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Java环境设置失败，请检查路径: %JAVA_HOME%
    pause
    exit /b 1
)
echo   当前使用Java路径: %JAVA_HOME%
echo   版本信息:
"%JAVA_HOME%\bin\java" -version 2>&1 | findstr /i "version"

echo.
echo [3/5] 清除项目旧的构建缓存...
if exist "build" (
    rmdir /s /q "build"
    echo   已清除 build 目录
)
if exist "android" (
    rmdir /s /q "android"
    echo   已清除 android 目录
)

echo.
echo [4/5] 配置Gradle使用指定JDK...
(
echo org.gradle.java.home=%JAVA_HOME:\=/%
) > "gradle.properties"
echo   已更新 gradle.properties

echo.
echo [5/5] 开始打包APK...
echo --------------------------------------------------
flet build apk

if %errorlevel% == 0 (
    echo.
    echo ============================================
    echo   打包成功！APK 位于 build\apk 目录
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   打包失败，请检查上方错误信息
    echo ============================================
)

pause
endlocal