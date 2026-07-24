"""One-off script to confirm SES is wired up correctly.

Usage:
    uv run python scripts/send_test_email.py --to you@example.com
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.email_service import send_email


async def main(to_email: str) -> None:
    await send_email(
        to_email=to_email,
        subject="Tell Your Story — SES test email",
        body="If you're reading this, SES is wired up correctly.",
    )
    print(f"Done. If SES_FROM_EMAIL is set, check {to_email}'s inbox.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, dest="to_email")
    args = parser.parse_args()
    asyncio.run(main(args.to_email))
