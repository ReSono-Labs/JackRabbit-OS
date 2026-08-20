---
name: voice-mail
description: Safely read, organize, draft, review, and send email through the built-in ReSono Mail tools.
license: Apache-2.0
compatibility: Requires a configured ReSono Mail account and the built-in Mail tool set.
metadata:
  owner: resono-labs
---

# Voice Mail

Use the local synchronized Mail tools for mailbox questions. Identify the mailbox when more than one account could match.

Before sending, create a pending draft. Read the exact recipients, subject, and complete body aloud. Ask whether it is okay to send. Call the send tool only after a new, explicit affirmative answer from the user.

Never claim a message was sent when the tool reports failure. If SMTP succeeded but Sent filing is pending, say that the message was sent and its Sent-folder copy is still being reconciled.

There is no mail deletion capability. Do not suggest, simulate, or attempt delete, trash, purge, or expunge operations. Archive or move only to an explicitly non-destructive folder.
