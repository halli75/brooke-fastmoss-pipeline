#!/usr/bin/env python3
"""
Brooke API Server - FastAPI endpoints for Vercel admin dashboard
Serverless-optimized version
"""

import os
import sys
from typing import List, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Brooke API",
    description="FastMoss Video Scraping Pipeline API",
    version="1.0.0"
)

# CORS for Vercel dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy initialization globals
_pipeline = None
_dashboard = None
jobs = {}

def get_pipeline():
    """Lazy initialization of pipeline"""
    global _pipeline, _dashboard
    if _pipeline is None:
        from brooke_main import BrookePipeline, DashboardAPI, TEST_MODE
        _pipeline = BrookePipeline()
        _dashboard = DashboardAPI(_pipeline)
    return _pipeline, _dashboard

# Pydantic models
class ScrapeRequest(BaseModel):
    product_name: str
    niche_keywords: Optional[str] = None
    daily_post_goal: int = 10
    test_mode: bool = True

class ScrapeResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    results: Optional[dict] = None
    error: Optional[str] = None

class VideoStatus(BaseModel):
    video_id: str
    product_id: str
    status: str
    scraped_at: str
    s3_path: str
    metrics: dict

class PipelineStatus(BaseModel):
    pipeline_status: str
    pending_reviews: int
    last_scrape: str
    test_mode: bool

def run_scrape_job(job_id: str, product_name: str, niche_keywords: Optional[str], 
                   daily_post_goal: int, test_mode: bool):
    """Background task for scraping"""
    import os
    if test_mode:
        os.environ["TEST_MODE"] = "true"
    else:
        os.environ["TEST_MODE"] = "false"
    
    try:
        pipeline, _ = get_pipeline()
        results = pipeline.run(
            product_name=product_name,
            niche_keywords=niche_keywords,
            daily_post_goal=daily_post_goal
        )
        jobs[job_id] = {"status": "completed", "results": results, "completed_at": datetime.utcnow().isoformat()}
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e), "failed_at": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "Brooke API - FastMoss Video Scraping Pipeline", "status": "active", "version": "1.0.0"}

@app.get("/status")
async def get_status():
    """Get current pipeline status"""
    try:
        _, dashboard = get_pipeline()
        status = dashboard.get_status()
        return PipelineStatus(
            pipeline_status=status.get("pipeline_status", "unknown"),
            pending_reviews=status.get("pending_reviews", 0),
            last_scrape=status.get("last_scrape", ""),
            test_mode=status.get("test_mode", True)
        )
    except Exception as e:
        return {"error": str(e), "pipeline_status": "error"}

@app.get("/pending")
async def get_pending_videos(limit: int = 50):
    """Get videos pending VLM review"""
    try:
        _, dashboard = get_pipeline()
        videos = dashboard.get_pending_videos(limit)
        return [
            VideoStatus(
                video_id=v.get("VideoID", ""),
                product_id=v.get("BrandID", ""),
                status=v.get("VLM_Status", ""),
                scraped_at=v.get("ScrapedAt", ""),
                s3_path=v.get("S3Path", ""),
                metrics=v.get("Original_Metrics", {})
            ) for v in videos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Trigger a new scraping job"""
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    jobs[job_id] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
    
    background_tasks.add_task(
        run_scrape_job,
        job_id,
        request.product_name,
        request.niche_keywords,
        request.daily_post_goal,
        request.test_mode
    )
    
    return ScrapeResponse(
        success=True,
        job_id=job_id,
        message=f"Scraping job started in {'TEST' if request.test_mode else 'PRODUCTION'} mode"
    )

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a scraping job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    return {"jobs": jobs}

@app.post("/validate")
async def validate_product(product_name: str):
    """Validate a product exists before full scrape"""
    try:
        pipeline, _ = get_pipeline()
        products = pipeline.fastmoss.search_products(product_name, limit=5)
        if not products:
            return {"valid": False, "message": "No products found"}
        
        return {
            "valid": True,
            "products": [
                {
                    "product_id": p.product_id,
                    "title": p.product_title,
                    "category": p.category,
                    "day28_units_sold": p.day28_units_sold
                } for p in products[:3]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
