from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import time
import boto3
import requests
import io
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):  # Reduce excessive scrolling
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def download_and_upload_image(src, idx):
    try:
        response = requests.get(src, stream=True, timeout=5)
        if response.status_code == 200:
            image_data = io.BytesIO(response.content)
            s3_key = f"images/image_{idx}.jpg"
            s3_client.upload_fileobj(image_data, S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/jpeg"})
            return generate_s3_url(S3_BUCKET_NAME, S3_REGION, s3_key)
    except Exception as e:
        print(f"Failed to download {src}: {e}")
    return None

# @app.post("/scrape/")
def capture_and_upload(url: str):
    driver = setup_driver()
    uploaded_urls = []

    try:
        driver.get(url)
        time.sleep(3)  # Allow page to load

        scroll_page(driver)  # Optimized scrolling

        images = driver.find_elements(By.TAG_NAME, "img")
        if not images:
            raise HTTPException(status_code=404, detail="No images found on the page.")

        image_sources = [img.get_attribute("src") for img in images if img.get_attribute("src") and img.get_attribute("src").startswith("http")]

        # Use threading to speed up downloads and uploads
        with ThreadPoolExecutor(max_workers=5) as executor:
            uploaded_urls = list(filter(None, executor.map(download_and_upload_image, image_sources, range(len(image_sources)))))

    finally:
        driver.quit()

    return {"images": uploaded_urls}
