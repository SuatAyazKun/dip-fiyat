@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   DİP FİYAT — Kurulum Başlıyor
echo ========================================
echo.

:: Python kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo Python'u https://www.python.org adresinden indirin.
    pause
    exit /b 1
)

echo [1/5] Python paketleri yukleniyor...
pip install -r requirements.txt
if errorlevel 1 (
    echo [HATA] Paket yuklemesi basarisiz oldu!
    pause
    exit /b 1
)
echo       Tamam.

echo.
echo [2/5] FFmpeg indiriliyor (internet gerekli, birkaç dakika sürebilir)...
if exist "ffmpeg.exe" (
    echo       FFmpeg zaten mevcut, atlanıyor.
) else (
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg_setup.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo [HATA] FFmpeg indirilemedi. Internet baglantinizi kontrol edin.
        pause
        exit /b 1
    )
    powershell -NoProfile -Command ^
        "Expand-Archive -Path 'ffmpeg_setup.zip' -DestinationPath 'ffmpeg_extracted' -Force"
    powershell -NoProfile -Command ^
        "Copy-Item 'ffmpeg_extracted\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe' -Destination 'ffmpeg.exe' -Force"
    rd /s /q ffmpeg_extracted >nul 2>&1
    del ffmpeg_setup.zip >nul 2>&1
    echo       Tamam.
)

echo.
echo [3/5] Klasorler kontrol ediliyor...
if not exist "assets\fonts"     mkdir "assets\fonts"
if not exist "assets\music"     mkdir "assets\music"
if not exist "assets\templates" mkdir "assets\templates"
if not exist "assets\temp"      mkdir "assets\temp"
if not exist "output\videos"    mkdir "output\videos"
if not exist "logs"             mkdir "logs"
if not exist "data"             mkdir "data"
echo       Tamam.

echo.
echo [4/5] Veritabani olusturuluyor...
python modules\database.py
echo       Tamam.

echo.
echo [5/5] Windows Gorev Zamanlayici ayarlaniyor...
schtasks /create /tn "DipFiyat_Sabah" /tr "python \"%~dp0scheduler.py\"" /sc daily /st 08:00 /f >nul
schtasks /create /tn "DipFiyat_Ogle"  /tr "python \"%~dp0scheduler.py\"" /sc daily /st 12:30 /f >nul
schtasks /create /tn "DipFiyat_Aksam" /tr "python \"%~dp0scheduler.py\"" /sc daily /st 20:00 /f >nul
echo       Gorevler olusturuldu: 08:00, 12:30, 20:00

echo.
echo ========================================
echo   KURULUM TAMAMLANDI!
echo ========================================
echo.
echo Sonraki adim:
echo   config.py dosyasini acin ve API bilgilerinizi girin.
echo   (Amazon, Keepa, Instagram, Cloudflare R2, Telegram)
echo.
echo Elle test etmek icin:
echo   python scheduler.py
echo.
pause
