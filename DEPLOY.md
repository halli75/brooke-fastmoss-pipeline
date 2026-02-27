# Brooke Deployment Guide

## Local Development

### 1. Setup
```bash
cd /home/ubuntu/.openclaw/workspace/brooke
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - FASTMOSS_API_KEY (already set)
```

### 3. Initialize Infrastructure
```bash
# Create DynamoDB table
python brooke_main.py --init-db

# Verify S3 bucket exists (creates if not)
python -c "from brooke_main import S3Manager; S3Manager().ensure_bucket_exists()"
```

### 4. Test Run
```bash
# Test with 5 videos (test mode)
python brooke_main.py -p "wireless earbuds" -k "earbuds review" --test
```

## AWS Setup

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/MediaVault_Metadata"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::content-pipeline-raw",
        "arn:aws:s3:::content-pipeline-raw/*"
      ]
    }
  ]
}
```

### DynamoDB Table Creation

If you prefer manual creation:

```bash
aws dynamodb create-table \
  --table-name MediaVault_Metadata \
  --attribute-definitions \
    AttributeName=VideoID,AttributeType=S \
    AttributeName=Product_ID,AttributeType=S \
    AttributeName=VLM_Status,AttributeType=S \
    AttributeName=ScrapedAt,AttributeType=S \
  --key-schema AttributeName=VideoID,KeyType=HASH \
  --global-secondary-indexes \
    "IndexName=ProductIndex,KeySchema=[{AttributeName=Product_ID,KeyType=HASH},{AttributeName=ScrapedAt,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
    "IndexName=StatusIndex,KeySchema=[{AttributeName=VLM_Status,KeyType=HASH},{AttributeName=ScrapedAt,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
  --billing-mode PAY_PER_REQUEST
```

## Vercel Deployment

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Deploy
```bash
cd /home/ubuntu/.openclaw/workspace/brooke
vercel

# Or for production
vercel --prod
```

### 3. Environment Variables
Set these in Vercel dashboard:
- `FASTMOSS_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET`
- `DYNAMODB_TABLE`

## Docker Deployment (Alternative)

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "api_server.py"]
```

### Build & Run
```bash
docker build -t brooke-api .
docker run -p 8000:8000 --env-file .env brooke-api
```

## Production Checklist

- [ ] Move API key from hardcoded to environment variable
- [ ] Set up proper AWS credentials with limited permissions
- [ ] Configure S3 bucket with proper CORS for video access
- [ ] Set up CloudWatch logging
- [ ] Enable DynamoDB point-in-time recovery
- [ ] Configure API rate limits
- [ ] Set up monitoring/alerting
- [ ] Test TikTok download with yt-dlp in production
- [ ] Verify Vercel CORS settings match your domain

## Monitoring

### Check Pipeline Status
```bash
curl https://your-api.vercel.app/status
```

### View Recent Jobs
```bash
curl https://your-api.vercel.app/jobs
```

### Get Pending Reviews
```bash
curl https://your-api.vercel.app/pending
```

## Troubleshooting

### "No module named 'boto3'"
```bash
source venv/bin/activate
pip install boto3
```

### "Table does not exist"
```bash
python brooke_main.py --init-db
```

### "Access Denied" on S3
- Check IAM permissions
- Verify bucket name in environment

### FastMoss API Errors
- Verify API key is valid
- Check rate limits (add delays if needed)
- Review API response format changes

## Scheduled Scraping

Use cron or Vercel Cron Jobs:

```javascript
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/scrape",
      "schedule": "0 2 * * *"
    }
  ]
}
```

Or external scheduler calling:
```bash
curl -X POST https://your-api.vercel.app/scrape \
  -H "Authorization: Bearer $CRON_SECRET" \
  -d '{"product_name": "your-product", "test_mode": false}'
```
