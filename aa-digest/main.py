import os
import re
from dotenv import load_dotenv

from gmail_client import (
    get_service,
    get_label_id,
    get_latest_message_id,
    read_message,
)
from notifier import send_telegram_message
from aa_parser import (
    parse_projects_from_plain,
    extract_meta_by_breakdown_from_html,
    is_vertical_meta,
)

load_dotenv()

LABEL_NAME = os.environ["LABEL_NAME"]
STATE_FILE = "state.txt"

VERSION = "AA DIGEST v17 (PLAIN APPLY LINKS + HTML META + NO VERTICALS)"


def normalize_location(loc: str) -> str:
    if not loc:
        return loc
    s = loc.strip()
    if re.search(r"\bLos\s+Angeles\b", s, flags=re.I) or re.search(r"\bLA\b", s, flags=re.I):
        return "LA"
    return s


def format_meta_with_pipes(meta: str) -> str:
    """
    "Short NON-UNION Los Angeles, CA" -> "Short | Non-Union | LA"
    "Short SAG-AFTRA Los Angeles, CA, USA" -> "Short | SAG-AFTRA | LA"
    """
    meta = (meta or "").strip()
    if not meta:
        return ""

    m = re.match(r"^(.*?)\s+(NON-UNION|SAG-AFTRA|UNION)\s+(.*)$", meta, flags=re.I)
    if not m:
        return meta

    proj_type = m.group(1).strip()
    union_raw = m.group(2).strip().upper()
    loc = normalize_location(m.group(3).strip())

    if union_raw == "SAG-AFTRA":
        union = "SAG-AFTRA"
    elif union_raw == "NON-UNION":
        union = "Non-Union"
    else:
        union = "Union"

    return f"{proj_type} | {union} | {loc}"


def format_project_message(title: str, meta: str, first_role: str, apply_url: str, role_count: int) -> str:
    role_line = (first_role or "").strip()
    if role_count > 1:
        role_line = f"{role_line} (and others)"

    meta_line = format_meta_with_pipes(meta)

    parts = [
        (title or "").strip(),
        meta_line,
        role_line,
        f"Apply: {apply_url.strip()}",
    ]

    return "\n".join([p for p in parts if p])[:3500]


def main():
    print(VERSION)

    service = get_service()
    label_id = get_label_id(service, LABEL_NAME)

    msg_id = get_latest_message_id(service, label_id)
    if not msg_id:
        print("No new emails.")
        return

    if os.path.exists(STATE_FILE):
        last_id = open(STATE_FILE, "r", encoding="utf-8").read().strip()
        if msg_id == last_id:
            print("Already processed.")
            return

    _, text_plain, html = read_message(service, msg_id)

    # Apply links + roles from plain text (these links work)
    roles = parse_projects_from_plain(text_plain)

    # Meta from HTML (type/union/location + vertical detection)
    meta_map = extract_meta_by_breakdown_from_html(html)

    # Group by project (breakdown_id) so multiple roles => "(and others)"
    grouped = {}
    skipped_vertical_projects = 0

    for r in roles:
        bid = (r.get("breakdown_id") or "").strip()
        title = r.get("title", "")
        role = r.get("role", "")
        apply_url = r.get("apply_url", "")

        meta = meta_map.get(bid, "")

        # Exclude verticals (using the HTML meta, which contains "Vertical Short Form")
        if is_vertical_meta(meta):
            skipped_vertical_projects += 1
            continue

        key = bid if bid else (title.strip(), apply_url.strip())
        if key not in grouped:
            grouped[key] = {"title": title, "meta": meta, "apply_url": apply_url, "roles": []}

        grouped[key]["roles"].append(role)

    sent = 0
    for info in grouped.values():
        roles_list = [x for x in info["roles"] if x and x.strip()]
        if not roles_list:
            continue

        msg = format_project_message(
            title=info["title"],
            meta=info["meta"],
            first_role=roles_list[0],
            apply_url=info["apply_url"],
            role_count=len(roles_list),
        )

        if send_telegram_message(msg):
            sent += 1

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(msg_id)

    print(f"Done. SentProjects={sent} | SkippedVerticalProjects={skipped_vertical_projects} | ParsedRoles={len(roles)}")


if __name__ == "__main__":
    main()
