#!/bin/bash
cd /home/ubuntu/scraper_project
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
