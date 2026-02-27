#!/usr/bin/env python3
"""
Brooke CLI - Command line interface for testing the pipeline
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brooke_main import BrookePipeline

def test_product_discovery():
    """Test Phase 1: Product Intelligence"""
    print("\n" + "="*60)
    print("TEST: Phase 1 - Product Discovery")
    print("="*60)
    
    pipeline = BrookePipeline()
    
    # Test with a generic product
    products = pipeline.fastmoss.search_products("wireless earbuds", limit=10)
    
    if products:
        print(f"✓ Found {len(products)} products")
        top = products[0]
        print(f"✓ Top product: {top.product_title}")
        print(f"  - ID: {top.product_id}")
        print(f"  - Category: {top.category}")
        print(f"  - 28-day sales: {top.day28_units_sold}")
        return top.product_id
    else:
        print("✗ No products found")
        return None

def test_video_scraping(product_id: str):
    """Test Phase 2: Video Scraping"""
    print("\n" + "="*60)
    print("TEST: Phase 2 - Video Scraping")
    print("="*60)
    
    pipeline = BrookePipeline()
    
    # Test commercial DNA pull
    print("\nTesting Commercial DNA Pull (70%)...")
    commercial_videos = pipeline.fastmoss.get_product_videos(
        product_id, 
        limit=3  # Small batch for testing
    )
    print(f"✓ Retrieved {len(commercial_videos)} commercial videos")
    
    if commercial_videos:
        v = commercial_videos[0]
        print(f"  - Sample: {v.video_id}")
        print(f"    Plays: {v.play_count}, Likes: {v.digg_count}")
    
    # Test aesthetic inspiration pull
    print("\nTesting Aesthetic Inspiration Pull (30%)...")
    aesthetic_videos = pipeline.fastmoss.search_videos(
        "wireless earbuds review",
        limit=2
    )
    print(f"✓ Retrieved {len(aesthetic_videos)} aesthetic videos")
    
    return commercial_videos + aesthetic_videos

def test_storage(videos):
    """Test Phase 3: Storage"""
    print("\n" + "="*60)
    print("TEST: Phase 3 - Storage & Registration")
    print("="*60)
    
    pipeline = BrookePipeline()
    
    # Test DynamoDB
    print("\nTesting DynamoDB...")
    test_video = videos[0] if videos else None
    
    if test_video:
        s3_path = f"s3://test-bucket/test-path/{test_video.video_id}.mp4"
        success = pipeline.dynamodb.register_video(test_video, s3_path, "Test Product")
        if success:
            print(f"✓ Registered video {test_video.video_id} in DynamoDB")
        else:
            print(f"✗ Failed to register video")
    
    # Test S3 path generation
    print("\nTesting S3 path generation...")
    s3_key = pipeline.s3.generate_s3_path("Test Product", "vid123")
    print(f"✓ Generated path: {s3_key}")

def test_full_pipeline():
    """Test complete pipeline in test mode"""
    print("\n" + "="*60)
    print("TEST: Full Pipeline (Test Mode)")
    print("="*60)
    
    os.environ["TEST_MODE"] = "true"
    os.environ["TEST_BATCH_SIZE"] = "5"
    
    pipeline = BrookePipeline()
    
    try:
        results = pipeline.run(
            product_name="wireless earbuds",
            niche_keywords="earbuds review unboxing",
            daily_post_goal=1  # Will scrape 10 videos (10:1 ratio)
        )
        
        print("\n✓ Pipeline completed successfully!")
        print(f"\nResults Summary:")
        print(f"  - Product: {results['phases']['product_discovery']['product_title']}")
        print(f"  - Videos scraped: {results['phases']['video_scraping']['total_count']}")
        print(f"  - Successfully ingested: {results['phases']['ingestion']['successful']}")
        print(f"  - Failed: {results['phases']['ingestion']['failed']}")
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Brooke Test Suite")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                       help="Test specific phase or all")
    parser.add_argument("--product-id", help="Specific product ID for testing")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("BROOKE TEST SUITE")
    print("="*60)
    
    if args.phase in ["1", "all"]:
        product_id = test_product_discovery()
    else:
        product_id = args.product_id
    
    if args.phase in ["2", "all"] and product_id:
        videos = test_video_scraping(product_id)
    else:
        videos = []
    
    if args.phase in ["3", "all"]:
        test_storage(videos)
    
    if args.phase == "all":
        test_full_pipeline()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
