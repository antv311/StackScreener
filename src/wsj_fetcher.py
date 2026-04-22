"""
wsj_fetcher.py — Automated WSJ newspaper PDF downloader for StackScreener.

Checks Gmail for WSJ Print Edition delivery emails, extracts the wsjtodaysedition
download URL, uses an existing Chrome profile (already logged into WSJ) to trigger
the PDF download, moves it to src/News/pdfs/, then ingests it via news.py.

The Chrome profile must already be authenticated with WSJ. To set up or refresh the
session, run login.py from the original WSJbot directory.

Setup (one-time — stores Gmail app password encrypted in the DB):
    python src/wsj_fetcher.py --setup antv311@gmail.com "xxxx xxxx xxxx xxxx"

Fetch + ingest new editions:
    python src/wsj_fetcher.py --fetch

Download only (skip ingestion):
    python src/wsj_fetcher.py --fetch --no-ingest

Override Chrome profile path:
    python src/wsj_fetcher.py --fetch --profile-dir "C:\\path\\to\\chromeprofile"
"""

import argparse
import glob
import imaplib
import email
import email.utils
import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timedelta

import db
import news
from screener_config import (
    DEBUG_MODE,
    NEWS_PDF_DIR,
    PROVIDER_GMAIL_WSJ,
    WSJ_BACKFILL_LIMIT_DAYS,
    WSJ_CHROME_PROFILE_DIR,
    WSJ_CHROME_PROFILE_NAME,
    WSJ_DOWNLOAD_WAIT_SECS,
    WSJ_EMAIL_FROM,
    WSJ_EMAIL_SUBJECT,
    WSJ_GMAIL_USER_KEY,
    WSJ_LAST_POLLED_KEY,
)

# admin user_uid — credentials are always stored against user 1
_ADMIN_UID = 1


# ── Credential helpers ─────────────────────────────────────────────────────────

def setup_credentials(gmail_user: str, gmail_app_password: str) -> None:
    """Store Gmail credentials in the DB (one-time setup). App password is encrypted."""
    db.init_db()
    db.set_setting(_ADMIN_UID, WSJ_GMAIL_USER_KEY, gmail_user)
    db.set_api_key(_ADMIN_UID, PROVIDER_GMAIL_WSJ, gmail_app_password)
    print(f"  Credentials stored for {gmail_user}")


def _get_credentials() -> tuple[str, str] | None:
    """Return (gmail_user, app_password) or None if not configured."""
    gmail_user = db.get_setting(_ADMIN_UID, WSJ_GMAIL_USER_KEY)
    app_password = db.get_api_key(_ADMIN_UID, PROVIDER_GMAIL_WSJ)
    if not gmail_user or not app_password:
        print("  Gmail credentials not configured.")
        print("  Run: python src/wsj_fetcher.py --setup EMAIL APP_PASSWORD")
        return None
    return gmail_user, app_password


# ── Bookmark helpers ───────────────────────────────────────────────────────────

def _get_last_polled() -> datetime.date:
    raw = db.get_setting(_ADMIN_UID, WSJ_LAST_POLLED_KEY)
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    return (datetime.now().date() - timedelta(days=3))


def _set_last_polled(d: datetime.date) -> None:
    db.set_setting(_ADMIN_UID, WSJ_LAST_POLLED_KEY, d.strftime("%Y-%m-%d"))
    if DEBUG_MODE:
        print(f"  [wsj_fetcher] bookmark updated → {d}")


# ── Gmail task discovery ───────────────────────────────────────────────────────

def _check_gmail(gmail_user: str, app_password: str) -> list[dict]:
    """
    Scan the inbox for WSJ Print Edition emails newer than the last polled date.
    Returns a list of task dicts: {url, date, is_backfill}.
    """
    today = datetime.now().date()
    last_polled = _get_last_polled()
    print(f"  Searching for WSJ editions newer than {last_polled}...")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, app_password)
        mail.select("inbox")

        status, messages = mail.search(
            None, f'(FROM "{WSJ_EMAIL_FROM}" SUBJECT "{WSJ_EMAIL_SUBJECT}")'
        )
        if not messages[0]:
            mail.logout()
            print("  No WSJ emails found in inbox.")
            return []

        email_ids = messages[0].split()
        search_limit = WSJ_BACKFILL_LIMIT_DAYS + 3
        target_ids = email_ids[-search_limit:]

        tasks: list[dict] = []
        for eid in target_ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            if not date_tuple:
                continue
            edition_date = datetime.fromtimestamp(
                email.utils.mktime_tz(date_tuple)
            ).date()

            if not (last_polled < edition_date <= today):
                continue

            # Extract the wsjtodaysedition download URL from the email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")

            urls = re.findall(r'(https?://[^\s<>"]+)', body)
            for url in urls:
                if "wsjtodaysedition" in url and url.rstrip("/").endswith("-i"):
                    tasks.append({
                        "url":         url,
                        "date":        edition_date,
                        "is_backfill": edition_date < today,
                    })
                    break  # one URL per email

        mail.logout()
        return sorted(tasks, key=lambda t: t["date"])

    except Exception as exc:
        print(f"  Gmail check failed: {exc}")
        return []


# ── Chrome download ────────────────────────────────────────────────────────────

def _download_via_chrome(
    url: str,
    dest_dir: str,
    profile_dir: str,
    profile_name: str,
) -> str | None:
    """
    Open url in Chrome using the saved WSJ session. Chrome's PDF download preference
    causes the PDF to land in dest_dir. Returns the PDF path or None on failure.

    NOT headless — the browser window opens visibly so the saved login session is used.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    abs_dest = os.path.abspath(dest_dir)
    os.makedirs(abs_dest, exist_ok=True)

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--profile-directory={profile_name}")
    options.add_experimental_option("prefs", {
        "download.default_directory":    abs_dest,
        "download.prompt_for_download":  False,
        "plugins.always_open_pdf_externally": True,
    })

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
        driver.get(url)

        # Poll for the PDF — Chrome writes a .crdownload while downloading
        deadline = time.time() + WSJ_DOWNLOAD_WAIT_SECS + 60
        pdf_path: str | None = None
        while time.time() < deadline:
            time.sleep(2)
            if glob.glob(os.path.join(abs_dest, "*.crdownload")):
                continue  # still downloading
            pdfs = glob.glob(os.path.join(abs_dest, "*.pdf"))
            if pdfs:
                pdf_path = max(pdfs, key=os.path.getctime)
                break

        return pdf_path

    except Exception as exc:
        print(f"  Chrome download failed: {exc}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _clean_filename(raw: str) -> str:
    """Extract the WSJNewsPaper... portion and strip hyphens, matching WSJbot behaviour."""
    base = os.path.basename(raw)
    if "WSJNewsPaper" in base:
        idx = base.find("WSJNewsPaper")
        return base[idx:].replace("-", "")
    return base.replace("-", "")


# ── Main fetch orchestration ───────────────────────────────────────────────────

def fetch_new_pdfs(
    profile_dir: str = WSJ_CHROME_PROFILE_DIR,
    profile_name: str = WSJ_CHROME_PROFILE_NAME,
    ingest: bool = True,
) -> int:
    """
    Full pipeline: check Gmail → download new PDFs via Chrome → (optionally) ingest.
    Returns count of PDFs successfully downloaded.
    """
    db.init_db()
    creds = _get_credentials()
    if not creds:
        return 0
    gmail_user, app_password = creds

    tasks = _check_gmail(gmail_user, app_password)
    if not tasks:
        print("  Nothing new to download.")
        return 0

    downloaded = 0
    # Use a temp staging dir so partial downloads don't mix with already-ingested PDFs
    staging_dir = tempfile.mkdtemp(prefix="wsj_staging_")

    try:
        for task in tasks:
            label = "BACKFILL" if task["is_backfill"] else "TODAY"
            print(f"  [{label}] Downloading edition {task['date']} ...")

            raw_path = _download_via_chrome(
                task["url"], staging_dir, profile_dir, profile_name
            )
            if not raw_path:
                print(f"  No PDF found after download attempt — skipping {task['date']}")
                continue

            clean_name = _clean_filename(raw_path)
            final_path = os.path.join(os.path.abspath(NEWS_PDF_DIR), clean_name)
            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            if not os.path.exists(final_path):
                shutil.move(raw_path, final_path)
            else:
                os.unlink(raw_path)  # already have it

            print(f"  Saved: {final_path}")
            _set_last_polled(task["date"])
            downloaded += 1

            if ingest:
                news.ingest_wsj_pdf(final_path)

            time.sleep(3)  # brief pause between editions

    finally:
        # Clean up staging dir if empty
        try:
            if not os.listdir(staging_dir):
                os.rmdir(staging_dir)
        except OSError:
            pass

    return downloaded


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="WSJ newspaper PDF fetcher")
    parser.add_argument(
        "--setup", nargs=2, metavar=("EMAIL", "APP_PASSWORD"),
        help="Store Gmail app password in the encrypted DB (one-time setup)",
    )
    parser.add_argument(
        "--fetch", action="store_true",
        help="Check Gmail and download any new WSJ editions",
    )
    parser.add_argument(
        "--no-ingest", action="store_true",
        help="Download PDFs but skip ingestion into news_articles",
    )
    parser.add_argument(
        "--profile-dir", default=WSJ_CHROME_PROFILE_DIR, metavar="PATH",
        help=f"Chrome profile directory (default: {WSJ_CHROME_PROFILE_DIR})",
    )
    parser.add_argument(
        "--profile-name", default=WSJ_CHROME_PROFILE_NAME, metavar="NAME",
        help=f"Chrome profile name (default: {WSJ_CHROME_PROFILE_NAME})",
    )
    args = parser.parse_args()

    if args.setup:
        setup_credentials(args.setup[0], args.setup[1])

    if args.fetch:
        n = fetch_new_pdfs(
            profile_dir=args.profile_dir,
            profile_name=args.profile_name,
            ingest=not args.no_ingest,
        )
        print(f"  {n} edition(s) downloaded.")


if __name__ == "__main__":
    main()
