@echo off
echo AWS Configuration Setup
echo =======================

echo.
echo You'll need your AWS credentials:
echo - AWS Access Key ID
echo - AWS Secret Access Key
echo - Default region (e.g., us-east-1)
echo - Default output format (json)
echo.

echo Running aws configure...
aws configure

echo.
echo Testing AWS connection...
aws sts get-caller-identity

if %errorlevel% equ 0 (
    echo ✅ AWS CLI configured successfully!
    echo.
    echo Your AWS identity:
    aws sts get-caller-identity
) else (
    echo ❌ AWS configuration failed. Please check your credentials.
    echo.
    echo Make sure you have:
    echo 1. Valid AWS Access Key ID
    echo 2. Valid AWS Secret Access Key
    echo 3. Proper IAM permissions for S3, CloudFront, and App Runner
)

echo.
echo Press any key to continue...
pause
