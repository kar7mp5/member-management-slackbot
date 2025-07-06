# Member Management Slackbot

A Slack bot that automates the process of granting permissions to new members by adding them to a user group when they join a channel.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment (AWS)](#deployment-aws)
- [Local Development](#local-development)
- [License](#license)

## Features

- **Welcome Message**: Greets users with a private message when they join a monitored channel.
- **Interactive Onboarding**: Prompts new users to click a button to request permissions.
- **Automated Permissions**: Adds the user to a predefined Slack User Group upon button click.
- **DM Confirmation**: Notifies the user via Direct Message once permissions are granted.

## Prerequisites

- Python 3.10+
- A Slack Workspace where you have permission to install apps.
- An AWS account with permissions to manage Lambda, API Gateway, and S3.

## Configuration

Create a `.env` file in the root of the project and add the following variables:

```env
# Found under "OAuth & Permissions" in your Slack App settings
SLACK_BOT_TOKEN="xoxb-..."

# The ID of the user group you want to add members to (e.g., UG1234567)
USER_GROUP_ID="YOUR_SLACK_USER_GROUP_ID"
```

### Slack App Setup

1.  **Create a Slack App**: Go to the [Slack API page](https://api.slack.com/apps) and create a new app.
2.  **Add Bot Token Scopes**: Navigate to **OAuth & Permissions** and add the following scopes under "Bot Token Scopes":
    - `chat:write`
    - `usergroups:read`
    - `usergroups:write`
    - `channels:read`
    - `groups:read`
3.  **Install App to Workspace**: Install the app to your workspace to generate the `SLACK_BOT_TOKEN`.
4.  **Enable Event Subscriptions & Interactivity**:
    - Go to **Event Subscriptions**, toggle it on, and subscribe to the `member_joined_channel` bot event.
    - Go to **Interactivity & Shortcuts** and toggle it on.
5.  **Add the Bot to a Channel**: Manually invite your bot to the channel you want it to monitor.

## Deployment (AWS)

This project is configured for automated deployment to AWS Lambda and API Gateway using GitHub Actions.

### 1. GitHub Secrets

To enable automated deployment, you must configure the following secrets in your GitHub repository's **Settings > Secrets and variables > Actions**:

- `AWS_ACCESS_KEY_ID`: Your AWS access key ID.
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key.
- `AWS_REGION`: The AWS region for your resources (e.g., `us-east-1`).
- `LAMBDA_FUNCTION_NAME`: The name of your Lambda function.
- `S3_BUCKET_NAME`: The name of the S3 bucket for storing the deployment package.
- `SLACK_BOT_TOKEN`: Your Slack bot token.
- `USER_GROUP_ID`: The ID of the Slack user group.

### 2. How It Works

The `.github/workflows/deploy.yml` workflow will automatically:

1.  Install dependencies and create a deployment package.
2.  Upload the package to the specified S3 bucket.
3.  Update the Lambda function with the new code.
4.  Update the Lambda function's environment variables.

**Note**: The initial setup of the Lambda function and API Gateway must be done manually in the AWS console. This workflow only handles updates.

## Local Development

### 1. Clone and Install

```bash
git clone <your-repository-url>
cd member-management-slackbot
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r app/requirements.txt
```

### 2. Run the Server

You will need a tool like [ngrok](https://ngrok.com/download) to expose your local server to the internet for Slack to send events.

```bash
# Start the local server (if you have a local server setup)
# uvicorn main:app --reload

# Expose your local server with ngrok
ngrok http 8000
```

### 3. Update Slack Request URLs

1.  **Event Subscriptions**: In your Slack App settings, go to **Event Subscriptions**. Set the "Request URL" to your ngrok URL, appending `/slack/events`.
2.  **Interactivity & Shortcuts**: Go to **Interactivity & Shortcuts**. Set the "Request URL" to your ngrok URL, appending `/slack/interactions`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
