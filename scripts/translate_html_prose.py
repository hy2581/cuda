#!/usr/bin/env python3
"""
Translate remaining English prose in the Chinese CUDA guide HTML.

Uses Google Translate's public web endpoint (same idea as deep_translator) with an
explicit timeout. Skips code: <script>, <style>, <pre>, <code>, and .highlight blocks.

Progress is saved to scripts/translate_cache_en_zh.json so a run can be resumed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

GOOGLE_M = "https://translate.google.com/m"
SKIP_PARENT_NAMES = frozenset({"script", "style", "pre", "code", "kbd", "samp"})
ATTRS_TO_TRANSLATE = ("title", "alt", "placeholder", "aria-label")
# Rare in source; stripped from strings before batching.
SEP = "\n<<<SEG>>>\n"


def _cache_key(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


def _in_skipped_subtree(tag: Tag) -> bool:
    """Skip code-like regions except Pygments line comments (span.c1) inside <pre>."""
    if tag.name == "pre":
        return True
    for p in tag.parents:
        if not isinstance(p, Tag):
            continue
        if p.name in ("script", "style"):
            return True
        cls = " ".join(p.get("class") or [])
        if "highlight" in cls:
            return True
        if p.name == "pre":
            if "c1" in (tag.get("class") or []):
                return False
            return True
        if p.name == "code":
            return True
        if p.name in ("kbd", "samp"):
            return True
    return False


def _looks_like_url(s: str) -> bool:
    t = s.strip()
    if re.match(r"^https?://", t, re.I):
        return True
    if "/" in t and len(t) > 15:
        if re.fullmatch(r"[\w./#:?=&;\-\%+~,\[\]]+", t):
            return True
    return False


def _should_translate_string(s: str) -> bool:
    if not s.strip():
        return False
    if not re.search(r"[A-Za-z]{3,}", s):
        return False
    st = s.strip()
    cjk = sum(1 for c in st if "\u4e00" <= c <= "\u9fff")
    if cjk and cjk / len(st) > 0.12:
        return False
    if _looks_like_url(s):
        return False
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", st):
        return False
    return True


def _collect_text_targets(soup: BeautifulSoup) -> list[NavigableString]:
    nodes: list[NavigableString] = []
    for el in soup.descendants:
        if not isinstance(el, NavigableString):
            continue
        parent = el.parent
        if not isinstance(parent, Tag):
            continue
        if _in_skipped_subtree(parent):
            continue
        if not _should_translate_string(str(el)):
            continue
        nodes.append(el)
    return nodes


def _collect_attr_targets(soup: BeautifulSoup) -> list[tuple[Tag, str, str]]:
    out: list[tuple[Tag, str, str]] = []
    for tag in soup.find_all(True):
        if _in_skipped_subtree(tag):
            continue
        for attr in ATTRS_TO_TRANSLATE:
            if attr not in tag.attrs:
                continue
            val = tag.get(attr)
            if not isinstance(val, str) or not _should_translate_string(val):
                continue
            out.append((tag, attr, val))
    # Narrative meta description only (not generator/keywords/viewport).
    for tag in soup.find_all("meta"):
        if tag.get("name") != "description":
            continue
        if _in_skipped_subtree(tag):
            continue
        val = tag.get("content")
        if isinstance(val, str) and _should_translate_string(val):
            out.append((tag, "content", val))
    return out


def _google_translate(
    session: requests.Session,
    text: str,
    *,
    source: str,
    target: str,
    timeout: float,
) -> str:
    text = text.strip()
    if not text:
        return text
    if len(text) > 4800:
        mid = len(text) // 2
        return _google_translate(session, text[:mid], source=source, target=target, timeout=timeout) + _google_translate(
            session, text[mid:], source=source, target=target, timeout=timeout
        )
    params = {"sl": source, "tl": target, "q": text}
    for attempt in range(6):
        try:
            r = session.get(GOOGLE_M, params=params, timeout=timeout)
            if r.status_code == 429:
                time.sleep(8 + attempt * 4)
                continue
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            el = (
                soup.find("div", class_="t0")
                or soup.find("div", class_="result-container")
                or soup.find("div", class_=lambda c: c and "result" in " ".join(c).lower())
            )
            if not el:
                raise RuntimeError("translation element not found")
            out = el.get_text()
            if not out.strip():
                raise RuntimeError("empty translation")
            return out
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return text


def _translate_batch_cached(
    session: requests.Session,
    parts: list[str],
    cache: dict[str, str],
    *,
    source: str,
    target: str,
    timeout: float,
    sleep_s: float,
) -> list[str]:
    """Translate a list of strings, using one HTTP call when possible."""
    if len(parts) == 1:
        s = parts[0]
        k = _cache_key(s)
        if k not in cache or not cache[k]:
            cache[k] = _google_translate(session, s, source=source, target=target, timeout=timeout)
            time.sleep(sleep_s)
        return [cache[k]]

    safe_parts = [p.replace(SEP, " ").replace("\r", " ") for p in parts]
    blob_key = _cache_key(SEP.join(safe_parts))
    if blob_key in cache and SEP in (cache[blob_key] or ""):
        t = cache[blob_key]
        out = t.split(SEP)
        if len(out) == len(safe_parts):
            return out

    blob = SEP.join(safe_parts)
    if len(blob) > 4800:
        mid = max(1, len(safe_parts) // 2)
        a = _translate_batch_cached(session, safe_parts[:mid], cache, source=source, target=target, timeout=timeout, sleep_s=sleep_s)
        b = _translate_batch_cached(session, safe_parts[mid:], cache, source=source, target=target, timeout=timeout, sleep_s=sleep_s)
        return a + b

    translated = _google_translate(session, blob, source=source, target=target, timeout=timeout)
    time.sleep(sleep_s)
    out = translated.split(SEP)
    if len(out) == len(safe_parts):
        cache[blob_key] = translated
        return out

    # Separator mangled: fall back per string, then store a synthetic blob for mapping
    per: list[str] = []
    for p in safe_parts:
        per.append(
            _translate_batch_cached(session, [p], cache, source=source, target=target, timeout=timeout, sleep_s=sleep_s)[0]
        )
    cache[blob_key] = SEP.join(per)
    return per


def _load_soup(path: Path) -> BeautifulSoup:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines(True)
    if lines and lines[0].strip() == "html":
        raw = "".join(lines[1:])
    if not raw.lstrip().startswith("<!DOCTYPE"):
        raw = "<!DOCTYPE html>\n" + raw
    return BeautifulSoup(raw, "html.parser")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=Path("cuda-c-programming-guide.zh-CN.html"))
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--cache", type=Path, default=Path("scripts/translate_cache_en_zh.json"))
    ap.add_argument("--sleep", type=float, default=0.25, help="Pause after each translation request")
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--chunk-chars", type=int, default=4200, help="Max chars per batched request")
    ap.add_argument("--source", default="en")
    ap.add_argument("--target", default="zh-CN")
    args = ap.parse_args()
    out_path = args.output or args.input

    cache = _load_cache(args.cache)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; CUDA-Guide-Translator/1.0)",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    )

    soup = _load_soup(args.input)
    html_tag = soup.find("html")
    if isinstance(html_tag, Tag):
        html_tag["lang"] = "zh-CN"

    text_nodes = _collect_text_targets(soup)
    attr_entries = _collect_attr_targets(soup)
    strings = [str(n) for n in text_nodes] + [v for _, _, v in attr_entries]
    uniq = sorted(set(strings), key=len, reverse=True)

    def batch_fully_cached(parts: list[str]) -> bool:
        if len(parts) == 1:
            return bool(cache.get(_cache_key(parts[0])))
        safe = [p.replace(SEP, " ").replace("\r", " ") for p in parts]
        bk = _cache_key(SEP.join(safe))
        blob = cache.get(bk)
        if not blob:
            return False
        return len(blob.split(SEP)) == len(parts)

    i = 0
    batch_idx = 0
    while i < len(uniq):
        group: list[str] = []
        size = 0
        while i < len(uniq):
            s = uniq[i]
            add = len(s) + (len(SEP) if group else 0)
            if group and size + add > args.chunk_chars:
                break
            group.append(s)
            size += add
            i += 1
            if size >= args.chunk_chars:
                break

        if batch_fully_cached(group):
            continue

        batch_idx += 1
        print(f"Batch {batch_idx}: {len(group)} strings, ~{size} chars", file=sys.stderr)
        _translate_batch_cached(
            session,
            group,
            cache,
            source=args.source,
            target=args.target,
            timeout=args.timeout,
            sleep_s=args.sleep,
        )
        if batch_idx % 5 == 0:
            _save_cache(args.cache, cache)

    _save_cache(args.cache, cache)

    mapping: dict[str, str] = {}
    i = 0
    while i < len(uniq):
        group: list[str] = []
        size = 0
        while i < len(uniq):
            s = uniq[i]
            add = len(s) + (len(SEP) if group else 0)
            if group and size + add > args.chunk_chars:
                break
            group.append(s)
            size += add
            i += 1
            if size >= args.chunk_chars:
                break
        if len(group) == 1:
            k0 = _cache_key(group[0])
            if k0 not in cache:
                _translate_batch_cached(
                    session,
                    group,
                    cache,
                    source=args.source,
                    target=args.target,
                    timeout=args.timeout,
                    sleep_s=args.sleep,
                )
            mapping[group[0]] = cache[k0]
        else:
            safe_group = [p.replace(SEP, " ").replace("\r", " ") for p in group]
            blob_key = _cache_key(SEP.join(safe_group))
            if blob_key not in cache or len(cache[blob_key].split(SEP)) != len(group):
                _translate_batch_cached(
                    session,
                    group,
                    cache,
                    source=args.source,
                    target=args.target,
                    timeout=args.timeout,
                    sleep_s=args.sleep,
                )
            parts = cache[blob_key].split(SEP)
            if len(parts) != len(group):
                for g in group:
                    kg = _cache_key(g)
                    if kg not in cache:
                        _translate_batch_cached(
                            session,
                            [g],
                            cache,
                            source=args.source,
                            target=args.target,
                            timeout=args.timeout,
                            sleep_s=args.sleep,
                        )
                    mapping[g] = cache[kg]
            else:
                for a, b in zip(group, parts):
                    mapping[a] = b

    replaced = 0
    for node in text_nodes:
        orig = str(node)
        new = mapping.get(orig, orig)
        if new != orig:
            node.replace_with(new)
            replaced += 1

    for tag, attr, val in attr_entries:
        new = mapping.get(val, val)
        if new != val:
            tag[attr] = new
            replaced += 1

    print(f"Replaced segments: {replaced}", file=sys.stderr)
    out_path.write_text(str(soup), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
