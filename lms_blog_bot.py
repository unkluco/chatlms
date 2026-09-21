from __future__ import annotations
import json, sys, time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "processed.json"
PROFILE_DIR = ROOT / ".browser_profile"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def debug_log(cfg, msg):
    if bool(cfg.get("debug", False)):
        log("[DEBUG] " + msg)

def load_processed():
    if not STATE_PATH.exists():
        return set()
    try:
        return set(map(str, json.loads(STATE_PATH.read_text(encoding="utf-8")).get("processed_entry_ids", [])))
    except Exception:
        return set()

def save_processed(items):
    STATE_PATH.write_text(json.dumps({"processed_entry_ids": sorted(items)}, indent=2), encoding="utf-8")

def entry_id(url):
    try:
        x = parse_qs(urlparse(url).query).get("entryid")
        return x[0] if x else None
    except Exception:
        return None

def launch_browser(pw, headless=False):
    for channel in ("chrome", "msedge"):
        try:
            log(f"Mo trinh duyet {channel}...")
            return pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR), channel=channel,
                headless=headless, ignore_https_errors=True,
                viewport={"width": 1400, "height": 900},
                args=["--disable-notifications"])
        except Exception:
            pass
    return pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR), headless=headless,
        ignore_https_errors=True, viewport={"width": 1400, "height": 900})

def logged_out(page):
    return "/login/" in page.url.lower() or page.locator('input[name="username"]').count() > 0

def ensure_login(page, cfg):
    base_url = str(cfg.get("lms_base_url", "https://lms.iuh.edu.vn")).rstrip("/")
    login_url = base_url + "/login/index.php"
    page.goto(login_url, wait_until="domcontentloaded", timeout=45000)

    if not logged_out(page):
        log("Da co phien dang nhap LMS.")
        return

    username = str(cfg.get("username", "")).strip()
    password = str(cfg.get("password", ""))
    if username and password:
        log("Dang tu dong dang nhap LMS bang config.json...")
        try:
            page.locator('input[name="username"]').fill(username)
            page.locator('input[name="password"]').fill(password)
            page.locator('#loginbtn, button[type="submit"], input[type="submit"]').first.click(timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)
            if not logged_out(page):
                log("Tu dong dang nhap thanh cong.")
                return
            log("Tu dong dang nhap chua thanh cong. Co the LMS dang yeu cau CAPTCHA/MFA.")
        except Exception as exc:
            log(f"Tu dong dang nhap gap loi: {type(exc).__name__}")

    log("Dang cho dang nhap thu cong trong cua so trinh duyet...")
    while True:
        time.sleep(2)
        try:
            if not logged_out(page):
                log("Dang nhap thanh cong.")
                return
        except Exception:
            pass

def discover_user_id(page, cfg):
    base_url = str(cfg.get("lms_base_url", "https://lms.iuh.edu.vn")).rstrip("/")
    page.goto(base_url + "/", wait_until="domcontentloaded", timeout=45000)

    selectors = [
        '[data-region="usermenu"] a[href*="/user/profile.php?id="]',
        '.usermenu a[href*="/user/profile.php?id="]',
        '.logininfo a[href*="/user/profile.php?id="]',
        'a[href*="/user/profile.php?id="]'
    ]

    for selector in selectors:
        try:
            links = page.locator(selector)
            for i in range(min(links.count(), 20)):
                href = links.nth(i).get_attribute("href") or ""
                values = parse_qs(urlparse(href).query).get("id")
                if values and values[0].isdigit():
                    debug_log(cfg, f"Phat hien profile URL: {href}")
                    return values[0]
        except Exception:
            pass

    raise RuntimeError("Khong xac dinh duoc userid tu URL ho so sau khi dang nhap.")

def get_entries(page, blog_url, limit):
    page.goto(blog_url, wait_until="domcontentloaded", timeout=45000)
    if logged_out(page):
        raise RuntimeError("login_required")
    hrefs = page.locator('a[href*="entryid="]').evaluate_all("els => els.map(e => e.href).filter(Boolean)")
    out, seen = [], set()
    for href in hrefs:
        eid = entry_id(href)
        if not eid or eid in seen:
            continue
        seen.add(eid)
        out.append((eid, href))
        if len(out) >= limit:
            break
    return out

def first_text(page, selectors):
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                text = loc.first.inner_text(timeout=3000).strip()
                if text:
                    return text
        except Exception:
            pass
    return ""

def extract_entry_texts(page):
    title = first_text(page, [
        ".blog_entry .subject",
        ".blog-entry .subject",
        '[data-region="blog-post"] .subject',
        ".page-header-headings h1",
        "article h1",
        "article h2",
        "h1",
    ])
    content = first_text(page, [
        ".blog_entry .content",
        ".blog-entry .content",
        ".blog_entry .no-overflow",
        ".blog-entry .no-overflow",
        '[data-region="blog-post"] .content',
        "article .content",
        "article .no-overflow",
        "#region-main .blog_entry",
        "#region-main article",
        "#region-main",
    ])
    return title, content

def match_command(page, cfg):
    title, content = extract_entry_texts(page)

    detect_pattern = str(cfg.get("detect_pattern", "#bot")).strip()
    if not detect_pattern:
        return None

    default_system_prompt = str(cfg.get("default_system_prompt", "")).strip()
    commands = cfg.get("commands", {})
    if not isinstance(commands, dict):
        commands = {}

    position = str(cfg.get("trigger_position", "content")).strip().lower()
    if position not in ("content", "title", "both"):
        position = "content"

    sources = []
    if position in ("content", "both"):
        sources.append(("content", content))
    if position in ("title", "both"):
        sources.append(("title", title))

    for source_name, source_text in sources:
        detect_pos = source_text.find(detect_pattern)
        if detect_pos < 0:
            continue

        if source_name == "content":
            prompt = source_text[detect_pos + len(detect_pattern):].strip()
        else:
            title_after = source_text[detect_pos + len(detect_pattern):].strip()
            prompt = (title_after + "\n" + content).strip()

        selected_command = None
        selected_system_prompt = default_system_prompt

        for tag in sorted(commands.keys(), key=len, reverse=True):
            tag = str(tag)
            if not tag:
                continue
            tag_pos = prompt.find(tag)
            if tag_pos < 0:
                continue
            command_cfg = commands.get(tag) or {}
            selected_command = tag
            selected_system_prompt = str(command_cfg.get("system_prompt", "")).strip() or default_system_prompt
            prompt = (prompt[:tag_pos] + prompt[tag_pos + len(tag):]).strip()
            break

        return detect_pattern, selected_command, selected_system_prompt, prompt

    return None

def call_groq(prompt, system_prompt, cfg):
    api_key = str(cfg.get("groq_api_key", "")).strip()
    if not api_key:
        raise RuntimeError("Thieu groq_api_key trong config.json")

    model = str(cfg.get("ai_model", "")).strip() or "openai/gpt-oss-120b"
    max_chars = max(100, int(cfg.get("max_answer_length", 6000)))
    max_tokens = max(128, min(4096, max_chars // 2 + 128))

    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=90.0)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt or "Tra loi dung trong tam va ro rang."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_completion_tokens=max_tokens,
            reasoning_effort="low",
            include_reasoning=False
        )
    except Exception as exc:
        raise RuntimeError(f"Groq SDK error: {type(exc).__name__}: {exc}") from exc

    answer = str(response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Groq tra ve noi dung rong")
    return answer[:max_chars]

def call_ai(prompt, system_prompt, cfg):
    provider = str(cfg.get("provider", "groq")).strip().lower() or "groq"
    retries = max(0, int(cfg.get("retry_count", 2)))
    retry_delay = max(0.0, float(cfg.get("retry_delay_seconds", 2)))
    last_error = None

    for attempt in range(retries + 1):
        try:
            if provider == "groq":
                return call_groq(prompt, system_prompt, cfg)
            raise RuntimeError(f"Provider chua duoc ho tro: {provider}")
        except Exception as exc:
            last_error = exc
            debug_log(cfg, f"AI attempt {attempt + 1} loi: {type(exc).__name__}: {exc}")
            if attempt < retries and retry_delay > 0:
                time.sleep(retry_delay)

    raise RuntimeError(str(last_error))

def post_comment(page, reply):
    textarea = page.locator('textarea[name="content"], textarea[id^="dlg-content-"]').last
    if not textarea.is_visible():
        toggles = page.locator("a.comment-link")
        if toggles.count() > 0:
            try:
                toggles.last.click(timeout=5000)
            except Exception:
                pass
    try:
        textarea.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError:
        return False, "Khong tim thay o binh luan."
    textarea.fill(reply)
    save_btn = page.locator('a[id^="comment-action-post-"]').last
    if save_btn.count() == 0:
        return False, "Khong tim thay nut luu binh luan."
    save_btn.click(timeout=10000)
    page.wait_for_timeout(1500)
    return True, "Da gui binh luan."

def process_entry(page, eid, url, cfg):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    if logged_out(page):
        raise RuntimeError("login_required")
    matched = match_command(page, cfg)
    if not matched:
        return False

    detect_pattern, command_tag, system_prompt, prompt = matched
    if not prompt:
        log(f"Entry {eid}: co mau kich hoat {detect_pattern!r} nhung khong co noi dung cau hoi.")
        return False

    mode = command_tag if command_tag else "default"
    log(f"Phat hien {detect_pattern!r} o entry {eid}; mode={mode}. Dang goi AI...")
    answer = call_ai(prompt, system_prompt, cfg)
    log(f"Entry {eid}: AI tra loi {len(answer)} ky tu. Dang gui binh luan...")

    ok, detail = post_comment(page, answer)
    log(f"Entry {eid}: {detail}")
    return ok

def main():
    cfg = load_config()
    processed = load_processed()
    base_url = str(cfg["lms_base_url"]).rstrip("/")
    commands = cfg.get("commands", {})
    only_new = bool(cfg.get("only_new_posts", False))
    interval = max(2, int(cfg.get("poll_interval_seconds", 5)))
    limit = max(1, int(cfg.get("max_posts_per_scan", 10)))
    cooldown = max(0.0, float(cfg.get("cooldown_seconds", 0)))
    provider = str(cfg.get("provider", "groq") or "groq")
    model = str(cfg.get("ai_model", "")).strip() or "openai/gpt-oss-120b"
    log("=== IUH LMS BLOG BOT ===")
    names = ", ".join(commands.keys()) if isinstance(commands, dict) else "(none)"
    detect_pattern = str(cfg.get("detect_pattern", "#bot"))
    log(f"Mau kich hoat: {detect_pattern!r}; scan moi {interval}s")
    log(f"Lenh phu: {names}")
    log(f"AI provider: {provider}; model: {model}")
    with sync_playwright() as pw:
        context = launch_browser(pw, bool(cfg.get("headless", False)))
        page = context.pages[0] if context.pages else context.new_page()
        try:
            ensure_login(page, cfg)
            user_id = discover_user_id(page, cfg)
            blog_url = f"{base_url}/blog/index.php?userid={user_id}"
            log("Da xac dinh blog cua tai khoan dang nhap.")

            if only_new:
                initial = get_entries(page, blog_url, limit)
                for eid, _ in initial:
                    processed.add(eid)
                save_processed(processed)
                log(f"only_new_posts=true: bo qua {len(initial)} bai hien co.")

            while True:
                try:
                    entries = get_entries(page, blog_url, limit)
                    for eid, url in entries:
                        if eid in processed:
                            continue
                        if process_entry(page, eid, url, cfg):
                            processed.add(eid)
                            save_processed(processed)
                            if cooldown > 0:
                                time.sleep(cooldown)
                    time.sleep(interval)
                except RuntimeError as exc:
                    if str(exc) == "login_required":
                        ensure_login(page, cfg)
                        user_id = discover_user_id(page, cfg)
                        blog_url = f"{base_url}/blog/index.php?userid={user_id}"
                    else:
                        log(f"Loi: {exc}")
                        time.sleep(interval)
                except Exception as exc:
                    log(f"Loi tam thoi: {type(exc).__name__}: {exc}")
                    time.sleep(interval)
        except KeyboardInterrupt:
            log("Da dung bot.")
        finally:
            context.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
