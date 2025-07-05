import json
import os
import requests

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
USER_GROUP_ID = os.getenv("USER_GROUP_ID")

def lambda_handler(event, context):
    """Main AWS Lambda handler for Slack bot events.

    This function handles:
    - Slack's URL verification challenge
    - Member join events
    - Interactive button clicks

    Args:
        event (dict): AWS Lambda event payload.
        context (object): Lambda context runtime methods and attributes.

    Returns:
        dict: HTTP response formatted for API Gateway.
    """
    try:
        print("Incoming event:", json.dumps(event, indent=2))
        body = json.loads(event.get("body", "{}"))

        # Handle Slack URL verification
        if body.get("type") == "url_verification" and "challenge" in body:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/plain"},
                "body": body["challenge"]
            }

        # Handle event_callback (e.g., member joined a channel)
        if body.get("type") == "event_callback":
            event_data = body.get("event", {})
            if event_data.get("type") == "member_joined_channel":
                user_id = event_data.get("user")
                channel_id = event_data.get("channel")
                print(f"User {user_id} joined channel {channel_id}")
                send_ephemeral_welcome(user_id, channel_id)

        # Handle interactive message actions (form-urlencoded)
        if event.get("headers", {}).get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
            from urllib.parse import parse_qs
            payload_raw = parse_qs(event["body"]).get("payload", [None])[0]

            if payload_raw:
                payload = json.loads(payload_raw)
                print("Interaction payload:", json.dumps(payload, indent=2))

                action = payload["actions"][0]
                user_id = payload["user"]["id"]

                if action["action_id"] == "grant_permission":
                    handle_grant_permission(user_id)
                    send_dm(user_id, "Your permission has been granted. You can now access team channels.")
                    return response_json({"text": "Permission granted."})

        return response_json({"message": "OK"})

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def handle_grant_permission(user_id):
    """Adds a user to a Slack user group if not already a member.

    Args:
        user_id (str): Slack user ID to be added to the group.
    """
    group_url = "https://slack.com/api/usergroups.users.list"
    update_url = "https://slack.com/api/usergroups.users.update"

    res = requests.get(
        group_url,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        params={"usergroup": USER_GROUP_ID}
    )
    current_users = res.json().get("users", [])

    # Add the user to the group if not already included
    if user_id not in current_users:
        current_users.append(user_id)

    update_res = requests.post(
        update_url,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        data={"usergroup": USER_GROUP_ID, "users": ",".join(current_users)}
    )
    print("Updated user group:", update_res.status_code, update_res.text)

def send_ephemeral_welcome(user_id, channel_id):
    """Sends an ephemeral message prompting the user to request permission.

    Args:
        user_id (str): Slack user ID of the joined member.
        channel_id (str): Slack channel ID where the user joined.
    """
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
                    "text": f"<@{user_id}> welcome! Please click the button below to request permission."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Request Permission"},
                        "style": "primary",
                        "action_id": "grant_permission"
                    }
                ]
            }
        ]
    }
    resp = requests.post(url, headers=headers, json=data)
    print("Ephemeral message sent:", resp.status_code, resp.text)

def send_dm(user_id, message):
    """Sends a direct message to a user via Slack.

    Args:
        user_id (str): Slack user ID.
        message (str): Message to send.
    """
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        json={"channel": user_id, "text": message}
    )
    print("DM sent:", resp.status_code, resp.text)

def response_json(data, status=200):
    """Returns a JSON-formatted HTTP response.

    Args:
        data (dict): JSON-serializable response body.
        status (int): HTTP status code. Defaults to 200.

    Returns:
        dict: Formatted response object for API Gateway.
    """
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data)
    }
