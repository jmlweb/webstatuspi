# Telegram Bot Setup Guide

Get instant push notifications on your phone when monitored URLs go down or recover.

## Overview

**Why Telegram?**
- Free, no subscription required
- Instant push notifications
- Works on mobile and desktop
- No server-side setup needed
- Supports rich message formatting

**Requirements:**
- Telegram account (mobile or desktop app)
- WebStatusπ with webhook alerts enabled
- Internet connection from your Raspberry Pi

## Quick Setup (5 minutes)

### Step 1: Create Your Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat and send `/newbot`
3. Choose a display name (e.g., "My Server Monitor")
4. Choose a username ending in `bot` (e.g., `myserver_monitor_bot`)
5. **Copy the bot token** - it looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

```
BotFather response:
Done! Congratulations on your new bot. You will find it at t.me/myserver_monitor_bot.
Use this token to access the HTTP API:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

> **Keep this token secret!** Anyone with it can control your bot.

### Step 2: Get Your Chat ID

#### Option A: Personal Notifications (Recommended)

1. Open a chat with your new bot (search for `@your_bot_username`)
2. Send any message (e.g., "hello")
3. Open this URL in your browser (replace `YOUR_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
4. Find your chat ID in the response:
   ```json
   {"ok":true,"result":[{"message":{"chat":{"id":123456789}}}]}
   ```
   Your chat ID is `123456789` (a positive number)

#### Option B: Group Notifications

1. Create a Telegram group or use an existing one
2. Add your bot to the group
3. Send a message in the group
4. Use the `getUpdates` URL above
5. Find the group chat ID (negative number, e.g., `-100123456789`)

### Step 3: Set Up a Webhook Relay

WebStatusπ sends a generic JSON payload that isn't directly compatible with Telegram's API. You need a relay service to transform the payload.

#### Option A: Pipedream (Free, Recommended)

[Pipedream](https://pipedream.com) offers a free tier perfect for this use case.

1. Create a free account at https://pipedream.com
2. Create a new workflow with **HTTP trigger**
3. Copy the webhook URL (e.g., `https://eo1234abc.m.pipedream.net`)
4. Add a **Node.js** code step with this code:

```javascript
export default defineComponent({
  async run({ steps }) {
    const event = steps.trigger.event.body;

    // Format the message
    const isDown = event.event === "url_down";
    const emoji = isDown ? "🔴" : "🟢";
    const status = isDown ? "DOWN" : "UP";

    const message = `${emoji} *${event.url.name}* is ${status}

URL: ${event.url.url}
Status Code: ${event.status.code || "N/A"}
Response Time: ${event.status.response_time_ms}ms
Time: ${new Date(event.status.timestamp).toLocaleString()}`;

    // Send to Telegram
    const TELEGRAM_TOKEN = "YOUR_BOT_TOKEN";
    const CHAT_ID = "YOUR_CHAT_ID";

    const response = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: CHAT_ID,
          text: message,
          parse_mode: "Markdown"
        })
      }
    );

    return await response.json();
  }
});
```

5. Replace `YOUR_BOT_TOKEN` and `YOUR_CHAT_ID` with your values
6. Deploy the workflow

#### Option B: n8n (Self-Hosted)

If you prefer self-hosting, [n8n](https://n8n.io) is a great option.

1. Install n8n on your server or use n8n cloud
2. Create a workflow:
   - **Webhook** trigger node
   - **Telegram** node (send message)
3. Configure the Telegram node with your bot token
4. Use expressions to format the message from the webhook data
5. Copy the webhook URL

#### Option C: Make.com (Formerly Integromat)

1. Create a free account at https://make.com
2. Create a new scenario with **Webhooks** → **Custom webhook**
3. Add **Telegram Bot** → **Send a Text Message**
4. Map the fields from the webhook to the Telegram message
5. Copy the webhook URL

### Step 4: Configure WebStatusπ

Add the relay webhook URL to your `config.yaml`:

```yaml
alerts:
  webhooks:
    - url: "https://eo1234abc.m.pipedream.net"  # Your Pipedream/n8n URL
      enabled: true
      on_failure: true      # Alert when URL goes DOWN
      on_recovery: true     # Alert when URL comes back UP
      cooldown_seconds: 300 # 5 minutes between alerts per URL
```

### Step 5: Test Your Setup

```bash
webstatuspi test-alert
```

You should receive a test notification in Telegram within seconds.

## Message Formatting

Telegram supports Markdown formatting in messages:

| Format | Syntax | Result |
|--------|--------|--------|
| Bold | `*text*` | **text** |
| Italic | `_text_` | *text* |
| Code | `` `code` `` | `code` |
| Link | `[text](url)` | [text](url) |

Example formatted alert:

```
🔴 *APP_PROD* is DOWN

URL: https://api.example.com
Status Code: 503
Response Time: 5000ms
Time: 1/21/2026, 10:30:15 AM
```

## Troubleshooting

### Bot not responding to messages

1. **Did you start a conversation?** You must send at least one message to the bot first
2. **Is the token correct?** Check for typos or extra spaces
3. **Test the bot directly:**
   ```bash
   curl "https://api.telegram.org/botYOUR_TOKEN/getMe"
   ```
   Should return bot info, not an error

### Wrong chat ID

| ID Type | Format | Example |
|---------|--------|---------|
| Personal | Positive number | `123456789` |
| Group | Negative number | `-123456789` |
| Supergroup/Channel | Starts with `-100` | `-1001234567890` |

### Messages not arriving

1. **Check the relay service logs** (Pipedream, n8n, etc.)
2. **Verify WebStatusπ is sending webhooks:**
   ```bash
   webstatuspi test-alert --verbose
   ```
3. **Test Telegram API directly:**
   ```bash
   curl -X POST "https://api.telegram.org/botYOUR_TOKEN/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "YOUR_CHAT_ID", "text": "Test message"}'
   ```

### Bot was removed from group

If you remove the bot from a group, you need to:
1. Add the bot back to the group
2. Get the new chat ID (it may change)
3. Update your relay configuration

### Rate limiting

Telegram limits bots to ~30 messages per second. If monitoring many URLs that fail simultaneously, alerts may be delayed. Consider:
- Increasing `cooldown_seconds` to reduce alert frequency
- Using a group chat for multiple administrators

## Security Best Practices

1. **Never commit bot tokens** to version control
2. **Use environment variables** in your relay service for sensitive values
3. **Restrict bot permissions** - Telegram bots can only read messages sent to them directly
4. **Monitor relay service logs** for unusual activity

## Example Configurations

### Minimal Setup

```yaml
alerts:
  webhooks:
    - url: "https://your-relay-service.com/webhook"
      enabled: true
```

### Production Setup

```yaml
alerts:
  webhooks:
    # Primary: Telegram via Pipedream
    - url: "https://eo1234abc.m.pipedream.net"
      enabled: true
      on_failure: true
      on_recovery: true
      cooldown_seconds: 300

    # Backup: Slack for redundancy
    - url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      enabled: true
      on_failure: true
      on_recovery: false  # Only critical alerts to Slack
      cooldown_seconds: 600
```

## Webhook Payload Reference

WebStatusπ sends this JSON structure to your relay service:

```json
{
  "event": "url_down",
  "url": {
    "name": "API_PROD",
    "url": "https://api.example.com"
  },
  "status": {
    "code": 503,
    "success": false,
    "response_time_ms": 5000,
    "error": "Service Unavailable",
    "timestamp": "2026-01-21T10:30:00Z"
  },
  "previous_status": "up"
}
```

| Field | Description |
|-------|-------------|
| `event` | Either `url_down`, `url_up`, or `test` |
| `url.name` | The URL's configured name |
| `url.url` | The full URL being monitored |
| `status.code` | HTTP status code (null if connection failed) |
| `status.success` | Boolean indicating if check passed |
| `status.response_time_ms` | Response time in milliseconds |
| `status.error` | Error message if failed |
| `status.timestamp` | ISO 8601 timestamp |
| `previous_status` | `up`, `down`, or `null` (first check) |

## Related Documentation

- [Webhook Alerts](../README.md#-webhook-alerts) - General webhook configuration
- [Troubleshooting](TROUBLESHOOTING.md) - General troubleshooting guide
- [Architecture](ARCHITECTURE.md) - System design and alert flow
