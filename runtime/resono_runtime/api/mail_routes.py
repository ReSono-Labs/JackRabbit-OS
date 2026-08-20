from __future__ import annotations

from typing import TYPE_CHECKING

from resono_runtime.domains.mail.repository import MailAccountLimitError, MailRepository
from resono_runtime.domains.mail.service import MailService
from resono_runtime.security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class MailRoutes:
    """Mail account configuration/status only; never exposes message content."""

    def __init__(self, repository: MailRepository, service: MailService) -> None:
        self._repository = repository
        self._service = service

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if path != "/v1/management/mail/accounts" and not path.startswith("/v1/management/mail/accounts/"):
            return False
        if not self._session(request, pairing, mutation=False):
            return True
        if path == "/v1/management/mail/accounts":
            request.respond_json(200, {"accounts": [_view(item) for item in self._repository.list_accounts()]})
            return True
        item = self._repository.get_account(path.rsplit("/", 1)[-1])
        if item is None:
            _error(request, 404, "mail_account_not_found", "Mail account not found.")
        else:
            request.respond_json(200, _view(item))
        return True

    def handle_post(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/mail/accounts"):
            return False
        if not self._session(request, pairing, mutation=True):
            return True
        payload = request.request_json(max_bytes=16_384)
        if payload is None:
            return True
        try:
            if path == "/v1/management/mail/accounts":
                item = self._service.connect_account(
                    label=_string(payload, "label"), email_address=_string(payload, "emailAddress"),
                    username=_string(payload, "username"), password=_string(payload, "password"),
                    imap_host=_string(payload, "imapHost"), imap_port=_port(payload, "imapPort"),
                    imap_security=_security(payload, "imapSecurity"), smtp_host=_string(payload, "smtpHost"),
                    smtp_port=_port(payload, "smtpPort"), smtp_security=_security(payload, "smtpSecurity"),
                )
                request.respond_json(201, _view(item))
                return True
            if path.endswith("/sync"):
                account_id = path.split("/")[-2]
                self._service.sync(account_id)
                item = self._repository.get_account(account_id)
                request.respond_json(200, _view(item) if item is not None else {})
                return True
        except MailAccountLimitError as error:
            _error(request, 409, "mail_account_limit", str(error)); return True
        except (TypeError, ValueError) as error:
            _error(request, 400, "invalid_mail_account", str(error)); return True
        except Exception:
            _error(request, 502, "mail_provider_unavailable", "Mail provider validation or synchronization failed."); return True
        _error(request, 404, "not_found", "Not found.")
        return True

    def handle_delete(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/mail/accounts/"):
            return False
        if not self._session(request, pairing, mutation=True):
            return True
        account_id = path.rsplit("/", 1)[-1]
        if not self._repository.remove_account_local(account_id):
            _error(request, 404, "mail_account_not_found", "Mail account not found.")
        else:
            request.respond_json(200, {"mailAccountId": account_id, "removed": True})
        return True

    @staticmethod
    def _session(request: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
        if pairing is None:
            _error(request, 503, "management_unavailable", "Management pairing is unavailable."); return False
        return request.browser_session(pairing, mutation=mutation) is not None


def _view(item: object) -> dict[str, object]:
    configuration = item.configuration
    return {"mailAccountId": configuration.account_id, "label": configuration.label, "emailAddress": configuration.email_address, "imapHost": configuration.imap_host, "imapPort": configuration.imap_port, "imapSecurity": configuration.imap_security, "smtpHost": configuration.smtp_host, "smtpPort": configuration.smtp_port, "smtpSecurity": configuration.smtp_security, "enabled": item.enabled, "credentialPresent": item.credential_present, "syncState": item.last_sync_state, "syncDetail": item.last_sync_detail, "lastSyncAt": item.last_sync_at, "nextSyncAt": item.next_sync_at}


def _string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{key} is required.")
    return value.strip()


def _port(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535: raise ValueError(f"{key} is invalid.")
    return value


def _security(payload: dict[str, object], key: str) -> str:
    value = _string(payload, key)
    if value not in {"tls", "starttls"}: raise ValueError(f"{key} must be tls or starttls.")
    return value


def _error(request: "RouteRequest", status: int, code: str, message: str) -> None:
    request.respond_json(status, {"error": {"code": code, "message": message}})
