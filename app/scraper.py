from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import time
import boto3
import requests
import cv2
import numpy as np
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

# @app.post("/scrape/")
def capture_and_upload(url: str):
    driver = setup_driver()
    uploaded_urls = []
    image_files = []

    try:
        driver.get(url)
        time.sleep(3)  # Allow initial load

        # Scroll multiple times to load all images
        for _ in range(5):  # Increase this value if images are missing
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight / 4);")
            time.sleep(2)

        images = driver.find_elements(By.TAG_NAME, "img")
        if not images:
            raise HTTPException(status_code=404, detail="No images found on the page.")

        for idx, img in enumerate(images):
            src = img.get_attribute("src")
            if src and src.startswith("http"):

                image_filename = f"image_{idx}.jpg"
                response = requests.get(src, stream=True)

                if response.status_code == 200:
                    with open(image_filename, "wb") as file:
                        for chunk in response.iter_content(1024):
                            file.write(chunk)

                    # Verify OpenCV can read the image
                    # img_cv = cv2.imread(image_filename)
                    # if img_cv is not None:
                    #     # Resize to a standard resolution (e.g., 1280x720)
                    #     img_resized = cv2.resize(img_cv, (1280, 720))
                    #     cv2.imwrite(image_filename, img_resized)

                    #     image_files.append(image_filename)
                        # print("checking time>>>>")

                       

        # Cleanup image files
        for img_file in image_files:
             # Upload to S3 with correct content type
            s3_key = f"images/{img_file}"
            s3_client.upload_file(img_file, S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/jpeg"})
            uploaded_urls.append(generate_s3_url(S3_BUCKET_NAME, S3_REGION, s3_key))
            os.remove(img_file)
    
    finally:
        driver.quit()

    return {"images": uploaded_urls}
