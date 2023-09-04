import requests
import os
import json
import csv
from datetime import datetime

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_TOKEN = os.environ.get('GITHUB_TOKEN')
GIST_ID = os.environ.get('NOTIFYBOT_GIST')
FILE_NAME = 'notifybot.json'
BOT_USER_ID = 35748

def fetch_last_processed_ids():
    try:
        resp = requests.get(GIST_URL)
        resp.raise_for_status()
        data = resp.json()
        return data
    except requests.RequestException as e:
        logging.error(f"Failed to fetch processed IDs from Gist. Error: {e}")
        return {}

def save_processed_id(community, post_id):
    data = fetch_last_processed_ids()
    data[community]['last_processed_id'] = post_id
    
    headers = {
        'Authorization': f'token {GIST_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "files": {
            FILE_NAME: {
                "content": json.dumps(data, indent=4)
            }
        }
    }

    try:
        resp = requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=headers, json=payload)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to update processed ID for {community}. Error: {e}. Resp: {resp}")

def send_dm(thread_id, message):
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    resp = requests.post(f'https://squabblr.co/api/message-threads/{thread_id}/messages', data={"content": message, "user_id": BOT_USER_ID}, headers=headers)
    return resp.json()

def get_latest_posts():
    processed_ids = fetch_last_processed_ids()

    for community, data in processed_ids.items():
        last_processed_id = data['last_processed_id']

        logging.info(f"Checking posts for community: {community}")
        response = requests.get(f'https://squabblr.co/api/s/{community}/posts?page=1&sort=new&')

        if response.status_code != 200:
            logging.warning(f"Failed to fetch posts for community: {community}")
            continue

        posts = response.json()["data"]
        for post in posts:
            post_id = post['id']

            if post_id <= last_processed_id:
                continue

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    get_latest_posts()
