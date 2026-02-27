# Brooke - FastMoss Video Scraping Pipeline

**Brooke** is a specialized Research & Retrieval Engine that autonomously scrapes high-velocity video assets from FastMoss to fuel your content pipeline.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Admin Dashboard│────▶│   Brooke API     │────▶│  FastMoss API   │
│   (Vercel)      │◄────│   (FastAPI)      │◄────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Brooke Pipeline │
                       │                  │
                       │ ┌──────────────┐ │
                       │ │ Phase 1:     │ │
                       │ │ Product      │ │
                       │ │ Discovery    │ │
                       │ └──────────────┘ │
                       │ ┌──────────────┐ │
                       │ │ Phase 2:     │ │
                       │ │ Video Scraping│ │
                       │ │ (70/30 Split)│ │
                       │ └──────────────┘ │
                       │ ┌──────────────┐ │
                       │ │ Phase 3:     │ │
                       │ │ Ingestion    │ │
                       │ │ & Storage    │ │
                       │ └──────────────┘ │
                       └──────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              ┌──────────┐            ┌──────────┐
              │  S3      │            │ DynamoDB │
              │  Bucket  │            │ MediaVault│
              │          │            │ Metadata │
              └──────────┘            └──────────┘
```

## Quick Start

### 1. Setup Environment

```bash
cd brooke
cp .env.example .env
# Edit .env with your credentials
```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python brooke_main.py --init-db
```

### 4. Run Test Scrape

```bash
python brooke_main.py -p "wireless earbuds" -k "earbuds review" --test
```

## Pipeline Phases

### Phase 1: Product Intelligence (Discovery)
- Searches FastMoss products by keyword
- Selects product with highest `day28_units_sold`
- Validates product matches expected niche

### Phase 2: High-Volume Video Scraping
**70% Commercial DNA Pull:**
- Uses `/product/v1/videoList` endpoint
- Filters by last 7 days, sorted by interaction rate
- Targets videos directly linked to product

**30% Aesthetic Inspiration Pull:**
- Uses `/video/v1/search` endpoint
- Filters by minimum 100k plays
- Broad niche keyword targeting

**10:1 Scrape-to-Post Ratio:**
- If daily post goal = 10, scrapes 100 videos
- 70 commercial + 30 aesthetic

### Phase 3: Automated Ingestion
- Downloads videos from TikTok URLs
- Uploads to S3: `s3://bucket/raw-scrapes/product-name/YYYY-MM-DD/video_id.mp4`
- Registers in DynamoDB with status `PENDING_REVIEW`

## API Endpoints

### Start API Server
```bash
python api_server.py
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/status` | GET | Pipeline status |
| `/pending` | GET | Videos pending review |
| `/scrape` | POST | Trigger new scrape job |
| `/job/{id}` | GET | Check job status |
| `/jobs` | GET | List all jobs |
| `/validate` | POST | Validate product exists |

### Example API Usage

```bash
# Start a scrape job
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "wireless earbuds",
    "niche_keywords": "earbuds review unboxing",
    "daily_post_goal": 10,
    "test_mode": true
  }'

# Check status
curl http://localhost:8000/status

# Get pending videos
curl http://localhost:8000/pending
```

## DynamoDB Schema

### Table: `MediaVault_Metadata`

| Field | Type | Description |
|-------|------|-------------|
| `VideoID` | String (PK) | Unique video identifier |
| `Product_ID` | String | FastMoss product ID |
| `ProductName` | String | Human-readable product name |
| `S3Path` | String | Full S3 path to video |
| `TikTokURL` | String | Original TikTok URL |
| `Original_Metrics` | Map | `{PlayCount, Likes, Comments, Shares}` |
| `VLM_Status` | String | `PENDING_REVIEW`, `APPROVED`, `REJECTED` |
| `ScrapedAt` | String | ISO timestamp |
| `Source` | String | `fastmoss_product` or `fastmoss_search` |

### Global Secondary Indexes
- `ProductIndex`: Query by Product_ID + ScrapedAt
- `StatusIndex`: Query by VLM_Status + ScrapedAt

## Testing

```bash
# Run all tests
python test_brooke.py

# Test specific phase
python test_brooke.py --phase 1  # Product discovery
python test_brooke.py --phase 2  # Video scraping
python test_brooke.py --phase 3  # Storage
```

## Vercel Dashboard Integration

The API server provides CORS-enabled endpoints for your Vercel admin dashboard:

```javascript
// Example dashboard usage
const response = await fetch('https://your-brooke-api.com/scrape', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    product_name: 'wireless earbuds',
    test_mode: true
  })
});

const job = await response.json();
// Poll for completion
const status = await fetch(`https://your-brooke-api.com/job/${job.job_id}`);
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTMOSS_API_KEY` | FastMoss API key | (required) |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET` | S3 bucket name | `content-pipeline-raw` |
| `DYNAMODB_TABLE` | DynamoDB table name | `MediaVault_Metadata` |
| `TEST_MODE` | Enable test mode | `false` |
| `TEST_BATCH_SIZE` | Videos per test run | `5` |

## Rate Limiting & Guardrails

- 500ms minimum between API requests
- Max 60,000 results per query (uses `search_after` pagination)
- 24-hour scrape cycles recommended
- Test mode limits batches to 5 videos

## File Structure

```
brooke/
├── brooke_main.py      # Core pipeline logic
├── api_server.py       # FastAPI web server
├── test_brooke.py      # Test suite
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

## Notes

- **Test Mode**: Always test with `--test` flag before production runs
- **TikTok Downloads**: Uses simplified downloader; production should use `yt-dlp`
- **AWS Credentials**: Required for S3 and DynamoDB operations
- **API Key**: FastMoss API key is hardcoded for testing; move to env var in production
