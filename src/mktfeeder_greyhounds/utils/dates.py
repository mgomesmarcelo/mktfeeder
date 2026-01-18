from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def hhmm_to_today_iso(hhmm: str) -> str:
    """Converte 'HH:MM' para ISO hoje."""
    try:
        hour, minute = [int(x) for x in hhmm.strip()[:5].split(":")]
        now = datetime.now()
        dt = datetime(now.year, now.month, now.day, hour, minute)
        return dt.isoformat(timespec="minutes")
    except Exception:
        return datetime.now().isoformat(timespec="minutes")


def iso_to_hhmm(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except Exception:
        return ""


__all__ = ["utc_now_iso", "today_str", "hhmm_to_today_iso", "iso_to_hhmm"]

