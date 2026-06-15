@echo off
chcp 65001 >nul
setlocal

REM ====== 路径配置 ======
set "INJECT_EXE=E:\C-Code\vbot\4.1.8.27\x64 inject.exe"
set "WECHAT_EXE=C:\Program Files\Tencent\Weixin\Weixin.exe"
set "HOOK_DLL=E:\C-Code\vbot\4.1.8.27\libGLESv1.dll"

REM ====== 注入参数(JSON) ======
set "INJECT_JSON={\"recivemode\":\"tcp\",\"tcp_ip\":\"127.0.0.1\",\"tcp_port\":61108,\"http_server_port\":19088,\"http_callback_url\":\"http://127.0.0.1:5000/api/recvMsg\",\"usedefault\":false,\"start_server_while_login\":true}"

echo ========================================
echo 启动微信注入服务
echo ========================================
echo.

if not exist "%INJECT_EXE%" (
    echo [错误] 未找到注入程序: %INJECT_EXE%
    pause
    exit /b 1
)

if not exist "%WECHAT_EXE%" (
    echo [错误] 未找到微信程序: %WECHAT_EXE%
    pause
    exit /b 1
)

if not exist "%HOOK_DLL%" (
    echo [错误] 未找到Hook DLL: %HOOK_DLL%
    pause
    exit /b 1
)

echo [信息] 注入程序: %INJECT_EXE%
echo [信息] 微信程序: %WECHAT_EXE%
echo [信息] Hook DLL : %HOOK_DLL%
echo [信息] JSON参数: %INJECT_JSON%
echo.

"%INJECT_EXE%" "%WECHAT_EXE%" "%HOOK_DLL%" "%INJECT_JSON%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [错误] 注入命令执行失败, exit code=%EXIT_CODE%
    pause
    exit /b %EXIT_CODE%
)

echo.
echo [成功] 注入命令已执行完成
pause
exit /b 0
