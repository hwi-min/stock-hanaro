from datetime import datetime, time
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def domestic_market_code(now: datetime | None = None) -> str:
    """Use NXT only while one of its three continuous sessions is trading."""
    current = (now or datetime.now(KST)).astimezone(KST)
    if current.weekday() >= 5:
        return "J"
    clock = current.time()
    if (
        time(8, 0) <= clock < time(8, 50)
        or time(9, 0, 30) <= clock < time(15, 20)
        or time(15, 40) <= clock < time(20, 0)
    ):
        return "NX"
    return "J"


def domestic_quote_ttl(now: datetime | None = None, *, surface: str = "detail") -> int:
    current = (now or datetime.now(KST)).astimezone(KST)
    if current.weekday() >= 5:
        return 12 * 60 * 60

    clock = current.time()
    if time(8, 0) <= clock < time(8, 50):
        return 30
    if time(8, 50) <= clock < time(9, 0):
        return 60
    if time(9, 0) <= clock < time(15, 30):
        return 10 if surface == "detail" else 30
    if time(15, 30) <= clock < time(15, 40):
        return 30
    if time(15, 40) <= clock < time(20, 0):
        return 30 if surface == "detail" else 60
    return 12 * 60 * 60


def domestic_chart_ttl(now: datetime | None = None) -> int:
    current = (now or datetime.now(KST)).astimezone(KST)
    return 5 * 60 if current.weekday() < 5 and time(8, 0) <= current.time() < time(20, 0) else 12 * 60 * 60
