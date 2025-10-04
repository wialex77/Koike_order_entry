@echo off
REM AWS Deployment Script for Arzana PO Processor (Windows)
echo 🚀 Starting AWS deployment...

REM Check if AWS CLI is installed
aws --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ AWS CLI not found. Please install it first:
    echo https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
    pause
    exit /b 1
)

REM Check if EB CLI is installed
eb --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ AWS Elastic Beanstalk CLI not found. Please install it first:
    echo pip install awsebcli
    pause
    exit /b 1
)

echo ✅ AWS CLI and EB CLI found

REM Step 1: Deploy Flask Server to Elastic Beanstalk
echo 📦 Deploying Flask server to AWS Elastic Beanstalk...

REM Initialize EB if not already done
if not exist ".elasticbeanstalk\config.yml" (
    echo 🔧 Initializing Elastic Beanstalk...
    eb init --platform python-3.9 --region us-east-1 arzana-po-processor
)

REM Create environment if it doesn't exist
echo 🌍 Creating/updating Elastic Beanstalk environment...
eb deploy --verbose

echo ✅ Flask server deployed!

REM Get the Flask server URL
for /f "tokens=2" %%i in ('eb status ^| findstr "CNAME"') do set FLASK_URL=%%i
echo 🔗 Flask server URL: http://%FLASK_URL%

REM Step 2: Build Outlook Add-in
echo 📦 Building Outlook add-in for production...
cd Arzana
call npm run build
cd ..

REM Step 3: Deploy Add-in to S3 + CloudFront
echo ☁️ Deploying add-in to AWS S3 + CloudFront...

REM Create S3 bucket for add-in files
set /a BUCKET_SUFFIX=%RANDOM%
set BUCKET_NAME=arzana-outlook-addin-%BUCKET_SUFFIX%
aws s3 mb s3://%BUCKET_NAME% --region us-east-1

REM Upload add-in files
aws s3 sync Arzana\dist\ s3://%BUCKET_NAME% --delete

echo.
echo 🎉 Deployment Complete!
echo ==================================
echo Flask Server URL: https://%FLASK_URL%
echo S3 Bucket: %BUCKET_NAME%
echo.
echo 📋 Next Steps:
echo 1. Create CloudFront distribution in AWS Console
echo 2. Update manifest.xml with CloudFront URL
echo 3. Test the deployment
echo.
echo 💾 Save these URLs for future reference!
pause
