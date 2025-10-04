# AWS Optimized Deployment Guide

## Research Summary

After deep research on AWS services, here's the optimal architecture for your Arzana PO Processor:

### **Recommended Architecture: Option A (Cost-Optimized)**

| Component | Service | Monthly Cost | Why This Choice |
|-----------|---------|--------------|-----------------|
| **Flask Backend** | AWS App Runner | $25-45 | Auto-scaling, managed, modern |
| **Outlook Add-in** | S3 + CloudFront | $2-8 | Global CDN, HTTPS, cost-effective |
| **Database** | RDS PostgreSQL (t3.micro) | $15-20 | Production-ready, reliable |
| **Total** | | **$42-73/month** | **Best value for production** |

### **Why These Services?**

#### **AWS App Runner (Backend)**
- ✅ **Fully managed** - No server management
- ✅ **Auto-scaling** - Handles traffic spikes automatically  
- ✅ **Modern architecture** - Built for containerized apps
- ✅ **Cost-effective** - Pay only for what you use
- ✅ **Easy deployment** - Connect to GitHub, auto-deploys

#### **S3 + CloudFront (Frontend)**
- ✅ **Global CDN** - Fast loading worldwide
- ✅ **HTTPS included** - Required for Office add-ins
- ✅ **Cost-effective** - $2-8/month for small traffic
- ✅ **Reliable** - 99.9% uptime SLA

#### **RDS PostgreSQL (Database)**
- ✅ **Production-ready** - Replace SQLite for multi-user
- ✅ **Backup included** - Automated backups
- ✅ **Scalable** - Can grow with your business

## Alternative Options

### **Option B: Budget-Conscious ($7-18/month)**
- **Backend**: Amazon Lightsail ($5-10/month)
- **Frontend**: S3 + CloudFront ($2-8/month)  
- **Database**: Keep SQLite initially ($0)
- **Best for**: Testing, small teams, limited budget

### **Option C: Enterprise-Ready ($45-90/month)**
- **Backend**: AWS Elastic Beanstalk ($20-35/month)
- **Frontend**: AWS Amplify ($5-15/month)
- **Database**: RDS Aurora Serverless ($20-40/month)
- **Best for**: Large teams, high availability needs

## Deployment Steps

### **Prerequisites**
```bash
# Install AWS CLI
# Download from: https://aws.amazon.com/cli/

# Configure AWS credentials
aws configure

# Install Node.js (if not already installed)
# Download from: https://nodejs.org/
```

### **Automated Deployment**

#### **Windows:**
```cmd
aws-optimized-deploy.bat
```

#### **Linux/Mac:**
```bash
chmod +x aws-optimized-deploy.sh
./aws-optimized-deploy.sh
```

### **Manual Deployment**

#### **Step 1: Deploy Flask to App Runner**

1. **Go to AWS Console** → App Runner
2. **Create service** → Source code repository
3. **Connect to GitHub** (your repository)
4. **Configure:**
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `python app.py`
   - Port: 8080
   - Environment variables:
     - `FLASK_ENV=production`
     - `PORT=8080`

#### **Step 2: Deploy Add-in to S3 + CloudFront**

1. **Create S3 bucket:**
   ```bash
   aws s3 mb s3://arzana-outlook-addin-$(date +%s)
   ```

2. **Build and upload add-in:**
   ```bash
   cd Arzana
   npm run build
   cd ..
   aws s3 sync Arzana/dist/ s3://your-bucket-name --delete
   ```

3. **Create CloudFront distribution:**
   - Origin: Your S3 bucket
   - Default root object: `taskpane.html`
   - Viewer protocol policy: Redirect HTTP to HTTPS

#### **Step 3: Update URLs**

1. **Update manifest.xml:**
   ```xml
   <SourceLocation DefaultValue="https://your-cloudfront-url/taskpane.html"/>
   <AppDomain>https://your-apprunner-url</AppDomain>
   ```

2. **Update taskpane.ts:**
   ```typescript
   const response = await fetch(`https://your-apprunner-url/api/get_processed_email?...`);
   ```

## Cost Breakdown

### **Monthly Costs (Small Business)**
- **App Runner**: $25-45 (0.25 vCPU, 0.5 GB RAM)
- **S3 Storage**: $1-2 (10 GB)
- **CloudFront**: $1-6 (100 GB transfer)
- **RDS PostgreSQL**: $15-20 (t3.micro)
- **Total**: $42-73/month

### **Cost Optimization Tips**
1. **Start small** - Use t3.micro instances
2. **Monitor usage** - Set up CloudWatch alarms
3. **Use Reserved Instances** - Save 30-50% on RDS
4. **Optimize CloudFront** - Use Price Class 100

## Performance Benefits

### **App Runner vs Elastic Beanstalk**
- **Faster deployments** (2-3 minutes vs 10-15 minutes)
- **Better auto-scaling** (responds in seconds vs minutes)
- **Modern architecture** (container-based vs EC2-based)
- **Lower operational overhead** (fully managed)

### **S3 + CloudFront vs Alternatives**
- **Global performance** (CDN in 200+ locations)
- **Cost-effective** (cheaper than Amplify for static sites)
- **Simple setup** (fewer moving parts than ECS)

## Security Considerations

1. **HTTPS everywhere** - CloudFront provides SSL certificates
2. **Environment variables** - Store API keys in App Runner
3. **IAM roles** - Use least-privilege access
4. **VPC** - App Runner can connect to VPC for RDS

## Monitoring & Maintenance

1. **CloudWatch** - Monitor performance and errors
2. **App Runner metrics** - CPU, memory, request count
3. **CloudFront analytics** - Cache hit rates, bandwidth
4. **RDS monitoring** - Database performance and connections

## Scaling Strategy

### **Traffic Growth**
- **App Runner**: Auto-scales to 25 instances
- **CloudFront**: Handles unlimited traffic
- **RDS**: Upgrade to larger instances as needed

### **Geographic Expansion**
- **CloudFront**: Already global
- **App Runner**: Deploy in multiple regions if needed
- **RDS**: Use read replicas for global performance

## Next Steps

1. **Test locally** - Ensure everything works
2. **Deploy to AWS** - Use provided scripts
3. **Test production** - Verify both URLs work
4. **Update manifest** - Use production URLs
5. **Distribute** - Provide manifest to users
6. **Monitor** - Set up alerts and monitoring

## Support & Resources

- **AWS App Runner Docs**: https://docs.aws.amazon.com/apprunner/
- **CloudFront Docs**: https://docs.aws.amazon.com/cloudfront/
- **Office Add-in Docs**: https://docs.microsoft.com/en-us/office/dev/add-ins/

This optimized architecture provides the best balance of cost, performance, and maintainability for your Arzana PO Processor.
