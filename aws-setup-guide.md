# AWS Deployment Guide for Arzana PO Processor

## Prerequisites

### 1. Install AWS CLI
```bash
# Windows (using Chocolatey)
choco install awscli

# Or download from: https://aws.amazon.com/cli/
```

### 2. Install AWS Elastic Beanstalk CLI
```bash
pip install awsebcli
```

### 3. Configure AWS Credentials
```bash
aws configure
```
Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (e.g., `json`)

## Deployment Steps

### Option A: Automated Deployment (Recommended)
```bash
# Make the script executable
chmod +x deploy-aws.sh

# Run the deployment script
./deploy-aws.sh
```

### Option B: Manual Deployment

#### Step 1: Deploy Flask Server to Elastic Beanstalk

```bash
# Initialize Elastic Beanstalk
eb init --platform python-3.9 --region us-east-1 arzana-po-processor

# Create environment
eb create arzana-prod

# Deploy
eb deploy
```

#### Step 2: Deploy Outlook Add-in to S3 + CloudFront

```bash
# Build the add-in
cd Arzana
npm run build
cd ..

# Create S3 bucket
aws s3 mb s3://arzana-outlook-addin-$(date +%s)

# Upload files
aws s3 sync Arzana/dist/ s3://your-bucket-name --delete

# Create CloudFront distribution (use AWS Console for easier setup)
```

## AWS Services Used

### 1. Elastic Beanstalk
- **Purpose**: Hosts your Flask server
- **Benefits**: Auto-scaling, load balancing, health monitoring
- **Cost**: ~$15-30/month (t2.micro instance)

### 2. S3 + CloudFront
- **Purpose**: Hosts Outlook add-in files with HTTPS
- **Benefits**: Global CDN, SSL certificates, high availability
- **Cost**: ~$1-5/month (for small traffic)

### 3. RDS (Optional)
- **Purpose**: Replace SQLite with PostgreSQL for production
- **Benefits**: Better performance, backup, multi-user support
- **Cost**: ~$15-25/month (db.t3.micro)

## Environment Variables

Set these in Elastic Beanstalk environment:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional
FLASK_ENV=production
MAX_FILE_SIZE=16777216
```

## Database Migration (Optional)

For production, consider migrating from SQLite to PostgreSQL:

```bash
# Install psycopg2
pip install psycopg2-binary

# Update requirements.txt
echo "psycopg2-binary>=2.9.0" >> requirements.txt
```

## Security Considerations

1. **Environment Variables**: Store API keys in Elastic Beanstalk environment variables
2. **CORS**: Already configured for Outlook add-ins
3. **HTTPS**: CloudFront provides SSL certificates
4. **IAM**: Use least-privilege access for deployment

## Monitoring

1. **CloudWatch**: Monitor server logs and performance
2. **Health Checks**: Elastic Beanstalk monitors app health
3. **Alarms**: Set up alerts for errors or high CPU usage

## Cost Optimization

1. **Instance Types**: Start with t2.micro, scale as needed
2. **Auto Scaling**: Configure based on CPU/memory usage
3. **CloudFront**: Use Price Class 100 for cost savings
4. **RDS**: Use db.t3.micro for small workloads

## Troubleshooting

### Common Issues

1. **Deployment Fails**: Check Elastic Beanstalk logs
2. **Add-in Not Loading**: Verify CloudFront distribution is deployed
3. **CORS Errors**: Ensure Flask-CORS is properly configured
4. **SSL Issues**: CloudFront handles SSL automatically

### Useful Commands

```bash
# Check Elastic Beanstalk status
eb status

# View logs
eb logs

# SSH into instance
eb ssh

# Check CloudFront distribution
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID
```

## Post-Deployment

1. **Test Flask Server**: Visit `https://your-app.elasticbeanstalk.com/api/health`
2. **Test Add-in**: Visit `https://your-cloudfront-domain/taskpane.html`
3. **Update Manifest**: Use CloudFront URL in manifest.xml
4. **Distribute**: Provide manifest to users or submit to Office Store

## Support

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Elastic Beanstalk**: https://docs.aws.amazon.com/elasticbeanstalk/
- **CloudFront**: https://docs.aws.amazon.com/cloudfront/
