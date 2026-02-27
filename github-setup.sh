#!/bin/bash
# GitHub Repository Setup Script for Brooke
# Run this on your local machine after creating an empty GitHub repo

echo "=========================================="
echo "Brooke GitHub Repository Setup"
echo "=========================================="
echo ""

# Instructions for Arnav
echo "Step 1: Create a new GitHub repository"
echo "  - Go to https://github.com/new"
echo "  - Name it: brooke-fastmoss-pipeline"
echo "  - Make it private (recommended)"
echo "  - DON'T initialize with README (we already have one)"
echo ""

# Show current remotes
echo "Step 2: After creating the repo, run these commands:"
echo ""
echo "  cd /path/to/brooke"
echo "  git remote add origin https://github.com/YOUR_USERNAME/brooke-fastmoss-pipeline.git"
echo "  git push -u origin main"
echo ""

# Show what will be pushed
echo "The following files will be pushed:"
git ls-files | head -20
echo ""
echo "Total files: $(git ls-files | wc -l)"
echo ""

# Show commit history
echo "Commit history:"
git log --oneline
echo ""

echo "=========================================="
echo "Repository Contents:"
echo "=========================================="
echo ""
echo "📁 Core Files:"
echo "  - brooke_main.py      Main pipeline logic"
echo "  - api_server.py       FastAPI server for Vercel"
echo "  - test_brooke.py      Test suite"
echo ""
echo "📁 Configuration:"
echo "  - requirements.txt    Python dependencies"
echo "  - vercel.json         Vercel deployment config"
echo "  - .env.example        Environment template"
echo ""
echo "📁 Documentation:"
echo "  - README.md           Full documentation"
echo "  - DEPLOY.md           Deployment guide"
echo "  - DEPLOYMENT_REPORT.md Deployment log"
echo ""
echo "=========================================="
echo "Done! Repository is ready to push."
echo "=========================================="
