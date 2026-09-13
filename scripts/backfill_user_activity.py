r"""Backfill dashboard activity fields without reading message documents.

Usage (preview):
    .venv\Scripts\python scripts\backfill_user_activity.py

Usage (apply writes):
    .venv\Scripts\python scripts\backfill_user_activity.py --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv
from firebase_admin import firestore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from app.firebase import init_firebase


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write lastMessageAt, lastChatId, and lastChatTitle to users.",
    )
    args = parser.parse_args()

    init_firebase()
    db = firestore.client()
    updated = 0
    skipped = 0
    batch = db.batch()
    batch_size = 0

    for user in db.collection("users").stream():
        latest_chats = (
            user.reference.collection("chats")
            .order_by("lastMessageAt", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        latest_chat = next(iter(latest_chats), None)
        if latest_chat is None:
            skipped += 1
            continue

        chat = latest_chat.to_dict()
        last_message_at = chat.get("lastMessageAt")
        if last_message_at is None:
            skipped += 1
            continue

        update = {
            "lastMessageAt": last_message_at,
            "lastChatId": latest_chat.id,
        }
        title = chat.get("title")
        if isinstance(title, str) and title.strip():
            update["lastChatTitle"] = title

        updated += 1
        if args.apply:
            batch.set(user.reference, update, merge=True)
            batch_size += 1
            if batch_size == 450:
                batch.commit()
                batch = db.batch()
                batch_size = 0

    if args.apply and batch_size:
        batch.commit()

    action = "Updated" if args.apply else "Would update"
    print(f"{action} {updated} users; skipped {skipped} users with no chat activity.")
    if not args.apply:
        print("Preview only. Re-run with --apply to write the fields.")


if __name__ == "__main__":
    main()
