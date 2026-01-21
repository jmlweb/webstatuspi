# Task #017: Telegram Bot Integration Documentation

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Docs
- **Created**: 2026-01-21
- **Started**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user who wants to receive alerts on my phone, I want a step-by-step guide to set up a Telegram bot so that I can receive instant push notifications when my monitored URLs fail or recover.

**Acceptance Criteria**:
- [x] Create `docs/TELEGRAM_SETUP.md` with complete setup guide
- [x] Include @BotFather walkthrough with example commands and expected responses
- [x] Document how to get chat ID (personal and group chats)
- [x] Provide working config.yaml example for Telegram webhook
- [x] Include message formatting examples (Markdown support)
- [x] Add troubleshooting section for common issues
- [x] Link from README.md alerting section
- [ ] Test the documentation by following it on a fresh Telegram account (user responsibility)

## Implementation Notes

### Document Structure

```markdown
# Telegram Bot Setup Guide

## Overview
Why Telegram? (free, instant push, no server needed)

## Prerequisites
- Telegram account (mobile or desktop app)
- WebStatusPi with webhook alerts configured (#016)

## Step 1: Create Your Bot
1. Open Telegram, search for @BotFather
2. Send /newbot
3. Choose a name (e.g., "My Server Monitor")
4. Choose a username (must end in "bot", e.g., "myserver_monitor_bot")
5. Copy the bot token (looks like: 123456789:ABCdefGHI...)

## Step 2: Get Your Chat ID

### Option A: Personal notifications
1. Start a chat with your new bot
2. Send any message
3. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Find "chat":{"id": YOUR_CHAT_ID}

### Option B: Group notifications
1. Add bot to your group
2. Send a message in the group
3. Use getUpdates method above
4. Group IDs are negative numbers (e.g., -100123456789)

## Step 3: Configure WebStatusPi

```yaml
alerts:
  webhooks:
    - url: "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&parse_mode=Markdown"
      enabled: true
      on_failure: true
      on_recovery: true
      cooldown_seconds: 300
```

## Step 4: Test Your Setup

```bash
webstatuspi test-alert
```

## Message Formatting

Telegram supports Markdown in messages:
- *bold* with `*text*`
- _italic_ with `_text_`
- `code` with backticks
- [links](url) with `[text](url)`

## Troubleshooting

### Bot not responding
- Did you start a conversation with the bot first?
- Is the bot token correct?

### Wrong chat ID
- Personal IDs are positive numbers
- Group IDs are negative (start with -)
- Channel IDs start with -100

### Messages not arriving
- Check bot wasn't removed from group
- Verify webhook URL is correct
- Test with curl first
```

### Telegram API Details

The webhook URL format for Telegram:
```
https://api.telegram.org/bot{TOKEN}/sendMessage
```

POST body (what WebStatusPi sends):
```json
{
  "chat_id": "123456789",
  "text": "🔴 *APP_ES* is DOWN\nStatus: 503\nTime: 2026-01-21 10:30:15",
  "parse_mode": "Markdown"
}
```

**Note**: Task #016 needs to format the webhook payload appropriately for Telegram's API, or document how users can use an intermediary service (like n8n, Zapier) to transform the generic payload.

### Alternative: Direct Telegram Support

If during #016 implementation we decide generic webhooks don't work well with Telegram's API format, consider adding native Telegram support:

```yaml
alerts:
  telegram:
    enabled: true
    bot_token: "123456789:ABCdef..."
    chat_id: "987654321"
```

This would be a separate enhancement, not part of this documentation task.

## Files to Modify

**New Files**:
- `docs/TELEGRAM_SETUP.md` - Complete setup guide

**Modified Files**:
- `README.md` - Add link to Telegram guide in Alerts section
- `docs/TROUBLESHOOTING.md` - Add Telegram-specific troubleshooting

## Dependencies

- #016 (Webhook Alerts) - Documentation requires working webhook feature to reference

## Progress Log

- [2026-01-21 15:30] Started task - Ready to create Telegram setup documentation
- [2026-01-21] Completed task:
  - Created `docs/TELEGRAM_SETUP.md` with comprehensive guide
  - Documented @BotFather workflow and chat ID retrieval
  - Added relay service options (Pipedream, n8n, Make.com) since WebStatusPi sends generic JSON
  - Included Pipedream code example for payload transformation
  - Added message formatting table and troubleshooting section
  - Updated README.md with link in Supported Services table and Documentation section
  - Updated TROUBLESHOOTING.md with Telegram-specific section

## Learnings

- WebStatusPi sends generic webhook payloads, not Telegram-specific format
- A relay service (Pipedream, n8n, etc.) is required to transform the payload to Telegram's API format
- This is actually more flexible: the same webhook can be routed to multiple services
