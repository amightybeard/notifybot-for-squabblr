# 1. Importing required modules and initializing constants:

import os
import requests
import time
import logging
import json
from datetime import datetime

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
    prettified_data = json.dumps(data, indent=4)  # Convert the dictionary to a prettified JSON string
    payload = {
        'files': {
            NOTIFYBOT_GIST_FILENAME: {
                'content': prettified_data
            }
        }
    }
    resp = requests.patch(url, json=payload, headers=headers)
    logging.info(f"Updating notifybot.json with the new data.")
    resp.raise_for_status()
    if resp.status_code not in [200,201]:
        logging.error(f"Update Gist Error response: {resp.text}")
        resp.raise_for_status()

# 4. Helper function to check for new posts and notify moderators:
def check_chat_status(chat_messages, last_processed_chat_id):
    """
    Checks the chat status based on recent messages and returns the new status and the latest chat ID.
    """
    current_time = datetime.now()
    recent_messages = [msg for msg in chat_messages if (current_time - datetime.fromisoformat(msg['created_at'].replace('Z', ''))).seconds <= 900] # Messages in the last 15 minutes

    latest_chat_id = chat_messages[0]['id'] if chat_messages else last_processed_chat_id
    new_chat_status = "busy" if len(recent_messages) >= 5 else "quiet"
    
    return new_chat_status, latest_chat_id

def check_and_notify(user, notifybot_json):
    headers = {
        'Authorization': f"Bearer {SQUABBLES_TOKEN}",
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Processing communities
    for community in notifybot_json["communities"]:
        community_name = community["community_name"]
        last_processed_id = community["last_processed_id"]
        
        logging.info(f"Checking /s/{community_name} for new posts")
        logging.info(f"Last processed ID for /s/{community_name}: {last_processed_id}")

        resp = requests.get(f"https://squabblr.co/api/s/{community_name}/posts?page=1&sort=new", headers=headers)
        resp.raise_for_status()

        posts = resp.json().get('data', [])
        new_posts = [post for post in posts if post['id'] > last_processed_id]

        for post in new_posts:
            content = f"/s/{community_name} has a new post by @{post['author_username']}: [{post['title']}]({post['url']})"
            logging.info(f"Located a new post in /s/{community_name}. Notifying the mods.")
            
            for watcher in community["watchers"]:
                if watcher["user_id"] == user["user_id"]:
                    send_dm(watcher["thread_id"], content)
                    community["last_processed_id"] = post["id"]
                    logging.info(f"Updated last_processed_id for /s/{community_name} to {post['id']}.")

    # Processing chats
    for chat in notifybot_json["chats"]:
        community_name = chat["community_name"]
        last_processed_chat_id = chat["last_processed_id"]
        
        logging.info(f"Checking chat for /s/{community_name}")
        resp = requests.get(f"https://squabblr.co/api/s/{community_name}/chat-messages", headers=headers)
        resp.raise_for_status()
        
        chat_messages = resp.json().get('messages', [])
        new_chat_status, latest_chat_id = check_chat_status(chat_messages, last_processed_chat_id)
        
        # If there are new messages since the last_processed_id
        if latest_chat_id > last_processed_chat_id:
            message = f"https://squabblr.co/s/{community_name}/chat has a new message by @{chat_messages[0]['user']['username']}: {chat_messages[0]['content']}"
            
            for watcher in chat["watchers"]:
                if watcher["user_id"] == user["user_id"]:
                    send_dm(watcher["thread_id"], message)
                    chat["last_processed_id"] = latest_chat_id
                    logging.info(f"Updated last_processed_id for /s/{community_name}/chat to {latest_chat_id}.")

        # Update the chat status if it has changed
        if new_chat_status != chat["chat_status"]:
            chat["chat_status"] = new_chat_status
            logging.info(f"Updated chat_status for /s/{community_name} to {new_chat_status}.")

    # Update the notifybot.json gist after processing all communities and chats for this user
    update_notifybot_gist(notifybot_json)
    
# 5. Main function:

def main():
    # Fetch the current notifybot.json
    notifybot_json = fetch_notifybot_gist()
    
    # Check for new posts and notify moderators
    check_and_notify(CURRENT_USER, notifybot_json)  # We now pass the CURRENT_USER directly
        
    # Cooldown
    time.sleep(15)
    
    # Update notifybot.json
    update_notifybot_gist(notifybot_json)

if __name__ == "__main__":
    main()
