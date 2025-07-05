# Member Management Slackbot

A FastAPI-based Slack bot that automates the process of granting permissions to new members when they join a channel by adding them to a user group.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [License](#license)

## Features

- **Welcome Message**: Greets users with a private, ephemeral message when they join a monitored channel.
- **Interactive Button**: Prompts the new user to click a button to receive proper permissions.
- **Automated Permission Granting**: Adds the user to a predefined Slack User Group upon button click.
- **DM Confirmation**: Notifies the user via Direct Message once permissions have been successfully granted.

## Prerequisites

- [Python 3.8+](https://www.python.org/)
- [ngrok](https://ngrok.com/download) to expose your local server to the internet.
- A Slack Workspace where you have permission to install apps.

## Getting Started

This guide will walk you through the steps to set up the project on your local machine for development and testing.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd member-management-slackbot
```

### 2. Install Dependencies

It's highly recommended to use a virtual environment.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install the required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root of the project and add the following variables.

```env
# Found under "OAuth & Permissions" in your Slack App settings
SLACK_BOT_TOKEN="xoxb-..."

# The ID of the user group you want to add members to (e.g., UG1234567)
USER_GROUP_ID="YOUR_SLACK_USER_GROUP_ID"
```

### 4. Configure Your Slack App

1.  **Create a Slack App**: Go to the Slack API page and create a new app.

2.  **Add Bot Token Scopes**: Navigate to **OAuth & Permissions** and add the following scopes under "Bot Token Scopes":
    - `chat:write` (to send messages)
    - `usergroups:read` (to read user group members)
    - `usergroups:write` (to update user group members)
    - `channels:read` (to get info about public channels)
    - `groups:read` (to get info about private channels)

3.  **Install App to Workspace**: Install the app to your workspace to generate the `SLACK_BOT_TOKEN`.

4.  **Enable Event Subscriptions**:
    - Go to **Event Subscriptions** and toggle it on.
    - Subscribe to the `member_joined_channel` event under "Subscribe to bot events".

5.  **Enable Interactivity**:
    - Go to **Interactivity & Shortcuts** and toggle it on.

6.  **Add the Bot to a Channel**: Manually invite your bot to the public or private channel you want it to monitor.

> **Note**: You will set the Request URLs in the next section after starting the server.

## Running the Application

### 1. Start the FastAPI Server

The server will run on `http://localhost:8000`. The `--reload` flag automatically restarts the server on code changes.

```bash
uvicorn main:app --reload
```

### 2. Expose Your Local Server with ngrok

In a new terminal window, start ngrok to create a public URL for your local server.

```bash
ngrok http 8000
```

Copy the `https` Forwarding URL provided by ngrok (e.g., `https://xxxxxxxx.ngrok.io`).

### 3. Update Slack Request URLs

1.  **Event Subscriptions**: Go back to your Slack App settings -> **Event Subscriptions**. Paste your ngrok URL into the "Request URL" field, appending `/slack/events`.
    - Example: `https://xxxxxxxx.ngrok.io/slack/events`

2.  **Interactivity & Shortcuts**: Go to **Interactivity & Shortcuts**. Paste your ngrok URL, appending `/slack/interactions`.
    - Example: `https://xxxxxxxx.ngrok.io/slack/interactions`

Your bot is now ready! Add a new user to the channel to test the workflow.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.

cd build
zip -r ../lambda.zip .
cd ..

aws lambda update-function-code \
  --function-name slack-bot-lambda \
  --zip-file fileb://lambda.zip