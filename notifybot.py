import requests
import os
import json
import csv
from datetime import datetime

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_TOKEN = os.environ.get('GITHUB_TOKEN')
GIST_ID = os.environ.get('AUTORESPONDER_GIST')
FILE_NAME = 'notifier-timestamp.json'
CSV_PATH = 'csv/notifier.csv'
BOT_USER_ID = 35748

def get_last_timestamp(community_name):
    resp = requests.get(f'https://api.github.com/gists/{GIST_ID}', headers={'Authorization': f'token {GIST_TOKEN}'})
    data = resp.json()
    timestamps = data['files'][FILE_NAME]['content']
    timestamps_dict = eval(timestamps)  # Convert the string representation of dictionary back to a dictionary
    return datetime.strptime(timestamps_dict.get(community_name, '2000-01-01T00:00:00.000000Z'), '%Y-%m-%dT%H:%M:%S.%fZ')

def save_last_timestamp(community_name, timestamp):
    current_data = requests.get(f'https://api.github.com/gists/{GIST_ID}', headers={'Authorization': f'token {GIST_TOKEN}'}).json()
    current_timestamps = eval(current_data['files'][FILE_NAME]['content'])
    current_timestamps[community_name] = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    data = {
        'files': {
            FILE_NAME: {
                'content': json.dumps(current_timestamps, indent=4)  # Use json.dumps with indent
            }
        }
    }
    resp = requests.patch(f'https://api.github.com/gists/{GIST_ID}', json=data, headers={'Authorization': f'token {GIST_TOKEN}'})
    return resp.json()

def send_dm(thread_id, message):
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    resp = requests.post(f'https://squabblr.co/api/message-threads/{thread_id}/messages', data={"content": message, "user_id": BOT_USER_ID}, headers=headers)
    return resp.json()

def get_latest_posts(username, thread_id, community):
    last_timestamp = get_last_timestamp(community)
    data = requests.get(f'https://squabblr.co/api/s/{community}/posts?page=1&sort=new&').json()

    for post in data['data']:
        created_at = post['created_at']
        post_date = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        if post_date > last_timestamp:
            dm_message = f"/s/{post['community_name']} has a new post by @{post['author_username']}: {post['title']}: https://squabblr.co{post['path']}."
            send_dm(thread_id, dm_message)
            save_last_timestamp(community, post_date)

if __name__ == "__main__":
    with open(CSV_PATH, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            get_latest_posts(row['Username'], row['DM_Thread_ID'], row['Community'])
