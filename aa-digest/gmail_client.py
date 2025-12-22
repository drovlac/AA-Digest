import os
import pickle
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

def get_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)

def get_label_id(service, label_name: str):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label.get("name") == label_name:
            return label.get("id")
    raise ValueError(f"Label not found: {label_name}")

def get_latest_message_id(service, label_id: str):
    res = service.users().messages().list(
        userId="me", labelIds=[label_id], maxResults=1
    ).execute()
    msgs = res.get("messages", [])
    return msgs[0]["id"] if msgs else None

def _walk_parts(payload):
    if "parts" in payload:
        for p in payload["parts"]:
            yield from _walk_parts(p)
    else:
        yield payload

def _decode_part(part):
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "ignore")

def read_message(service, msg_id: str):
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    headers = msg.get("payload", {}).get("headers", [])
    subject = next(
        (h["value"] for h in headers if h.get("name", "").lower() == "subject"),
        "(no subject)"
    )

    text_plain_parts = []
    html_parts = []

    payload = msg.get("payload", {})
    for part in _walk_parts(payload):
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            text_plain_parts.append(_decode_part(part))
        elif mime == "text/html":
            html_parts.append(_decode_part(part))

    text_plain = "\n".join(text_plain_parts).strip() if text_plain_parts else msg.get("snippet", "")
    html = "\n".join(html_parts).strip()

    return subject, text_plain, html
