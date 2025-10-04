@echo off
echo Installing AWS CLI...

REM Download AWS CLI installer
echo Downloading AWS CLI installer...
powershell -Command "Invoke-WebRequest -Uri 'https://awscli.amazonaws.com/AWSCLIV2.msi' -OutFile 'AWSCLIV2.msi'"

REM Install AWS CLI
echo Installing AWS CLI...
msiexec /i AWSCLIV2.msi /quiet /norestart

REM Wait for installation
echo Waiting for installation to complete...
timeout /t 30

REM Clean up installer
del AWSCLIV2.msi

REM Verify installation
echo Verifying installation...
aws --version

if %errorlevel% equ 0 (
    echo ✅ AWS CLI installed successfully!
    echo.
    echo Next steps:
    echo 1. Run: aws configure
    echo 2. Enter your AWS Access Key ID
    echo 3. Enter your AWS Secret Access Key
    echo 4. Choose default region (e.g., us-east-1)
    echo 5. Choose default output format (json)
) else (
    echo ❌ AWS CLI installation failed. Please install manually:
    echo https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
)

pause
