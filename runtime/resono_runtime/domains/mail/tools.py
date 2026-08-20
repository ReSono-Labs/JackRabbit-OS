from __future__ import annotations

import json

from resono_runtime.agents import AudienceResource, AudienceResourceKind
from resono_runtime.domains.mail.repository import MailRepository
from resono_runtime.domains.mail.service import MailService
from resono_runtime.tools import ToolCatalog, ToolDefinition, ToolInvocationContext, ToolInvocationResult


MAIL_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "mail")

MAIL_TOOL_NAMES = (
    "email_account_status", "email_list_folders", "email_check", "email_get_unread",
    "email_search", "email_read", "email_read_attachment", "email_contact_lookup",
    "email_mark_read", "email_mark_unread", "email_compose", "email_send_pending",
    "email_archive", "email_create_folder", "email_rename_folder", "email_move_message",
)


def register_mail_tools(catalog: ToolCatalog, repository: MailRepository, service: MailService) -> None:
    for name in MAIL_TOOL_NAMES:
        catalog.register(
            ToolDefinition(
                tool_id=f"builtin.mail.{name}.v1",
                name=name,
                description=_description(name),
                input_schema=_schema(name),
                handler=lambda _: ToolInvocationResult("Mail requires an agent invocation context.", is_error=True),
                context_handler=lambda context, arguments, tool=name: _invoke(tool, context, arguments, repository, service),
                effect_class="read" if name in MAIL_TOOL_NAMES[:8] else "external_write",
                audience_resource=MAIL_TOOL_SET,
                available_to=lambda _: any(item.enabled and item.credential_present for item in repository.list_accounts()),
            )
        )


def _invoke(name: str, context: ToolInvocationContext, arguments: dict[str, object], repository: MailRepository, service: MailService) -> ToolInvocationResult:
    try:
        if name == "email_account_status":
            value = [_account_view(item) for item in repository.list_accounts()]
            return ToolInvocationResult(json.dumps(value, separators=(",", ":")), structured_content={"result": value})
        else:
            account_id = _account(arguments, repository)
        if name == "email_list_folders":
            value = list(repository.list_folders(account_id))
        elif name in {"email_check", "email_get_unread", "email_search"}:
            value = list(repository.list_messages(account_id, folder_id=_optional(arguments, "folderId"), query=_optional(arguments, "query"), unread_only=name == "email_get_unread", limit=_limit(arguments)))
        elif name == "email_read":
            value = repository.read_message(account_id, _required(arguments, "messageId"))
        elif name == "email_read_attachment":
            value = service.read_attachment(account_id, _required(arguments, "attachmentId"))
        elif name == "email_contact_lookup":
            messages = repository.list_messages(account_id, query=_required(arguments, "query"), limit=_limit(arguments))
            seen: dict[str, list[object]] = {}
            for message in messages:
                for display, address in message["from"]:
                    seen.setdefault(address, [display, address])
            value = list(seen.values())
        elif name == "email_mark_read":
            service.set_read_state(account_id, _required(arguments, "messageId"), read=True); value = {"state": "completed"}
        elif name == "email_mark_unread":
            service.set_read_state(account_id, _required(arguments, "messageId"), read=False); value = {"state": "completed"}
        elif name == "email_archive":
            service.archive_message(account_id, _required(arguments, "messageId")); value = {"state": "completed"}
        elif name == "email_move_message":
            service.move_message(account_id, _required(arguments, "messageId"), _required(arguments, "destinationFolder")); value = {"state": "completed"}
        elif name == "email_create_folder":
            service.create_folder(account_id, _required(arguments, "folderName")); value = {"state": "completed"}
        elif name == "email_rename_folder":
            service.rename_folder(account_id, _required(arguments, "sourceFolder"), _required(arguments, "destinationFolder")); value = {"state": "completed"}
        elif name == "email_compose":
            value = service.prepare_send(account_id, recipients=tuple(_string_list(arguments, "to")), subject=_required(arguments, "subject"), body=_required(arguments, "body"), voice_session_id=context.voice_session_id or "", tool_call_id=context.tool_call_id or "", user_utterance_id=context.user_utterance_id or 0)
            value["confirmationRequired"] = True
        elif name == "email_send_pending":
            value = service.confirm_send(
                account_id,
                draft_id=_required(arguments, "draftId"),
                content_hash=_required(arguments, "contentHash"),
                voice_session_id=context.voice_session_id or "",
                user_utterance=context.user_utterance or "",
                user_utterance_id=context.user_utterance_id or 0,
            )
        else:
            raise ValueError("Mail tool is unavailable.")
        return ToolInvocationResult(json.dumps(value, separators=(",", ":")), structured_content={"result": value})
    except (TypeError, ValueError, RuntimeError) as error:
        return ToolInvocationResult(str(error), is_error=True)


def _schema(name: str) -> dict[str, object]:
    properties: dict[str, object] = {"mailAccountId": {"type": "string"}}
    required: list[str] = []
    if name not in {"email_account_status"}:
        required.append("mailAccountId")
    fields = {
        "email_read": ("messageId",), "email_mark_read": ("messageId",), "email_mark_unread": ("messageId",),
        "email_archive": ("messageId",), "email_read_attachment": ("attachmentId",),
        "email_contact_lookup": ("query",), "email_compose": ("to", "subject", "body"),
        "email_send_pending": ("draftId", "contentHash"),
        "email_create_folder": ("folderName",), "email_rename_folder": ("sourceFolder", "destinationFolder"),
        "email_move_message": ("messageId", "destinationFolder"),
    }
    for field in fields.get(name, ()):
        properties[field] = {"type": "array", "items": {"type": "string"}} if field == "to" else {"type": "string"}
        required.append(field)
    if name in {"email_check", "email_get_unread", "email_search"}:
        properties.update({"folderId": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "integer"}})
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _description(name: str) -> str:
    if name == "email_compose":
        return "Create a pending email draft. Read the exact recipients, subject, and body to the user and ask whether it is okay to send. This does not send mail."
    if name == "email_send_pending":
        return "Send the exact pending email only after the user explicitly approves the reviewed draft in their latest Voice utterance."
    return name.replace("email_", "").replace("_", " ").capitalize() + " using the local synchronized Mail service."


def _account(arguments: dict[str, object], repository: MailRepository) -> str:
    value = arguments.get("mailAccountId")
    if isinstance(value, str) and repository.get_account(value) is not None:
        return value
    if value is None:
        accounts = repository.list_accounts()
        if len(accounts) == 1:
            return accounts[0].configuration.account_id
    raise ValueError("A valid Mail account ID is required.")


def _required(arguments: dict[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{key} is required.")
    return value.strip()


def _optional(arguments: dict[str, object], key: str) -> str | None:
    value = arguments.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _string_list(arguments: dict[str, object], key: str) -> list[str]:
    value = arguments.get(key)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value): raise ValueError(f"{key} must be a non-empty string list.")
    return [item.strip() for item in value]


def _limit(arguments: dict[str, object]) -> int:
    value = arguments.get("limit", 25)
    return max(1, min(value, 100)) if isinstance(value, int) and not isinstance(value, bool) else 25


def _account_view(item: object) -> dict[str, object]:
    configuration = item.configuration
    return {"mailAccountId": configuration.account_id, "label": configuration.label, "emailAddress": configuration.email_address, "enabled": item.enabled, "syncState": item.last_sync_state, "lastSyncAt": item.last_sync_at, "nextSyncAt": item.next_sync_at}
