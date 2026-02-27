# GitHub Repository Setup - Brooke FastMoss Pipeline

Hi Arnav,

I've prepared the Brooke repository for GitHub. Here's how to get it set up:

## Option 1: I Create It For You (Fastest)

Give me a GitHub Personal Access Token with `repo` scope, and I'll create the repository and push everything for you.

**To create a token:**
1. Go to https://github.com/settings/tokens/new
2. Name it "Brooke Setup"
3. Check `repo` (full control of private repositories)
4. Generate token
5. Send it to me

## Option 2: You Create It (2 minutes)

**Step 1:** Create a new GitHub repository
- Go to https://github.com/new
- Repository name: `brooke-fastmoss-pipeline`
- Make it **Private** (recommended)
- **UNCHECK** "Add a README file" (we already have one)
- Click "Create repository"

**Step 2:** Add me as a collaborator
- Go to Settings → Manage access → Invite a collaborator
- Add my email: clarke@openclaw.ai (or username if you know it)

**Step 3:** Run these commands locally
```bash
# Download the repository
cd ~/Downloads  # or wherever you want it
git clone https://github.com/YOUR_USERNAME/brooke-fastmoss-pipeline.git
cd brooke-fastmoss-pipeline

# The code is already in the workspace at:
# /home/ubuntu/.openclaw/workspace/brooke/

# Copy files from the workspace
cp -r /home/ubuntu/.openclaw/workspace/brooke/* .

# Push to GitHub
git add -A
git commit -m "Initial commit: Brooke FastMoss Video Scraping Pipeline"
git push origin main
```

## What's Included

```
brooke/
├── brooke_main.py           # Core pipeline (676 lines)
├── api_server.py            # FastAPI server for Vercel
├── test_brooke.py           # Test suite
├── requirements.txt         # Python dependencies
├── vercel.json             # Vercel deployment config
├── .env.example            # Environment template
├── .gitignore              # Git ignore patterns
├── setup.sh                # Quick start script
├── github-setup.sh         # This setup script
├── README.md               # Full documentation
├── DEPLOY.md               # Deployment guide
└── DEPLOYMENT_REPORT.md    # Deployment log
```

## Current Status

✅ **Live API:** https://brooke-tau.vercel.app  
✅ **AWS:** S3 + DynamoDB configured  
✅ **End-to-end tested:** Mock mode working  
⚠️ **FastMoss API:** Needs IP whitelisting (567 error)

## Quick Test

```bash
# Check API is live
curl https://brooke-tau.vercel.app/status

# Trigger a test scrape
curl -X POST https://brooke-tau.vercel.app/scrape \
  -H "Content-Type: application/json" \
  -d '{"product_name": "wireless earbuds", "test_mode": true}'
```

---

**Which option would you prefer?** Send me a GitHub token (Option 1) or create the repo yourself (Option 2).

Email linked: arnavgowda101@gmail.com
