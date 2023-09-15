# 1. Importing required modules and initializing constants:

import os
import requests
import time
import logging

# Constants
SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
NOTIFYBOT_ID = os.environ.get('NOTIFYBOT_ID')
NOTIFYBOT_GIST_TOKEN = os.environ.get('NOTIFYBOT_GIST_TOKEN')
NOTIFYBOT_GIST_ID = os.environ.get('NOTIFYBOT_GIST_ID')
NOTIFYBOT_GIST_FILENAME = 'notifybot.json'

# Setting up logging
logging.basicConfig(level=logging.INFO)

# 2. Helper function to fetch the current notifybot.json from GitHub Gist:

def fetch_notifybot_gist():
    url = f'https://api.github.com/gists/{NOTIFYBOT_GIST_ID}'
    headers = {'Authorization': f'token {NOTIFYBOT_GIST_TOKEN}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()  # Raise an exception for HTTP errors
    return resp.json()['files'][NOTIFYBOT_GIST_FILENAME]['content']

# 3. Helper function to update notifybot.json:

def update_notifybot_gist(data):
    url = f'https://api.github.com/gists/{NOTIFYBOT_GIST_ID}'
    headers = {'Authorization': f'token {NOTIFYBOT_GIST_TOKEN}'}
    payload = {
        'files': {
            NOTIFYBOT_GIST_FILENAME: {
                'content': data
            }
        }
    }
    resp = requests.patch(url, json=payload, headers=headers)
    resp.raise_for_status()

# 4. Helper function to check for new posts and notify moderators:

def check_and_notify(user):
    headers = {'authorization': 'Bearer ' + SQUABBLES_TOKEN}
    for community in user['communities']:
        community_name = community['community_name']
        last_processed_id = community['last_processed_id']
        
        # Fetch the latest posts for the community
        resp = requests.get(f'https://squabblr.co/api/s/{community_name}/posts?page=1&sort=new')
        resp.raise_for_status()
        posts = resp.json()
        
        # If there's a new post
        if posts and posts[0]['id'] > last_processed_id:
            post = posts[0]
            message = f"/s/{community_name} has a new post by {post['author_username']}: [{post['title']}]({post['url']})"
            logging.info(f"Sending message: {message}")
            
            # Send DM to the moderator
            resp = requests.post(f'https://squabblr.co/api/message-threads/{user['thread_id']}/messages',
                                 data={"content": message, "user_id": NOTIFYBOT_ID},
                                 headers=headers)
            resp.raise_for_status()
            
            # Update the last_processed_id
            community['last_processed_id'] = post['id']
            logging.info(f"Updated last_processed_id for {community_name} to {post['id']}")

# 5. Main function:

def main():
    # Fetch the current notifybot.json
    notifybot_json = fetch_notifybot_gist()
    
    # Check for new posts and notify moderators
    for user in notifybot_json['users']:
        check_and_notify(user)
        
        # Cooldown
        time.sleep(15)
    
    # Update notifybot.json
    update_notifybot_gist(notifybot_json)

if __name__ == "__main__":
    main()
