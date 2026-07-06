import json
import logging
import os
import re

from extract_agenda import extract_agenda_text


logger = logging.getLogger("fbpost")


class Meeting:
    def __init__(self, bag_dir: str):
        self.bag_dir = bag_dir
        self.metadata = {}
        self.transcript = ""
        self.agenda_text = ""
        self.id = ""
        self._load()

    def _load(self):
        logger.info(f"Loading meeting from: {self.bag_dir}")
        meta_path = os.path.join(self.bag_dir, "data", "metadata.json")
        with open(meta_path, "r") as f:
            self.metadata = json.load(f)
        self.id = self.metadata.get("id", "")
        logger.debug(f"  metadata.json loaded, meeting ID: {self.id}")

        transcript_path = os.path.join(self.bag_dir, "data", "whisper_transcript.txt")
        if os.path.exists(transcript_path):
            with open(transcript_path, "r") as f:
                self.transcript = f.read().strip()
            logger.info(f"  whisper_transcript.txt loaded: {len(self.transcript)} chars")
        else:
            logger.warning(f"  whisper_transcript.txt not found")

        agenda_path = os.path.join(self.bag_dir, "data", "agenda.pdf")
        if os.path.exists(agenda_path):
            self.agenda_text = extract_agenda_text(agenda_path)
        else:
            logger.warning(f"  agenda.pdf not found")

    @property
    def title(self) -> str:
        return self.metadata.get("title", "")

    @property
    def date(self) -> str:
        return self.metadata.get("date", "")

    @property
    def chapters(self) -> list:
        return self.metadata.get("chapters", [])

    @property
    def body_name(self) -> str:
        match = re.match(r".+?\s+(\w[\w\s\.]+?)\s+on\s+\d{4}", self.title)
        if match:
            name = match.group(1).strip()
            name = re.sub(r"^\d{4}\s*", "", name).strip()
            return name or "Unknown Body"
        return "Unknown Body"

    @property
    def source_url(self) -> str:
        return self.metadata.get("source_url", "")

    def get_agenda_summary(self) -> str:
        unique = []
        seen = set()
        for ch in self.chapters:
            t = ch["title"].strip()
            if t and t not in seen:
                seen.add(t)
                unique.append(t)
        return "\n".join(f"  - {t}" for t in unique)

    @staticmethod
    def list_meeting_ids(archive_dir: str, limit: int = 0) -> list:
        meetings = []
        for entry in os.scandir(archive_dir):
            if not entry.is_dir() or not entry.name.startswith("bag-"):
                continue
            meta_path = os.path.join(entry.path, "data", "metadata.json")
            if not os.path.exists(meta_path):
                continue
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meetings.append({
                "id": meta.get("id", ""),
                "date": meta.get("date", ""),
                "title": meta.get("title", ""),
                "bag_dir": entry.path,
            })
            if limit and len(meetings) >= limit:
                break
        return meetings

    @staticmethod
    def from_id(meeting_id: str, archive_dir: str) -> "Meeting":
        bag_dir = os.path.join(archive_dir, f"bag-{meeting_id}")
        if not os.path.isdir(bag_dir):
            raise FileNotFoundError(f"Meeting bag not found: {bag_dir}")
        return Meeting(bag_dir)
