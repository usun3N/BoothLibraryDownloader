if exist ".venv"(
    echo "venv already exists"
    exit
)
echo %PATH% | findstr "python" > NUL
if not ERRORLEVEL == 1(
    python -m venv .venv
    "./.venv/Scripts/python.exe" -m pip install -r requirements.txt
) else(
    echo "please install python first"
)