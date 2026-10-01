"""
Autonomous 15-Minute Background Refresh Daemon for Institutional Dividend Screener
Runs every 15 minutes even when the Streamlit web app is closed.
Fetches fresh market quotes, updates data/screener_cache.json and data/screener_cache.csv,
and commits/pushes to GitHub so Streamlit Cloud maintains 100% data freshness and uptime.
"""

import os
import sys
import time
import argparse
import subprocess
import datetime
from zoneinfo import ZoneInfo

from screener_engine import fetch_live_screener_universe, save_screener_cache

IST = ZoneInfo("Asia/Kolkata")
REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def git_commit_and_push(commit_msg: str):
    """
    Safely commits and pushes updated data cache to GitHub origin main.
    Avoids touching .github/workflows to prevent OAuth token scope errors.
    """
    try:
        # Check git status
        st_res = subprocess.run(
            ["git", "status", "--porcelain"], 
            cwd=REPO_DIR, 
            capture_output=True, 
            text=True
        )
        if not st_res.stdout.strip():
            print(f"[{datetime.datetime.now(IST).strftime('%H:%M:%S')}] No changes detected in working tree.")
            return True, "No changes to commit"

        # Stage data files and reboot marker
        subprocess.run(["git", "add", "data/screener_cache.json", "data/screener_cache.csv"], cwd=REPO_DIR, check=True)
        
        # Also stage .streamlit_reboot timestamp marker to keep Streamlit Cloud active
        reboot_marker = os.path.join(REPO_DIR, ".streamlit_reboot")
        with open(reboot_marker, "w", encoding="utf-8") as f:
            f.write(f"auto-sync: {datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}\n")
        subprocess.run(["git", "add", ".streamlit_reboot"], cwd=REPO_DIR, check=True)

        # Commit
        c_res = subprocess.run(
            ["git", "commit", "-m", commit_msg], 
            cwd=REPO_DIR, 
            capture_output=True, 
            text=True
        )
        if c_res.returncode != 0 and "nothing to commit" not in c_res.stdout:
            print(f"Git commit error: {c_res.stderr}")
            return False, c_res.stderr

        # Pull rebase before push to integrate any remote changes
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=REPO_DIR, capture_output=True)

        # Push to remote
        p_res = subprocess.run(
            ["git", "push", "origin", "main"], 
            cwd=REPO_DIR, 
            capture_output=True, 
            text=True
        )
        if p_res.returncode == 0:
            print(f"[{datetime.datetime.now(IST).strftime('%H:%M:%S')}] Pushed 15-min sync to origin main.")
            return True, "Pushed to origin main successfully"
        else:
            print(f"Git push failed: {p_res.stderr}")
            return False, p_res.stderr

    except Exception as e:
        print(f"Git push exception: {e}")
        return False, str(e)


def run_single_sync(push=True):
    """
    Executes one synchronization cycle.
    """
    now_ist = datetime.datetime.now(IST)
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"\n[{now_str}] Starting 15-minute screener refresh cycle...")

    t0 = time.time()
    df, status = fetch_live_screener_universe()
    elapsed = time.time() - t0

    if df.empty:
        print(f"[{now_str}] Error: Fetched DataFrame is empty. Retaining previous cache.")
        return False

    ok, msg = save_screener_cache(df, status)
    print(f"[{now_str}] Cache updated: {msg} (Elapsed: {elapsed:.2f}s, Rows: {len(df)})")

    if push:
        commit_msg = f"🔄 data: 15-min automated dividend screener sync [{now_ist.strftime('%Y-%m-%d %H:%M IST')}]"
        p_ok, p_msg = git_commit_and_push(commit_msg)
        print(f"[{now_str}] Cloud Push Status: {p_msg}")

    return True


def start_daemon_loop(interval_sec=900, push=True):
    """
    Runs continuously, executing every 15 minutes (900 seconds).
    Even when the user closes their browser, this daemon keeps the cloud data up to date.
    """
    print(f"=== Autonomous Screener Daemon Started (Interval: {interval_sec}s / 15m) ===")
    print("Press Ctrl+C to terminate.")

    while True:
        try:
            run_single_sync(push=push)
        except Exception as e:
            print(f"Error in sync cycle: {e}")

        now = datetime.datetime.now(IST).strftime("%H:%M:%S")
        print(f"[{now}] Sleeping for {interval_sec // 60} minutes until next cycle...\n")
        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dividend & REIT Screener Auto-Refresh Daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--no-push", action="store_true", help="Do not push git commits")
    parser.add_argument("--interval", type=int, default=900, help="Interval in seconds (default: 900 / 15m)")
    args = parser.parse_args()

    do_push = not args.no_push

    if args.once:
        run_single_sync(push=do_push)
    else:
        start_daemon_loop(interval_sec=args.interval, push=do_push)
