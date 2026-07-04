import argparse
import json
import logging
import os
import sys

from meeting import Meeting
from summarizer import summarize
from poster import format_post, run_post, is_already_posted


logger = logging.getLogger("fbpost")


def load_config(config_path: str) -> dict:
    logger.debug(f"Loading config from: {config_path}")
    with open(config_path, "r") as f:
        return json.load(f)


def list_meetings(config: dict):
    meetings = Meeting.list_meetings(config["archive_dir"])
    if not meetings:
        print("No meetings found in archive.")
        return

    print(f"{'ID':<12} {'Date':<12} {'Title'}")
    print("-" * 100)
    for m in meetings:
        print(f"{m['id']:<12} {m['date']:<12} {m['title']}")
    print(f"\nTotal: {len(meetings)} meetings")


def process_meeting(meeting_id: str, config: dict, auto: bool, dry_run: bool, force: bool):
    logger.info(f"Loading meeting {meeting_id} from: {config['archive_dir']}")
    meeting = Meeting.from_id(meeting_id, config["archive_dir"])

    print(f"Meeting: {meeting.title}")
    print(f"Body:    {meeting.body_name}")
    print(f"Date:    {meeting.date}")
    print()

    if not force and is_already_posted(config["posted_log"], meeting_id):
        logger.info(f"Meeting {meeting_id} already in posted log. Use --force to reprocess.")
        print(f"[SKIP] Meeting {meeting_id} already in posted log. Use --force to reprocess.")
        return

    if dry_run:
        print("=" * 60)
        print("  DRY RUN MODE — NO POST WILL BE MADE")
        print("=" * 60)
        print()

    logger.info("Generating LLM summary...")
    print("Generating summary... (this may take a moment)")
    summary = summarize(meeting, config)
    logger.info("LLM summary complete.")

    logger.info("Formatting post message...")
    message = format_post(summary, meeting, config)

    if dry_run:
        print("\n=== DRAFT POST ===")
        print(message)
        print("\n=== RAW SUMMARY JSON ===")
        print(json.dumps(summary, indent=2))
        logger.info("Dry run complete.")
        return

    if auto:
        logger.info("Auto mode: posting without review.")
        print("\n=== DRAFT POST ===")
        print(message)
        print()
        run_post(meeting_id, summary, meeting, message, config, force)
        return

    print("=== DRAFT POST ===")
    print(message)
    print("\n=== ACTIONS ===")
    print("[p]  Post to Facebook")
    print("[s]  Skip")
    print("[e]  Save draft to file and skip")
    choice = input("\nChoice: ").strip().lower()

    if choice == "p":
        run_post(meeting_id, summary, meeting, message, config, force)
    elif choice == "e":
        draft_path = f"draft_{meeting_id}.txt"
        with open(draft_path, "w") as f:
            f.write(message)
        logger.info(f"Draft saved to {draft_path}")
        print(f"Draft saved to {draft_path}")
    else:
        logger.info("User skipped post.")
        print("Skipped.")


def main():
    parser = argparse.ArgumentParser(
        description="Dentron 3000 - Denton City Meeting Summarizer"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose/debug output"
    )
    parser.add_argument(
        "--config", default="config.json",
        help="Path to config.json (default: config.json)"
    )
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list", help="List all meetings in archive")
    list_cmd.add_argument(
        "--search", type=str, default="",
        help="Filter meetings by keyword in title"
    )
    list_cmd.add_argument(
        "--body", type=str, default="",
        help="Filter by meeting body (e.g., 'City Council', 'Planning')"
    )
    list_cmd.add_argument(
        "--limit", type=int, default=50,
        help="Max number of meetings to show (default: 50)"
    )

    proc = sub.add_parser("process", help="Process a meeting by ID")
    proc.add_argument(
        "--meeting-id", type=str, required=True,
        help="Meeting ID (the number from bag-XXXXXX)"
    )
    proc.add_argument(
        "--auto", action="store_true",
        help="Auto-post without review"
    )
    proc.add_argument(
        "--dry-run", action="store_true",
        help="Generate and print summary without posting"
    )
    proc.add_argument(
        "--force", action="store_true",
        help="Reprocess even if already in posted log"
    )

    args = parser.parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silence noisy third-party loggers
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("http11").setLevel(logging.WARNING)

    config = load_config(args.config)

    if args.command == "list":
        logger.debug("Listing meetings from archive...")
        if args.search or args.body:
            meetings = Meeting.list_meeting_ids(config["archive_dir"])
        else:
            meetings = Meeting.list_meeting_ids(config["archive_dir"], limit=args.limit + 100)
        if args.search:
            kw = args.search.lower()
            meetings = [m for m in meetings if kw in m["title"].lower()]
        if args.body:
            kw = args.body.lower()
            meetings = [m for m in meetings if kw in m["title"].lower()]
        meetings = meetings[:args.limit]

        if not meetings:
            print("No meetings found matching filters.")
            return

        print(f"{'ID':<12} {'Date':<12} {'Title'}")
        print("-" * 100)
        for m in meetings:
            print(f"{m['id']:<12} {m['date']:<12} {m['title']}")
        print(f"\nShowing min({len(meetings)}, {args.limit}) of {len(meetings)} matching meetings")

    elif args.command == "process":
        process_meeting(args.meeting_id, config, args.auto, args.dry_run, args.force)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
