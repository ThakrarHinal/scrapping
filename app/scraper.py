from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import time
import cv2
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Initialize FastAPI app
app = FastAPI()

# AWS S3 Configuration
S3_BUCKET_NAME = "scrap-project-bucket-demo"
S3_REGION = "eu-north-1"
s3_client = boto3.client("s3")

class ScraperRequest(BaseModel):
    url: str

def generate_s3_url(bucket, region, file_key):
    return f"https://{bucket}.s3.{region}.amazonaws.com/{file_key}"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# @app.post("/scrape/")  # Changed to POST to accept JSON body
def capture_and_upload(url: str):
    driver = setup_driver()
    uploaded_urls = {"frames": [], "video": None}

    try:
        driver.get(url)  # Use URL from request body
        time.sleep(5)

        rotation_area = driver.find_element("tag name", "canvas")
        action = ActionChains(driver)

        frame_files = []
        for i in range(36):
            action.click_and_hold(rotation_area).move_by_offset(10, 0).release().perform()
            time.sleep(0.2)
            frame_file = f"frame_{i:03d}.png"
            driver.save_screenshot(frame_file)

            if not os.path.exists(frame_file):
                continue

            frame_files.append(frame_file)
            s3_key = f"frames/{frame_file}"
            s3_client.upload_file(frame_file, S3_BUCKET_NAME, s3_key)
            uploaded_urls["frames"].append(generate_s3_url(S3_BUCKET_NAME, S3_REGION, s3_key))

        if not frame_files:
            raise HTTPException(status_code=500, detail="No frames were captured.")

        first_frame = cv2.imread(frame_files[0])
        height, width, _ = first_frame.shape
        output_video = "360_view_video.mp4"
        video = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*"mp4v"), 30, (width, height))

        for frame_file in frame_files:
            frame = cv2.imread(frame_file)
            if frame is not None:
                video.write(frame)

        video.release()
        s3_video_key = f"videos/{output_video}"
        s3_client.upload_file(output_video, S3_BUCKET_NAME, s3_video_key)
        uploaded_urls["video"] = generate_s3_url(S3_BUCKET_NAME, S3_REGION, s3_video_key)

        os.remove(output_video)
        os.remove(frame_file)

    finally:
        driver.quit()

    return uploaded_urls
