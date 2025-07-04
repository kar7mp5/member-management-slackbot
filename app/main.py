from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import requests
from mangum import Mangum
from dotenv import load_dotenv
from pathlib import Path
import json
import os

# Load .env file for local development (ignored in AWS Lambda)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# Load secrets from environment variables
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
USER_GROUP_ID = os.environ.get("USER_GROUP_ID")

if not SLACK_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN is not set.")
if not USER_GROUP_ID:
    raise RuntimeError("USER_GROUP_ID is not set.")


@app.post("/slack/events")
async def slack_events(req: Request):
    """
    Handles incoming Slack Events API requests (e.g., URL verification, event_callback).

    Args:
        req (Request): Incoming request from Slack.

    Returns:
        Response: Either a URL challenge (for verification) or OK after event handling.
    """
    body = await req.json()
    print("\nSlack Event Received:", json.dumps(body, indent=2))

    # Handle Slack URL verification
    if body.get("type") == "url_verification":
        print("Received URL verification challenge")
        return PlainTextResponse(content=body["challenge"])

    # Handle actual Slack events
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        print(f"Event type: {event.get('type')}")

        # Respond when a user joins a channel
        if event.get("type") == "member_joined_channel":
            user_id = event.get("user")
            channel_id = event.get("channel")
            print(f"User {user_id} joined channel {channel_id}")

            # Send an ephemeral message prompting permission
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
                                "text": f"🎉 <@{user_id}>님, 환영합니다! 아래 버튼을 눌러 권한을 신청해주세요."
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
            )
            print(f"Ephemeral message sent. Status: {resp.status_code}, Response: {resp.text}")

    return JSONResponse(content={"status": "ok"})


@app.post("/slack/interactions")
async def handle_button_click(request: Request):
    """
    Handles interactive button clicks from Slack (e.g., 권한 신청).

    Args:
        request (Request): The HTTP form-encoded payload sent by Slack.

    Returns:
        JSONResponse: Status of permission update or fallback message.
    """
    try:
        form = await request.form()
        payload_raw = form.get("payload")

        if not payload_raw:
            print("Payload is missing.")
            return JSONResponse(status_code=400, content={"error": "Missing payload"})

        payload = json.loads(payload_raw)
        print("🖱️ Button click event received:", json.dumps(payload, indent=2))

        action = payload["actions"][0]
        user_id = payload["user"]["id"]

        if action["action_id"] == "grant_permission":
            print(f"Permission grant button clicked by {user_id}")

            # Fetch existing members of the user group
            res = requests.get(
                "https://slack.com/api/usergroups.users.list",
                params={"usergroup": USER_GROUP_ID},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
            )
            current_users = res.json().get("users", [])
            print(f"Existing group members: {current_users}")

            # Append user to the group if not already included
            if user_id not in current_users:
                current_users.append(user_id)

            # Update the user group with the new list
            update_res = requests.post(
                "https://slack.com/api/usergroups.users.update",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                data={
                    "usergroup": USER_GROUP_ID,
                    "users": ",".join(current_users),
                }
            )
            print(f"Group update result. Status: {update_res.status_code}, Response: {update_res.text}")

            # Notify the user via DM
            dm_res = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                json={
                    "channel": user_id,
                    "text": "🙌 권한이 부여되었습니다! 이제 팀 채널을 자유롭게 사용할 수 있어요."
                }
            )
            print(f"📨 DM sent. Status: {dm_res.status_code}, Response: {dm_res.text}")

            return JSONResponse(content={"text": "✅ 권한이 성공적으로 부여되었습니다."})

        return JSONResponse(content={"text": "❌ 알 수 없는 동작입니다."})

    except Exception as e:
        print(f"❗ An exception occurred: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Adapter for AWS Lambda via API Gateway
handler = Mangum(app)
