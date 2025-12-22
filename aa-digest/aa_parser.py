import re
from html import unescape


def _qp_cleanup(s: str) -> str:
    if not s:
        return ""
    s = s.replace("=\r\n", "").replace("=\n", "")
    s = s.replace("=3D", "=")
    return unescape(s)


def extract_breakdown_id(url: str) -> str:
    m = re.search(r"breakdown=(\d+)", url or "")
    return m.group(1) if m else ""


def parse_projects_from_plain(text_plain: str) -> list[dict]:
    if not text_plain:
        return []

    lines = [ln.rstrip("\r") for ln in text_plain.splitlines()]

    def looks_like_role(line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        if re.search(r"\byears old\b", s, flags=re.I):
            return False
        if ";" in s:
            return False
        if len(s) > 70:
            return False
        if not re.match(r"^[A-Za-z0-9\-\(\) '\.]+$", s):
            return False
        return True

    roles = []
    i = 0
    while i < len(lines):
        title = (lines[i] or "").strip()
        if not title:
            i += 1
            continue

        j = i + 1
        while j < len(lines) and not (lines[j] or "").strip():
            j += 1
        if j >= len(lines):
            break

        url_line = (lines[j] or "").strip()
        if not re.match(r"^https?://actorsaccess\.com/projects/\?[^\s]*breakdown=\d+", url_line):
            i += 1
            continue

        apply_url = url_line
        breakdown_id = extract_breakdown_id(apply_url)

        k = j + 1
        role_names = []
        while k < len(lines):
            ln = lines[k]

            if ln and not ln.startswith(" "):
                look = k + 1
                while look < len(lines) and not (lines[look] or "").strip():
                    look += 1
                if look < len(lines) and re.match(
                    r"^https?://actorsaccess\.com/projects/\?[^\s]*breakdown=\d+",
                    (lines[look] or "").strip(),
                ):
                    break
                k += 1
                continue

            if ln and ln.startswith(" "):
                cand = ln.strip()
                if looks_like_role(cand):
                    role_names.append(cand)

            k += 1

        for rn in role_names:
            roles.append(
                {
                    "title": title,
                    "role": rn,
                    "apply_url": apply_url,
                    "breakdown_id": breakdown_id,
                }
            )

        i = k

    return roles


def _strip_tags(html_fragment: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", html_fragment)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def extract_meta_by_breakdown_from_html(html: str) -> dict[str, str]:
    if not html:
        return {}

    h = _qp_cleanup(html)

    pattern = re.compile(
        r'breakdown=(\d+)[^"\']*["\'][^>]*>.*?</a>\s*</div>\s*'
        r'<div[^>]*>\s*(.*?)\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )

    meta_map: dict[str, str] = {}
    for m in pattern.finditer(h):
        bid = m.group(1)
        meta_html = m.group(2)

        meta_txt = _strip_tags(meta_html)
        meta_txt = meta_txt.replace("\xa0", " ").replace("&nbsp;", " ")
        meta_txt = re.sub(r"\s+", " ", meta_txt).strip()

        if bid and re.search(r"\b(NON-UNION|SAG-AFTRA|UNION)\b", meta_txt, flags=re.I):
            meta_map[bid] = meta_txt

    return meta_map


def is_vertical_meta(meta: str) -> bool:
    return "vertical short form" in (meta or "").lower()
