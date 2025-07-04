from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from mangum import Mangum
from dotenv import load_dotenv
from pathlib import Path
import json
import os

# Load .env for local development (ignored on AWS Lambda)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# Load secrets from environment
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
USER_GROUP_ID = os.environ.get("USER_GROUP_ID")

if not SLACK_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN is not set.")
if not USER_GROUP_ID:
    raise RuntimeError("USER_GROUP_ID is not set.")


@app.post("/slack/events")
async def slack_events(req: Request):
    """Handles Slack Events API, such as URL verification and member join events.

    Args:
        req: The incoming HTTP request from Slack.

    Returns:
        JSONResponse: A response to Slack depending on the event type.
    """
    body = await req.json()
    print("\nSlack Event Received:", json.dumps(body, indent=2))

    # Respond to Slack's URL verification challenge (used for endpoint validation).
    if body.get("type") == "url_verification":
        print("Received URL verification challenge")
        return JSONResponse(content={"challenge": body["challenge"]})

    # Handle actual events (e.g., member joined a channel).
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        print(f"Event type: {event.get('type')}")

        if event.get("type") == "member_joined_channel":
            user_id = event.get("user")
            channel_id = event.get("channel")
            print(f"User {user_id} joined channel {channel_id}")

            # Send a button prompt to the user using an ephemeral Slack message.
            resp = requests.post(
                "https://slack.com/api/chat.postEphemeral",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                json={
                    "channel": channel_id,
                    "user": user_id,
                    "text": " ",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Welcome, <@{user_id}>! To get the proper permissions, please click the button below."
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "✅ Grant Permissions"},
                                    "style": "primary",
                                    "action_id": "grant_permission"
                                }
                            ]
                        }
                    ]
                }
            )
            print(f"Ephemeral message sent. Status: {resp.status_code}, Response: {resp.text}")

    return JSONResponse(content={"status": "ok"})


@app.post("/slack/interactions")
async def handle_button_click(request: Request):
    """Handles Slack interactive button click (e.g., Grant Permission button).

    Args:
        request: The HTTP request from Slack Interactivity payload.

    Returns:
        JSONResponse: Result of the permission update or error response.
    """
    try:
        form = await request.form()
        payload_raw = form.get("payload")

        # Return error if payload is missing
        if not payload_raw:
            print("Payload is missing.")
            return JSONResponse(status_code=400, content={"error": "Missing payload"})

        payload = json.loads(payload_raw)
        print("🖱️ Button click event received:", json.dumps(payload, indent=2))

        action = payload["actions"][0]
        user_id = payload["user"]["id"]

        if action["action_id"] == "grant_permission":
            print(f"Permission grant button clicked by {user_id}")

            # Fetch current members of the user group from Slack API.
            res = requests.get(
                "https://slack.com/api/usergroups.users.list",
                params={"usergroup": USER_GROUP_ID},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
            )
            current_users = res.json().get("users", [])
            print(f"Existing group members: {current_users}")

            # Add user to group if not already included.
            if user_id not in current_users:
                current_users.append(user_id)

            # Update the user group with the new user list.
            update_res = requests.post(
                "https://slack.com/api/usergroups.users.update",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                data={
                    "usergroup": USER_GROUP_ID,
                    "users": ",".join(current_users),
                }
            )
            print(f"Group update result. Status: {update_res.status_code}, Response: {update_res.text}")

            # Notify the user via DM that permissions were granted.
            dm_res = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                json={
                    "channel": user_id,
                    "text": "✅ Permissions granted! You can now use the team channels."
                }
            )
            print(f"📨 DM sent. Status: {dm_res.status_code}, Response: {dm_res.text}")

            return JSONResponse(content={"text": "✅ Permissions have been granted."})

        # Return fallback message for unknown action IDs.
        return JSONResponse(content={"text": "❌ Unknown action."})

    except Exception as e:
        print(f"❗ An exception occurred: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Required for AWS Lambda integration via API Gateway.
# Mangum adapter wraps FastAPI to support AWS Lambda event format.
handler = Mangum(app)
