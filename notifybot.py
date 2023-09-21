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
    prettified_data = json.dumps(data, indent=4)  # Convert the dictionary to a prettified JSON string
    payload = {
        'files': {
            NOTIFYBOT_GIST_FILENAME: {
                'content': prettified_data
            }
        }
    }
    resp = requests.patch(url, json=payload, headers=headers)
    logging.info(f"Updating notifybot.json with data: {prettified_data}")
    resp.raise_for_status()
    if resp.status_code not in [200,201]:
        logging.error(f"Update Gist Error response: {resp.text}")
        resp.raise_for_status()

# 4. Helper function to check for new posts and notify moderators:

def check_and_notify(user, notifybot_json):
    headers = {
        'Authorization': f"Bearer {SQUABBLES_TOKEN}",
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    for community in user['communities']:
        community_name = community['community_name']
        last_processed_id = community['last_processed_id']

        logging.info(f"Checking /s/{community_name} for new posts")
        logging.info(f"Last processed ID for /s/{community_name}: {last_processed_id}")

        resp = requests.get(f"https://squabblr.co/api/s/{community_name}/posts?page=1&sort=new", headers=headers)
        resp.raise_for_status()
        if resp.status_code not in [200,201]:
            logging.error(f"Check and Notify Error in Community response: {resp.text}")
            resp.raise_for_status()

        posts = resp.json().get('data', [])

        # Loop through all posts to find new ones
        new_posts = [post for post in posts if post['id'] > last_processed_id]

        for post in new_posts:
            message = f"/s/{community_name} has a new post by @{post['author_username']}: [{post['title']}]({post['url']})"
            
            logging.info(f"Located a new post in /s/{community_name}. Notifying the mods.")
            logging.info(f"Sending a DM to {user['username']}: {message}")
            
            # Send DM to the moderator
            resp = requests.post(f"https://squabblr.co/api/message-threads/{user['thread_id']}/messages", json={"content": message, "user_id": NOTIFYBOT_ID}, headers=headers)
            
            if resp.status_code not in [200,201]:
                logging.error(f"Check and Notify Error in Post response: {resp.text}")
                resp.raise_for_status()
            
            logging.info("DM has been sent.")
            
            # Update the last_processed_id for this community
            if post['id'] > community['last_processed_id']:
                community['last_processed_id'] = post['id']
                logging.info(f"Updating notifybot.json with the new post ID: {post['id']} for /s/{community_name}")

    for chat in user.get('chats', []):
        community_name = chat['community_name']
        last_processed_chat_id = chat['last_processed_id']
        chat_status = chat.get('chat_status', 'quiet')
        
        # Fetch chat messages
        resp = requests.get(f"https://squabblr.co/api/s/{community_name}/chat-messages", headers=headers)
        resp.raise_for_status()

        chat_messages = resp.json().get('messages', [])
        latest_message = chat_messages[0] if chat_messages else None

        new_chat_status, latest_chat_id = check_chat_status(chat_messages, last_processed_chat_id)
        
        if new_chat_status != chat_status:
            chat['chat_status'] = new_chat_status
            
            if new_chat_status == "busy":
                message = f"https://squabblr.co/s/{community_name}/chat has had 5 messages in the last 15-minutes."
            elif latest_message:
                message = f"https://squabblr.co/s/{community_name}/chat has a new message by @{latest_message['user']['username']}: {latest_message['content']}"
            
            # Send DM to the moderator
            resp = requests.post(f"https://squabblr.co/api/message-threads/{user['thread_id']}/messages", data={"content": message, "user_id": NOTIFYBOT_ID}, headers=headers)
            
            if resp.status_code not in [200,201]:
                logging.error(f"Error in Chat DM response: {resp.text}")
                resp.raise_for_status()
            logging.info(f"DM regarding /s/{community_name}/chat has been sent to {user['username']}.")
            
            chat['last_processed_id'] = latest_chat_id
            logging.info(f"Updating notifybot.json with the new chat message ID: {latest_chat_id} for /s/{community_name}/chat")

    # Update the notifybot.json gist after processing all communities and chats for this user
    update_notifybot_gist(user_data)

    # Update the notifybot.json gist after processing all communities and chats for this user
    update_notifybot_gist(user_data)
    
# 5. Main function:

def main():
    # Fetch the current notifybot.json
    notifybot_json = fetch_notifybot_gist()
    
    # Check for new posts and notify moderators
    for user in notifybot_json['users']:
        check_and_notify(user, notifybot_json)
        
        # Cooldown
        time.sleep(15)
    
    # Update notifybot.json
    update_notifybot_gist(notifybot_json)

if __name__ == "__main__":
    main()
