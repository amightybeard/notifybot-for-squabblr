# 1. Importing required modules and initializing constants:

import os
import requests
import time
import logging
import json

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
    json_content = resp.json()['files'][NOTIFYBOT_GIST_FILENAME]['content']
    return json.loads(json_content)  # Convert the JSON string into a dictionary

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
        
        logging.info(f"Checking /s/{community_name} for new posts")
        
        # Fetch the latest posts for the community
        resp = requests.get(f'https://squabblr.co/api/s/{community_name}/posts?page=1&sort=new')
        resp.raise_for_status()
        posts = resp.json()

        # Log the API response for debugging
        logging.info(f"API response for /s/{community_name}: {posts}")
        
        # If there's a new post
        if posts and isinstance(posts, list) and len(posts) > 0 and posts[0]['id'] > last_processed_id:
            post = posts[0]
            message = f"/s/{community_name} has a new post by {post['author_username']}: [{post['title']}]({post['url']})"
            
            logging.info(f"Located a new post in /s/{community_name}. Notifying the mods.")
            logging.info(f"Sending a DM to {user['username']}: {message}")
            
            # Send DM to the moderator
            resp = requests.post(f"https://squabblr.co/api/message-threads/{user['thread_id']}/messages",
                                 data={"content": message, "user_id": NOTIFYBOT_ID},
                                 headers=headers)
            
            resp.raise_for_status()
            
            logging.info("DM has been sent.")
            
            # Update the last_processed_id
            community['last_processed_id'] = post['id']
            logging.info(f"Updating notifybot.json with the new post ID: {post['id']}")
        else:
            logging.info("No new posts found.")

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
