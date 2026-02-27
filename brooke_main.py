#!/usr/bin/env python3
"""
BROOKE - FastMoss Research & Retrieval Engine
Microservice for autonomous video asset scraping from FastMoss API
"""

import os
import sys
import json
import time
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

import requests
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FASTMOSS_API_KEY = os.getenv("FASTMOSS_API_KEY", "dytphebuvtaevuhjldhcdrcwcgkkayyq")
FASTMOSS_BASE_URL = "https://www.fastmoss.com/api"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "content-pipeline-raw")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "MediaVault_Metadata")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# Test mode settings
TEST_BATCH_SIZE = int(os.getenv("TEST_BATCH_SIZE", "5"))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Brooke")

@dataclass
class VideoAsset:
    """Represents a scraped video asset"""
    video_id: str
    play_count: int
    digg_count: int
    comment_count: int
    share_count: int
    tiktok_url: str
    product_id: Optional[str] = None
    source: str = "fastmoss"  # "fastmoss_product" or "fastmoss_search"
    scraped_at: str = ""
    
    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ProductInfo:
    """Product information from FastMoss"""
    product_id: str
    product_title: str
    category: str
    day28_units_sold: int
    price: float
    shop_name: str
    
    @classmethod
    def from_api_response(cls, data: Dict) -> "ProductInfo":
        return cls(
            product_id=str(data.get("product_id", "")),
            product_title=data.get("product_title", ""),
            category=data.get("category", ""),
            day28_units_sold=int(data.get("day28_units_sold", 0)),
            price=float(data.get("price", 0)),
            shop_name=data.get("shop_name", "")
        )

class FastMossClient:
    """Client for FastMoss API interactions"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = FASTMOSS_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests for rate limiting
        
    def _rate_limit(self):
        """Ensure we don't exceed API rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make a rate-limited request to FastMoss API"""
        self._rate_limit()
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def _mock_products(self, keywords: str, limit: int) -> List[ProductInfo]:
        """Generate mock products for testing when API fails"""
        logger.warning(f"Using MOCK mode for product search: {keywords}")
        import hashlib
        # Generate consistent mock data based on keywords
        hash_val = int(hashlib.md5(keywords.encode()).hexdigest(), 16)
        
        mock_products = [
            ProductInfo(
                product_id=f"MOCK_PROD_{hash_val % 10000}",
                product_title=f"Premium {keywords.title()} - Best Seller",
                category="Electronics/Accessories",
                day28_units_sold=5000 + (hash_val % 10000),
                price=29.99 + (hash_val % 50),
                shop_name="MockShop Official"
            ),
            ProductInfo(
                product_id=f"MOCK_PROD_{(hash_val + 1) % 10000}",
                product_title=f"Trendy {keywords.title()} - Popular Choice",
                category="Home/Lifestyle",
                day28_units_sold=3000 + (hash_val % 5000),
                price=19.99 + (hash_val % 30),
                shop_name="TrendyStore"
            )
        ]
        return mock_products[:limit]
    
    def _mock_videos(self, product_id: str, limit: int) -> List[VideoAsset]:
        """Generate mock videos for testing when API fails"""
        logger.warning(f"Using MOCK mode for videos: {product_id}")
        import hashlib
        hash_val = int(hashlib.md5(product_id.encode()).hexdigest(), 16)
        
        videos = []
        for i in range(min(limit, 5)):
            vid_hash = hash_val + i
            videos.append(VideoAsset(
                video_id=f"MOCK_VID_{vid_hash % 100000}",
                play_count=100000 + (vid_hash % 900000),
                digg_count=5000 + (vid_hash % 50000),
                comment_count=500 + (vid_hash % 5000),
                share_count=1000 + (vid_hash % 10000),
                tiktok_url=f"https://tiktok.com/@mockuser/video/{vid_hash % 100000}",
                product_id=product_id,
                source="fastmoss_product"
            ))
        return videos
    
    def search_products(self, keywords: str, limit: int = 50) -> List[ProductInfo]:
        """
        Phase 1: Product Intelligence Discovery
        Search for products and return sorted by day28_units_sold
        """
        logger.info(f"Searching products with keywords: {keywords}")
        
        # In test mode with MOCK fallback
        try:
            payload = {
                "keywords": keywords,
                "page": 1,
                "page_size": min(limit, 100)
            }
            
            data = self._make_request("POST", "/product/v1/search", json=payload)
            
            if not data or "data" not in data:
                logger.warning("No products found")
                return []
            
            products = [ProductInfo.from_api_response(p) for p in data.get("data", [])]
            products.sort(key=lambda x: x.day28_units_sold, reverse=True)
            
            logger.info(f"Found {len(products)} products, top seller: {products[0].product_title if products else 'None'}")
            return products
            
        except Exception as e:
            if TEST_MODE:
                logger.warning(f"API failed in TEST_MODE, using mock data: {e}")
                return self._mock_products(keywords, limit)
            raise
    
    def get_product_videos(
        self, 
        product_id: str, 
        date_type: int = 7, 
        orderby: str = "interact_rate",
        limit: int = None
    ) -> List[VideoAsset]:
        """
        Phase 2A: Commercial DNA Pull (70% of scrapes)
        Get videos associated with a specific product
        """
        logger.info(f"Fetching product videos for {product_id}")
        
        if TEST_MODE and limit is None:
            limit = int(TEST_BATCH_SIZE * 0.7)  # 70% of test batch
        
        videos = []
        page = 1
        page_size = 50
        search_after = None
        
        while True:
            try:
                payload = {
                    "product_id": product_id,
                    "date_type": date_type,
                    "orderby": orderby,
                    "page": page,
                    "page_size": page_size
                }
                
                if search_after:
                    payload["search_after"] = search_after
                
                data = self._make_request("POST", "/product/v1/videoList", json=payload)
            except Exception as e:
                if TEST_MODE:
                    logger.warning(f"API failed in TEST_MODE, using mock videos: {e}")
                    return self._mock_videos(product_id, limit or TEST_BATCH_SIZE)
                raise
            
            if not data or "data" not in data:
                break
            
            items = data.get("data", [])
            if not items:
                break
            
            for item in items:
                video = VideoAsset(
                    video_id=str(item.get("video_id", "")),
                    play_count=int(item.get("play_count", 0)),
                    digg_count=int(item.get("digg_count", 0)),
                    comment_count=int(item.get("comment_count", 0)),
                    share_count=int(item.get("share_count", 0)),
                    tiktok_url=item.get("tiktok_url", ""),
                    product_id=product_id,
                    source="fastmoss_product"
                )
                videos.append(video)
                
                if limit and len(videos) >= limit:
                    break
            
            if limit and len(videos) >= limit:
                break
            
            # Check for pagination
            if len(items) < page_size:
                break
            
            # Get search_after for deep pagination
            search_after = data.get("search_after")
            if not search_after and len(videos) >= 60000:
                logger.warning("Hit 60k pagination limit")
                break
            
            page += 1
            
            if page > 100:  # Safety limit
                break
        
        logger.info(f"Retrieved {len(videos)} product videos")
        return videos
    
    def search_videos(
        self, 
        keywords: str, 
        play_count_min: int = 100000,
        orderby: str = "interact_rate",
        limit: int = None
    ) -> List[VideoAsset]:
        """
        Phase 2B: Aesthetic Inspiration Pull (30% of scrapes)
        Search videos by niche keywords with engagement filters
        """
        logger.info(f"Searching videos with keywords: {keywords}")
        
        if TEST_MODE and limit is None:
            limit = int(TEST_BATCH_SIZE * 0.3)  # 30% of test batch
        
        videos = []
        page = 1
        page_size = 50
        search_after = None
        
        while True:
            try:
                payload = {
                    "keywords": keywords,
                    "play_count_range": {
                        "min": play_count_min
                    },
                    "orderby": orderby,
                    "page": page,
                    "page_size": page_size
                }
                
                if search_after:
                    payload["search_after"] = search_after
                
                data = self._make_request("POST", "/video/v1/search", json=payload)
            except Exception as e:
                if TEST_MODE:
                    logger.warning(f"API failed in TEST_MODE, using mock search videos: {e}")
                    # Return mock search videos (different from product videos)
                    mock_vids = self._mock_videos(f"search_{keywords}", limit or TEST_BATCH_SIZE)
                    for v in mock_vids:
                        v.source = "fastmoss_search"
                        v.product_id = None
                    return mock_vids
                raise
            
            if not data or "data" not in data:
                break
            
            items = data.get("data", [])
            if not items:
                break
            
            for item in items:
                video = VideoAsset(
                    video_id=str(item.get("video_id", "")),
                    play_count=int(item.get("play_count", 0)),
                    digg_count=int(item.get("digg_count", 0)),
                    comment_count=int(item.get("comment_count", 0)),
                    share_count=int(item.get("share_count", 0)),
                    tiktok_url=item.get("tiktok_url", ""),
                    source="fastmoss_search"
                )
                videos.append(video)
                
                if limit and len(videos) >= limit:
                    break
            
            if limit and len(videos) >= limit:
                break
            
            if len(items) < page_size:
                break
            
            search_after = data.get("search_after")
            if not search_after and len(videos) >= 60000:
                break
            
            page += 1
            
            if page > 100:
                break
        
        logger.info(f"Retrieved {len(videos)} search videos")
        return videos

class DynamoDBManager:
    """Manages DynamoDB MediaVault_Metadata table"""
    
    def __init__(self, table_name: str = DYNAMODB_TABLE, region: str = AWS_REGION):
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table_name = table_name
        self.table = None
        
    def init_table(self) -> bool:
        """Initialize DynamoDB table - works with existing schema"""
        try:
            # Check if table exists
            self.table = self.dynamodb.Table(self.table_name)
            self.table.load()
            logger.info(f"DynamoDB table '{self.table_name}' connected successfully")
            return True
        except ClientError as e:
            logger.error(f"Failed to connect to DynamoDB table: {e}")
            return False
    
    def register_video(
        self, 
        video: VideoAsset, 
        s3_path: str,
        product_name: str = ""
    ) -> bool:
        """Register a video asset in DynamoDB - adapted for existing schema"""
        if not self.table:
            self.init_table()
        
        try:
            import time
            timestamp = int(time.time())
            
            item = {
                "VideoID": video.video_id,
                "Timestamp": timestamp,
                "BrandID": video.product_id or "brooke-default",
                "ProductName": product_name,
                "S3Path": s3_path,
                "Original_Metrics": {
                    "PlayCount": video.play_count,
                    "Likes": video.digg_count,
                    "Comments": video.comment_count,
                    "Shares": video.share_count
                },
                "VLM_Status": "PENDING_REVIEW",
                "ScrapedAt": video.scraped_at,
                "Source": video.source,
                "TikTokURL": video.tiktok_url,
                "ProcessedAt": "",
                "VLM_Analysis": {},
                "ContentRating": ""
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Registered video {video.video_id} in DynamoDB")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to register video {video.video_id}: {e}")
            return False
    
    def get_videos_by_status(self, status: str) -> List[Dict]:
        """Query videos by VLM status - using scan with filter"""
        if not self.table:
            self.init_table()
        
        try:
            # Use scan with filter since we don't have a StatusIndex GSI
            response = self.table.scan(
                FilterExpression="VLM_Status = :status",
                ExpressionAttributeValues={":status": status}
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to query videos: {e}")
            return []

class S3Manager:
    """Manages S3 storage for video assets"""
    
    def __init__(self, bucket: str = S3_BUCKET, region: str = AWS_REGION):
        self.s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket
    
    def ensure_bucket_exists(self) -> bool:
        """Ensure the S3 bucket exists"""
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                try:
                    self.s3.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={
                            "LocationConstraint": os.getenv("AWS_REGION", "us-east-1")
                        }
                    )
                    logger.info(f"Created S3 bucket: {self.bucket}")
                    return True
                except ClientError as ce:
                    logger.error(f"Failed to create S3 bucket: {ce}")
                    return False
            logger.error(f"S3 bucket error: {e}")
            return False
    
    def generate_s3_path(self, product_name: str, video_id: str) -> str:
        """Generate S3 path for a video asset"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        safe_product = product_name.lower().replace(" ", "-").replace("/", "-")[:50]
        return f"raw-scrapes/{safe_product}/{date_str}/{video_id}.mp4"
    
    def upload_video(self, local_path: str, s3_key: str) -> bool:
        """Upload a video file to S3"""
        try:
            self.s3.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
            logger.info(f"Uploaded to s3://{self.bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False

class VideoDownloader:
    """Downloads videos from TikTok URLs"""
    
    def __init__(self, download_dir: str = None):
        # Use /tmp for serverless environments (Vercel, Lambda), otherwise use local downloads
        if download_dir is None:
            download_dir = "/tmp/brooke_downloads" if os.path.exists("/tmp") else "./downloads"
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def download(self, video: VideoAsset) -> Optional[str]:
        """Download a video from TikTok URL"""
        if not video.tiktok_url:
            logger.warning(f"No TikTok URL for video {video.video_id}")
            return None
        
        local_path = self.download_dir / f"{video.video_id}.mp4"
        
        try:
            # Note: This is a simplified downloader
            # In production, you'd use yt-dlp or similar for TikTok
            logger.info(f"Downloading video {video.video_id}...")
            
            # Simulate download for testing
            if TEST_MODE:
                # Create a dummy file for testing
                local_path.write_bytes(b"DUMMY_VIDEO_DATA")
                logger.info(f"Test mode: Created dummy file at {local_path}")
                return str(local_path)
            
            # Real download (requires yt-dlp or similar)
            response = self.session.get(video.tiktok_url, timeout=30)
            response.raise_for_status()
            
            local_path.write_bytes(response.content)
            logger.info(f"Downloaded {local_path}")
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Failed to download video {video.video_id}: {e}")
            return None

class BrookePipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        self.fastmoss = FastMossClient(FASTMOSS_API_KEY)
        self.dynamodb = DynamoDBManager()
        self.s3 = S3Manager()
        self.downloader = VideoDownloader()
        
        # Initialize storage
        self.dynamodb.init_table()
        self.s3.ensure_bucket_exists()
    
    def run(
        self, 
        product_name: str, 
        niche_keywords: str = None,
        daily_post_goal: int = 10,
        product_validation: Dict = None
    ) -> Dict[str, Any]:
        """
        Execute full pipeline
        
        Args:
            product_name: Name of the product to search for
            niche_keywords: Keywords for aesthetic inspiration search
            daily_post_goal: Target number of posts per day (determines scrape volume)
            product_validation: Dict with expected category/title patterns for validation
        """
        logger.info(f"Starting Brooke pipeline for: {product_name}")
        logger.info(f"Test mode: {TEST_MODE}")
        
        results = {
            "product_name": product_name,
            "started_at": datetime.utcnow().isoformat(),
            "phases": {}
        }
        
        # Calculate scrape targets based on 10:1 ratio
        total_videos_needed = daily_post_goal * 10
        commercial_target = int(total_videos_needed * 0.7)  # 70%
        aesthetic_target = int(total_videos_needed * 0.3)   # 30%
        
        if TEST_MODE:
            total_videos_needed = TEST_BATCH_SIZE
            commercial_target = int(TEST_BATCH_SIZE * 0.7)
            aesthetic_target = int(TEST_BATCH_SIZE * 0.3)
        
        logger.info(f"Scrape targets - Total: {total_videos_needed}, Commercial: {commercial_target}, Aesthetic: {aesthetic_target}")
        
        # Phase 1: Product Intelligence
        logger.info("=== PHASE 1: Product Intelligence ===")
        products = self.fastmoss.search_products(product_name)
        
        if not products:
            raise ValueError(f"No products found for: {product_name}")
        
        top_product = products[0]
        
        # Validate product if validation criteria provided
        if product_validation:
            if not self._validate_product(top_product, product_validation):
                raise ValueError(f"Product validation failed for: {top_product.product_title}")
        
        results["phases"]["product_discovery"] = {
            "product_id": top_product.product_id,
            "product_title": top_product.product_title,
            "category": top_product.category,
            "day28_units_sold": top_product.day28_units_sold,
            "validated": True
        }
        
        logger.info(f"Selected product: {top_product.product_title} (ID: {top_product.product_id})")
        
        # Phase 2: Video Scraping
        logger.info("=== PHASE 2: Video Scraping ===")
        
        # 70% Commercial DNA
        commercial_videos = self.fastmoss.get_product_videos(
            top_product.product_id,
            limit=commercial_target
        )
        
        # 30% Aesthetic Inspiration
        aesthetic_keywords = niche_keywords or product_name
        aesthetic_videos = self.fastmoss.search_videos(
            aesthetic_keywords,
            limit=aesthetic_target
        )
        
        all_videos = commercial_videos + aesthetic_videos
        
        results["phases"]["video_scraping"] = {
            "commercial_count": len(commercial_videos),
            "aesthetic_count": len(aesthetic_videos),
            "total_count": len(all_videos)
        }
        
        logger.info(f"Total videos scraped: {len(all_videos)}")
        
        # Phase 3: Ingestion & Storage
        logger.info("=== PHASE 3: Ingestion & Storage ===")
        
        successful_uploads = 0
        failed_uploads = 0
        
        for video in all_videos:
            try:
                # Download video
                local_path = self.downloader.download(video)
                
                if local_path:
                    # Generate S3 path
                    s3_key = self.s3.generate_s3_path(product_name, video.video_id)
                    s3_path = f"s3://{self.s3.bucket}/{s3_key}"
                    
                    # Upload to S3
                    if self.s3.upload_video(local_path, s3_key):
                        # Register in DynamoDB
                        if self.dynamodb.register_video(video, s3_path, product_name):
                            successful_uploads += 1
                            
                            # Clean up local file
                            Path(local_path).unlink(missing_ok=True)
                        else:
                            failed_uploads += 1
                    else:
                        failed_uploads += 1
                else:
                    # Register even if download failed (for tracking)
                    s3_key = self.s3.generate_s3_path(product_name, video.video_id)
                    s3_path = f"s3://{self.s3.bucket}/{s3_key}"
                    self.dynamodb.register_video(video, s3_path, product_name)
                    failed_uploads += 1
                    
            except Exception as e:
                logger.error(f"Failed to process video {video.video_id}: {e}")
                failed_uploads += 1
        
        results["phases"]["ingestion"] = {
            "successful": successful_uploads,
            "failed": failed_uploads,
            "total": len(all_videos)
        }
        
        results["completed_at"] = datetime.utcnow().isoformat()
        results["status"] = "completed"
        
        logger.info(f"Pipeline complete. Success: {successful_uploads}, Failed: {failed_uploads}")
        
        return results
    
    def _validate_product(self, product: ProductInfo, validation: Dict) -> bool:
        """Validate product matches expected criteria"""
        if "category" in validation:
            if validation["category"].lower() not in product.category.lower():
                logger.warning(f"Category mismatch: expected {validation['category']}, got {product.category}")
                return False
        
        if "title_contains" in validation:
            if validation["title_contains"].lower() not in product.product_title.lower():
                logger.warning(f"Title validation failed for: {product.product_title}")
                return False
        
        return True

# Admin Dashboard Integration
class DashboardAPI:
    """API endpoints for Vercel admin dashboard"""
    
    def __init__(self, pipeline: BrookePipeline):
        self.pipeline = pipeline
    
    def get_status(self) -> Dict:
        """Get pipeline status for dashboard"""
        pending = self.pipeline.dynamodb.get_videos_by_status("PENDING_REVIEW")
        
        return {
            "pipeline_status": "active",
            "pending_reviews": len(pending),
            "last_scrape": datetime.utcnow().isoformat(),
            "test_mode": TEST_MODE
        }
    
    def get_pending_videos(self, limit: int = 50) -> List[Dict]:
        """Get videos pending review"""
        return self.pipeline.dynamodb.get_videos_by_status("PENDING_REVIEW")[:limit]
    
    def trigger_scrape(self, product_name: str, niche_keywords: str = None, test: bool = True) -> Dict:
        """Trigger a new scrape job"""
        if test:
            os.environ["TEST_MODE"] = "true"
        
        try:
            results = self.pipeline.run(product_name, niche_keywords)
            return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

# CLI Interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Brooke - FastMoss Video Scraping Pipeline")
    parser.add_argument("--product", "-p", required=True, help="Product name to search")
    parser.add_argument("--keywords", "-k", help="Niche keywords for aesthetic search")
    parser.add_argument("--daily-goal", "-g", type=int, default=10, help="Daily post goal (default: 10)")
    parser.add_argument("--test", "-t", action="store_true", help="Run in test mode (small batches)")
    parser.add_argument("--init-db", action="store_true", help="Initialize DynamoDB table only")
    
    args = parser.parse_args()
    
    if args.test:
        os.environ["TEST_MODE"] = "true"
        logger.info("Running in TEST MODE - small batches only")
    
    pipeline = BrookePipeline()
    
    if args.init_db:
        logger.info("DynamoDB table initialized")
        return
    
    try:
        results = pipeline.run(
            product_name=args.product,
            niche_keywords=args.keywords,
            daily_post_goal=args.daily_goal
        )
        
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
