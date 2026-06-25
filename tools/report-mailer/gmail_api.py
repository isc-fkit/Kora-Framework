#!/usr/bin/env python3
"""
gmail_api.py — Gửi email qua Gmail API trên HTTPS (443), ĐỊNH TUYẾN QUA PROXY.

Dùng cho FALLBACK khi mạng chặn mọi cổng SMTP nhưng proxy công ty cho CONNECT tới 443
(vd FPT: SMTP 587/465/25/2525 đều chặn, proxy.hcm.fpt.vn:80 cho CONNECT 443).

CHỈ thư viện chuẩn (urllib/json/base64/ssl). KHÔNG in token. Module này được
`send_report.py` import — tự nó không phải CLI.

Cách proxy hoạt động: với URL `https://…` + proxy `http://…`, urllib (http.client) tự phát
`CONNECT host:443` tới proxy rồi handshake TLS BÊN TRONG tunnel → đi được qua firewall chặn SMTP.
"""
import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/{user}/messages/send"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailAuthError(Exception):
    """Creds OAuth sai/hết hạn/scope thiếu (HTTP 400/401/403)."""


class GmailUnreachableError(Exception):
    """Không tới được endpoint (mạng/proxy/timeout)."""


def _build_opener(proxy_url=None):
    """Opener dùng proxy TƯỜNG MINH (deterministic cho cron). proxy_url rỗng → no-proxy rõ ràng
    (chặn proxy hệ thống sai làm hỏng máy đi mạng trực tiếp). TLS verify GIỮ bật."""
    proxy_handler = (urllib.request.ProxyHandler({"https": proxy_url, "http": proxy_url})
                     if proxy_url else urllib.request.ProxyHandler({}))
    https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context())
    return urllib.request.build_opener(proxy_handler, https_handler)


def _safe_read(err) -> str:
    try:
        return err.read().decode("utf-8", "replace")[:500]
    except Exception:  # noqa: BLE001
        return ""


def refresh_access_token(client_id, client_secret, refresh_token, proxy=None, timeout=30) -> str:
    """Đổi refresh_token → access_token (POST oauth2.googleapis.com/token)."""
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("ascii")
    req = urllib.request.Request(
        OAUTH_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    opener = _build_opener(proxy)
    try:
        with opener.open(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise GmailAuthError(f"OAuth token refresh lỗi HTTP {e.code}: {_safe_read(e)}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GmailUnreachableError(f"Không kết nối được oauth2.googleapis.com: {e}") from e
    token = payload.get("access_token")
    if not token:
        raise GmailAuthError(f"OAuth không trả access_token: {payload}")
    return token


def send_message(msg, access_token, api_user="me", proxy=None, timeout=30) -> dict:
    """Gửi 1 MIME message (object email.message) qua Gmail API. Trả JSON (có message id)."""
    # base64URL (KHÔNG phải base64 thường — Gmail từ chối '+'/'/').
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    body = json.dumps({"raw": raw}).encode("utf-8")
    url = GMAIL_SEND_URL.format(user=urllib.parse.quote(api_user, safe="@"))
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    })
    opener = _build_opener(proxy)
    try:
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = _safe_read(e)
        if e.code in (400, 401, 403):
            raise GmailAuthError(f"Gmail API từ chối (HTTP {e.code}): {detail}") from e
        raise GmailUnreachableError(f"Gmail API lỗi HTTP {e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GmailUnreachableError(f"Không kết nối được gmail.googleapis.com: {e}") from e
