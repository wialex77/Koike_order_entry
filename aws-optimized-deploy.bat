@echo off
REM AWS Optimized Deployment Script for Arzana PO Processor (Windows)
REM Uses App Runner + S3 + CloudFront for best cost/performance ratio

echo 🚀 Starting AWS optimized deployment...

REM Check prerequisites
aws --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ AWS CLI not found. Please install it first.
    pause
    exit /b 1
)

npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js/npm not found. Please install it first.
    pause
    exit /b 1
)

echo ✅ Prerequisites found

REM Step 1: Deploy Flask Server to AWS App Runner
echo 📦 Deploying Flask server to AWS App Runner...

REM Note: App Runner setup requires manual configuration in AWS Console
echo ⚠️  App Runner setup requires manual configuration:
echo 1. Go to AWS Console ^> App Runner
echo 2. Create service from source code repository
echo 3. Configure with these settings:
echo    - Runtime: Python 3
echo    - Build command: pip install -r requirements.txt
echo    - Start command: python app.py
echo    - Port: 8080
echo    - Environment variables: FLASK_ENV=production

echo.
echo Press any key after setting up App Runner...
pause

REM Get App Runner URL from user
set /p APP_RUNNER_URL="Enter your App Runner URL (e.g., https://xxxxx.us-east-1.awsapprunner.com): "

echo 🔗 App Runner URL: %APP_RUNNER_URL%

REM Step 2: Build Outlook Add-in
echo 📦 Building Outlook add-in...
cd Arzana
call npm run build
cd ..

REM Step 3: Deploy Add-in to S3 + CloudFront
echo ☁️ Deploying add-in to S3 + CloudFront...

REM Create S3 bucket
set /a BUCKET_SUFFIX=%RANDOM%
set BUCKET_NAME=arzana-outlook-addin-%BUCKET_SUFFIX%
aws s3 mb s3://%BUCKET_NAME% --region us-east-1

REM Set bucket policy for CloudFront
echo { > bucket-policy.json
echo     "Version": "2012-10-17", >> bucket-policy.json
echo     "Statement": [ >> bucket-policy.json
echo         { >> bucket-policy.json
echo             "Sid": "PublicReadGetObject", >> bucket-policy.json
echo             "Effect": "Allow", >> bucket-policy.json
echo             "Principal": "*", >> bucket-policy.json
echo             "Action": "s3:GetObject", >> bucket-policy.json
echo             "Resource": "arn:aws:s3:::%BUCKET_NAME%/*" >> bucket-policy.json
echo         } >> bucket-policy.json
echo     ] >> bucket-policy.json
echo } >> bucket-policy.json

aws s3api put-bucket-policy --bucket %BUCKET_NAME% --policy file://bucket-policy.json

REM Upload add-in files
aws s3 sync Arzana\dist\ s3://%BUCKET_NAME% --delete

echo ☁️ Creating CloudFront distribution...
echo ⚠️  CloudFront setup requires manual configuration:
echo 1. Go to AWS Console ^> CloudFront
echo 2. Create distribution
echo 3. Origin domain: %BUCKET_NAME%.s3.amazonaws.com
echo 4. Default root object: taskpane.html
echo 5. Viewer protocol policy: Redirect HTTP to HTTPS
echo 6. Price class: Use only US, Canada and Europe

echo.
echo Press any key after setting up CloudFront...
pause

REM Get CloudFront URL from user
set /p ADDIN_URL="Enter your CloudFront URL (e.g., https://xxxxx.cloudfront.net): "

echo 🔗 Add-in URL: %ADDIN_URL%

REM Step 4: Update URLs in code
echo 🔧 Updating URLs in manifest and taskpane...

REM Update manifest.xml
powershell -Command "(Get-Content Arzana\manifest.xml) -replace 'https://localhost:3000', '%ADDIN_URL%' | Set-Content Arzana\manifest.xml"
powershell -Command "(Get-Content Arzana\manifest.xml) -replace 'https://localhost:5000', '%APP_RUNNER_URL%' | Set-Content Arzana\manifest.xml"

REM Update taskpane.ts
powershell -Command "(Get-Content Arzana\src\taskpane\taskpane.ts) -replace 'http://127.0.0.1:5000', '%APP_RUNNER_URL%' | Set-Content Arzana\src\taskpane\taskpane.ts"
powershell -Command "(Get-Content Arzana\src\taskpane\taskpane.ts) -replace 'http://localhost:5000', '%APP_RUNNER_URL%' | Set-Content Arzana\src\taskpane\taskpane.ts"

REM Rebuild and redeploy with updated URLs
cd Arzana
call npm run build
cd ..

aws s3 sync Arzana\dist\ s3://%BUCKET_NAME% --delete

REM Cleanup
del bucket-policy.json

echo.
echo 🎉 AWS Optimized Deployment Complete!
echo =====================================
echo Flask Server (App Runner): %APP_RUNNER_URL%
echo Outlook Add-in (CloudFront): %ADDIN_URL%
echo S3 Bucket: %BUCKET_NAME%
echo.
echo 💰 Estimated Monthly Costs:
echo - App Runner: ~$25-45
echo - S3 + CloudFront: ~$2-8
echo - Total: ~$27-53/month
echo.
echo 📋 Next Steps:
echo 1. Test Flask server: %APP_RUNNER_URL%/api/health
echo 2. Test add-in: %ADDIN_URL%/taskpane.html
echo 3. Update manifest.xml with production URLs
echo 4. Distribute to users
echo.
echo 💾 Save these URLs for future reference!
pause
