from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Brooke API - AWS EB Deployment", "status": "active", "region": "eu-west-1"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "brooke-eb", "region": "eu-west-1"}

@app.get("/status")
def status():
    return {
        "pipeline_status": "active",
        "test_mode": True,
        "region": "eu-west-1",
        "source": "elastic-beanstalk",
        "note": "AWS EB deployment for IP bypass"
    }

@app.post("/scrape")
def scrape(product_name: str = "test", test_mode: bool = True):
    return {
        "success": True,
        "job_id": "eb_test_job",
        "message": "Scrape request received on AWS EB (fresh IP from eu-west-1)",
        "test_mode": test_mode,
        "product_name": product_name,
        "deployment": "elastic-beanstalk-eu-west-1"
    }
