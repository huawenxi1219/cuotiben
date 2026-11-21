$ErrorActionPreference = 'Continue'
$rt = Join-Path $env:APPDATA 'apkstart\runtime'
$avdHome = Join-Path $env:APPDATA 'apkstart\avd'
$avdDir = Join-Path $avdHome 'chiyu.avd'
New-Item -ItemType Directory -Force $avdDir | Out-Null

$ini = "avd.ini.encoding=UTF-8`npath=" + ($avdDir -replace '\\', '/') + "`npath.rel=avd/chiyu.avd`ntarget=android-34`n"
Set-Content -Path (Join-Path $avdHome 'chiyu.ini') -Value $ini -Encoding ASCII

$cfg = @"
avd.ini.encoding=UTF-8
AvdId=chiyu
avd.ini.displayname=chiyu
image.sysdir.1=system-images/android-34/google_apis_playstore/x86_64/
tag.id=google_apis_playstore
tag.display=Google Play
hw.cpu.arch=x86_64
hw.ramSize=2048
vm.heapSize=256
hw.lcd.density=440
hw.lcd.width=1080
hw.lcd.height=2400
disk.dataPartition.size=6G
hw.keyboard=yes
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
showDeviceFrame=no
"@
Set-Content -Path (Join-Path $avdDir 'config.ini') -Value $cfg -Encoding ASCII

$env:ANDROID_SDK_ROOT = $rt
$env:ANDROID_HOME = $rt
$env:ANDROID_AVD_HOME = $avdHome

Write-Output ('runtime exists: ' + (Test-Path (Join-Path $rt 'emulator\emulator.exe')))
Write-Output '=== list-avds ==='
& (Join-Path $rt 'emulator\emulator.exe') -list-avds 2>&1
