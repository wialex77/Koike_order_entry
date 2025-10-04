#!/bin/bash

# AWS Deployment Script for Arzana PO Processor
echo "🚀 Starting AWS deployment..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if EB CLI is installed
if ! command -v eb &> /dev/null; then
    echo "❌ AWS Elastic Beanstalk CLI not found. Please install it first:"
    echo "pip install awsebcli"
    exit 1
fi

echo "✅ AWS CLI and EB CLI found"

# Step 1: Deploy Flask Server to Elastic Beanstalk
echo "📦 Deploying Flask server to AWS Elastic Beanstalk..."

# Initialize EB if not already done
if [ ! -f ".elasticbeanstalk/config.yml" ]; then
    echo "🔧 Initializing Elastic Beanstalk..."
    eb init --platform python-3.9 --region us-east-1 arzana-po-processor
fi

# Create environment if it doesn't exist
echo "🌍 Creating/updating Elastic Beanstalk environment..."
eb deploy --verbose

echo "✅ Flask server deployed!"

# Get the Flask server URL
FLASK_URL=$(eb status | grep "CNAME" | awk '{print $2}')
echo "🔗 Flask server URL: http://$FLASK_URL"

# Step 2: Build Outlook Add-in
echo "📦 Building Outlook add-in for production..."
cd Arzana
npm run build
cd ..

# Step 3: Deploy Add-in to S3 + CloudFront
echo "☁️ Deploying add-in to AWS S3 + CloudFront..."

# Create S3 bucket for add-in files
BUCKET_NAME="arzana-outlook-addin-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Upload add-in files
aws s3 sync Arzana/dist/ s3://$BUCKET_NAME --delete

# Create CloudFront distribution
echo "🌐 Creating CloudFront distribution..."
cat > cloudfront-config.json << EOF
{
    "CallerReference": "arzana-addin-$(date +%s)",
    "Comment": "Arzana Outlook Add-in",
    "DefaultRootObject": "taskpane.html",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-$BUCKET_NAME",
                "DomainName": "$BUCKET_NAME.s3.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-$BUCKET_NAME",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {
                "Forward": "none"
            }
        }
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}
EOF

DISTRIBUTION_ID=$(aws cloudfront create-distribution --distribution-config file://cloudfront-config.json --query 'Distribution.Id' --output text)
echo "📡 CloudFront Distribution ID: $DISTRIBUTION_ID"

# Wait for distribution to be deployed
echo "⏳ Waiting for CloudFront distribution to deploy (this may take 10-15 minutes)..."
aws cloudfront wait distribution-deployed --id $DISTRIBUTION_ID

# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id $DISTRIBUTION_ID --query 'Distribution.DomainName' --output text)
ADDIN_URL="https://$CLOUDFRONT_DOMAIN"
echo "🔗 Add-in URL: $ADDIN_URL"

# Step 4: Update manifest and taskpane with production URLs
echo "🔧 Updating URLs in manifest and taskpane..."

# Update manifest.xml
sed -i "s|https://localhost:3000|$ADDIN_URL|g" Arzana/manifest.xml
sed -i "s|https://localhost:5000|https://$FLASK_URL|g" Arzana/manifest.xml

# Update taskpane.ts
sed -i "s|http://127.0.0.1:5000|https://$FLASK_URL|g" Arzana/src/taskpane/taskpane.ts
sed -i "s|http://localhost:5000|https://$FLASK_URL|g" Arzana/src/taskpane/taskpane.ts

# Rebuild add-in with updated URLs
cd Arzana
npm run build
cd ..

# Upload updated files
aws s3 sync Arzana/dist/ s3://$BUCKET_NAME --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

echo ""
echo "🎉 Deployment Complete!"
echo "=================================="
echo "Flask Server URL: https://$FLASK_URL"
echo "Add-in URL: $ADDIN_URL"
echo "S3 Bucket: $BUCKET_NAME"
echo "CloudFront Distribution: $DISTRIBUTION_ID"
echo ""
echo "📋 Next Steps:"
echo "1. Test the Flask server: https://$FLASK_URL/api/health"
echo "2. Test the add-in: $ADDIN_URL/taskpane.html"
echo "3. Update your manifest.xml with the add-in URL"
echo "4. Distribute the manifest to users"
echo ""
echo "💾 Save these URLs for future reference!"
