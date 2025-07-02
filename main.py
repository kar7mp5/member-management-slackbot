from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests
import os
import json

app = FastAPI()

# .env 로부터 환경 변수 불러오기
load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
USER_GROUP_ID = os.environ.get("USER_GROUP_ID")

if not SLACK_TOKEN:
    raise RuntimeError("❌ SLACK_BOT_TOKEN이 설정되지 않았습니다.")


# 1. 채널 참여 이벤트 처리
@app.post("/slack/events")
async def slack_events(req: Request):
    body = await req.json()
    print("\n📨 Slack Event Received:", json.dumps(body, indent=2))

    # Slack URL 인증 처리
    if body.get("type") == "url_verification":
        print("✅ URL verification challenge 수신")
        return JSONResponse(content={"challenge": body["challenge"]})

    # 실제 이벤트 콜백 처리
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        print("🔎 이벤트 유형:", event.get("type"))

        if event.get("type") == "member_joined_channel":
            user_id = event.get("user")
            channel_id = event.get("channel")
            print(f"👤 유저 {user_id} 이(가) 채널 {channel_id} 에 참여함")

            # 에페메랄 메시지 전송
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
                                "text": f"<@{user_id}>님 반갑습니다. 권한 승계를 위해 아래 체크버튼을 눌러주세요."
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "✅ 체크"},
                                    "style": "primary",
                                    "action_id": "grant_permission"
                                }
                            ]
                        }
                    ]
                }
            )
            print("📤 Ephemeral 메시지 전송 결과:", resp.status_code, resp.text)

    return JSONResponse(content={"status": "ok"})


# 2. 버튼 클릭 처리 (Slack Interactivity)
@app.post("/slack/interactions")
async def handle_button_click(request: Request):
    try:
        form = await request.form()
        payload_raw = form.get("payload")

        if not payload_raw:
            print("⚠️ payload 값이 비어있음.")
            return JSONResponse(status_code=400, content={"error": "Missing payload"})

        payload = json.loads(payload_raw)
        print("🖱️ 버튼 클릭 이벤트 수신:", json.dumps(payload, indent=2))

        action = payload["actions"][0]
        user_id = payload["user"]["id"]

        if action["action_id"] == "grant_permission":
            print("✅ 권한 부여 버튼 클릭 by", user_id)

            # 현재 그룹 사용자 목록 조회
            res = requests.get(
                "https://slack.com/api/usergroups.users.list",
                params={"usergroup": USER_GROUP_ID},
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
            )
            current_users = res.json().get("users", [])
            print("👥 기존 그룹 멤버:", current_users)

            if user_id not in current_users:
                current_users.append(user_id)

            # 그룹 사용자 업데이트
            update_res = requests.post(
                "https://slack.com/api/usergroups.users.update",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                data={
                    "usergroup": USER_GROUP_ID,
                    "users": ",".join(current_users)
                }
            )
            print("🔧 그룹 업데이트 결과:", update_res.status_code, update_res.text)

            # DM 전송
            dm_res = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                json={
                    "channel": user_id,
                    "text": "✅ 권한이 부여되었습니다. 이제 팀 채널을 이용하실 수 있습니다!"
                }
            )
            print("📨 DM 전송 결과:", dm_res.status_code, dm_res.text)

            return JSONResponse(content={"text": "✅ 권한이 부여되었습니다."})

        return JSONResponse(content={"text": "❌ 알 수 없는 동작입니다."})

    except Exception as e:
        print("❗예외 발생:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})
