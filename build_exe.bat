@echo off
chcp 65001 > nul
echo ========================================================
echo       بناء الملف التنفيذي (.exe) لمطابقة الأسماء العربية
echo ========================================================
echo.

echo [1/3] تثبيت المتطلبات...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo خطأ في تثبيت المتطلبات.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] بناء ملف EXE بواسطة PyInstaller...
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "ArabicNameMatcher" ^
    --add-data "normalizer.py;." ^
    --add-data "master_store.py;." ^
    --add-data "matcher.py;." ^
    --add-data "exporter.py;." ^
    app.py

if %errorlevel% neq 0 (
    echo خطأ أثناء إنشاء ملف EXE.
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo [3/3] تم بناء الملف التنفيذي بنجاح في مجلد: dist\ArabicNameMatcher
echo ========================================================
echo.
pause
