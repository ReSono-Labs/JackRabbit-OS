---
name: voice-mail
description: Safely read, organize, draft, review, and send email through the built-in ReSono Mail tools.
license: Apache-2.0
compatibility: Requires a configured ReSono Mail account and the built-in Mail tool set.
metadata:
  owner: resono-labs
---

# Voice Mail

Use the local synchronized Mail tools for mailbox questions. When exactly one Mail account is available, use it automatically. When several accounts are available and the user did not name one, tell them the available account names and ask which one they want to use. Pass that human-readable account name or email address to the tool. Never ask the user for an internal account ID.

Before sending, create a pending draft. Read the exact recipients, subject, and complete body aloud. Ask whether it is okay to send. Call the send tool only after a new, explicit affirmative answer from the user.

Never claim a message was sent when the tool reports failure. If SMTP succeeded but Sent filing is pending, say that the message was sent and its Sent-folder copy is still being reconciled.

There is no mail deletion capability. Do not suggest, simulate, or attempt delete, trash, purge, or expunge operations. Archive or move only to an explicitly non-destructive folder.

Messages already in a Trash/Deleted folder or carrying the IMAP deleted flag are outside the Voice Mail boundary. Do not report, search, read, summarize, attach, or act on them.
