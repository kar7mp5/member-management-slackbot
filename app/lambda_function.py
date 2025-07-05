import os
import json
import requests
from urllib.parse import parse_qs
import base64

SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
USER_GROUP_ID = os.environ["USER_GROUP_ID"]

def lambda_handler(event, context):
    try:
        print("Incoming event:", json.dumps(event, indent=2))
        path = event.get("rawPath", "")
        headers = event.get("headers", {})
        content_type = headers.get("Content-Type", headers.get("content-type", ""))

        # Handle /slack/events
        if path.endswith("/slack/events") and content_type.startswith("application/json"):
            body = json.loads(event.get("body", "{}"))

            # URL verification
            if body.get("type") == "url_verification":
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/plain"},
                    "body": body["challenge"]
                }

            # Event callback
            if body.get("type") == "event_callback":
                event_data = body.get("event", {})
                if event_data.get("type") == "member_joined_channel":
                    user = event_data.get("user")
                    channel = event_data.get("channel")
                    send_ephemeral_button(user, channel)

        # Handle /slack/interactions (button click)
        if path.endswith("/slack/interactions") and content_type.startswith("application/x-www-form-urlencoded"):
            # Decode base64 body if necessary
            encoded_body = event.get("body", "")
            if event.get("isBase64Encoded", False):
                encoded_body = base64.b64decode(encoded_body).decode("utf-8")

            # Parse Slack interaction payload
            payload_raw = parse_qs(encoded_body).get("payload", [None])[0]
            if payload_raw:
                payload = json.loads(payload_raw)
                user_id = payload["user"]["id"]
                action_id = payload["actions"][0]["action_id"]

                if action_id == "grant_permission":
                    print("User clicked permission button:", user_id)

                    # Retrieve current users in the target user group
                    res = requests.get(
                        "https://slack.com/api/usergroups.users.list",
                        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                        params={"usergroup": USER_GROUP_ID}
                    )
                    current_users = res.json().get("users", [])
                    print("Current group members:", current_users)

                    # Append the user if not already in the group
                    if user_id not in current_users:
                        current_users.append(user_id)

                    # Update the user group
                    update_res = requests.post(
                        "https://slack.com/api/usergroups.users.update",
                        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                        data={
                            "usergroup": USER_GROUP_ID,
                            "users": ",".join(current_users)
                        }
                    )
                    update_json = update_res.json()
                    print("User group update response:", update_json)

                    if update_json.get("ok"):
                        # Send success DM
                        send_dm(user_id, "You’ve been granted access. You can now use the team channel freely.")
                    else:
                        # Send failure DM with reason
                        error_msg = update_json.get("error", "Unknown error")
                        send_dm(user_id, f"Failed to grant access. Reason: {error_msg}")
                        print("User group update failed:", error_msg)


        return response_json({"message": "ok"})

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def send_ephemeral_button(user_id, channel_id):
    """Sends ephemeral button message to user in channel"""
    url = "https://slack.com/api/chat.postEphemeral"
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    data = {
        "channel": channel_id,
        "user": user_id,
        "text": " ",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user_id}>님, 환영합니다! 아래 버튼을 눌러 권한을 신청해주세요."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ 권한 신청"},
                        "style": "primary",
                        "action_id": "grant_permission"
                    }
                ]
            }
        ]
    }
    res = requests.post(url, headers=headers, json=data)
    print("Ephemeral message sent:", res.status_code, res.text)

def add_user_to_group(user_id):
    """Adds user to Slack user group if not already present"""
    group_url = "https://slack.com/api/usergroups.users.list"
    update_url = "https://slack.com/api/usergroups.users.update"

    res = requests.get(
        group_url,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        params={"usergroup": USER_GROUP_ID}
    )
    current_users = res.json().get("users", [])

    if user_id not in current_users:
        current_users.append(user_id)

    update_res = requests.post(
        update_url,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        data={
            "usergroup": USER_GROUP_ID,
            "users": ",".join(current_users)
        }
    )
    print("User group update:", update_res.status_code, update_res.text)

def send_dm(user_id, message):
    """Sends DM to user"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": user_id,
        "text": message
    }
    res = requests.post(url, headers=headers, json=data)
    print("DM sent:", res.status_code, res.text)

def response_json(body_dict):
    """Returns a JSON-formatted HTTP response"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict)
    }
