# Gmail Agent

The Gmail agent fetches your recent emails from Gmail and feeds them to the AI so it can summarize, filter, or answer questions about your inbox — all in natural language.

## How It Works

When you ask about your email, the chatbot:

1. Detects Gmail-related keywords in your message
2. Authenticates with the Gmail API using your stored OAuth2 token
3. Fetches matching emails (subject, sender, date, preview snippet)
4. Passes the email data to the AI model, which summarizes or answers your question

## Trigger Phrases

These phrases automatically activate the Gmail agent:

| What you say | What happens |
|---|---|
| "Check my email" / "Check email" | Fetches unread emails |
| "My emails" / "My email" | Fetches unread emails |
| "Inbox" | Fetches unread emails |
| "Unread emails" / "Unread email" | Fetches unread emails |
| "New email" / "New emails" | Fetches unread emails |
| "Gmail" | Fetches unread emails |
| "Email summary" / "Summarize my email" | Fetches unread emails |
| "Check my recent email" | Fetches all inbox (not just unread) |
| "All my emails" | Fetches all inbox |

## Setup

The Gmail agent requires a one-time setup using Google Cloud Console.

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Give it a name (e.g. `chatbot-gmail`) and click **Create**

### Step 2: Enable the Gmail API

1. In your project, go to **APIs & Services** → **Library**
2. Search for **Gmail API**
3. Click it and press **Enable**

### Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
    - Choose **External** (or Internal if using Google Workspace)
    - Fill in App name, user support email, developer contact email
    - Add scope: `https://www.googleapis.com/auth/gmail.readonly`
    - Add your Gmail address as a test user
4. Back in **Create OAuth client ID**:
    - Application type: **Desktop app**
    - Name: anything (e.g. `chatbot`)
    - Click **Create**
5. Click **Download JSON** — this is your credentials file

### Step 4: Install the Credentials

Save the downloaded JSON file as `gmail_credentials.json` in the project root:

```
ai-chatbot/
├── gmail_credentials.json   ← put it here
├── agents/
│   └── gmail_agent.py
├── chatbot_agent.py
└── ...
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the Gmail packages directly:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 6: Authorize (First Run Only)

Run the chatbot and ask about your email:

```
You: Check my email
```

A browser window will open asking you to sign in with Google and grant read-only Gmail access. After you approve:

- A `gmail_token.json` file is saved in the project root
- Future runs use this token automatically (it refreshes when expired)
- You will not be prompted again unless you delete `gmail_token.json`

!!! warning "Keep credentials secure"
    Both `gmail_credentials.json` and `gmail_token.json` are listed in `.gitignore` and must **never** be committed to version control.

## Example Session

```
You: Summarize my unread emails

Bot: You have 4 unread emails:

1. **GitHub** — "[PR] Fix auth middleware" (May 14)
   A pull request was opened by user alice: "Fix token expiry
   check using <= instead of <..."

2. **no-reply@accounts.google.com** — "Security alert" (May 13)
   A new sign-in to your account was detected from macOS...

3. **newsletter@pycoders.com** — "PyCoder's Weekly Issue #634" (May 13)
   This week: asyncio patterns, Python 3.14 news, new packages...

4. **boss@company.com** — "Q2 planning" (May 12)
   Can we sync Thursday at 2pm to go over the roadmap?
```

## Parameters

The Gmail agent accepts these parameters when called programmatically:

| Parameter | Default | Description |
|---|---|---|
| `max_emails` | `10` | Maximum number of emails to fetch |
| `query` | `is:unread` | Gmail search query string |

### Gmail Query Examples

You can use any [Gmail search operator](https://support.google.com/mail/answer/7190):

| Query | Meaning |
|---|---|
| `is:unread` | Unread emails |
| `in:inbox` | All inbox (read + unread) |
| `from:boss@company.com` | From a specific sender |
| `subject:invoice` | Subject contains "invoice" |
| `newer_than:1d` | Last 24 hours |
| `has:attachment` | Emails with attachments |

### Programmatic Usage

```python
from sub_agents import execute_agent

# Fetch unread emails
result = execute_agent('gmail', max_emails=5, query='is:unread')
emails = result['data']['emails']

for email in emails:
    print(f"From: {email['from']}")
    print(f"Subject: {email['subject']}")
    print(f"Date: {email['date']}")
    print(f"Preview: {email['snippet']}")
    print()
```

## Permissions

The agent requests **read-only** Gmail access (`gmail.readonly` scope). It cannot:

- Send emails
- Delete or archive emails
- Modify labels
- Access other Google services

## Troubleshooting

### "Gmail not authenticated" error

`gmail_credentials.json` is missing or in the wrong location. Ensure it is in the project root directory.

### Browser does not open for OAuth

You may be running in a headless environment. Run the chatbot locally first to complete the OAuth flow and generate `gmail_token.json`, then copy that file to the server.

### "Access blocked: app not verified"

Your OAuth consent screen is in **Testing** mode. Add your Gmail address as a test user in Google Cloud Console → APIs & Services → OAuth consent screen → Test users.

### Token expired / refresh errors

Delete `gmail_token.json` and re-authorize:

```bash
rm gmail_token.json
# Then ask about email in the chatbot to trigger re-auth
```

### Agent times out

The default timeout is 10 seconds. Gmail API calls can be slow on first run. Increase the timeout:

```python
orchestrator.execute_agents(tasks, timeout=20)
```
