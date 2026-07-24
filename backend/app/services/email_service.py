from typing import Optional

import boto3
from starlette.concurrency import run_in_threadpool

from app.core.config import AWS_REGION, SES_FROM_EMAIL


def _send_via_ses(
    to_email: str, subject: str, body: str, html_body: Optional[str]
) -> None:
    kwargs = {"region_name": AWS_REGION} if AWS_REGION else {}
    client = boto3.client("ses", **kwargs)
    message_body = {"Text": {"Data": body}}
    if html_body:
        message_body["Html"] = {"Data": html_body}
    client.send_email(
        Source=SES_FROM_EMAIL,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": message_body,
        },
    )


async def send_email(
    to_email: str, subject: str, body: str, html_body: Optional[str] = None
) -> None:
    if not SES_FROM_EMAIL:
        # print(), not logging — guaranteed to show up in console/container
        # logs regardless of logging configuration, which matters since this
        # is the only way to grab a reset link without real SES credentials.
        print(
            f"SES_FROM_EMAIL not configured; printing email instead of "
            f"sending.\nTo: {to_email}\nSubject: {subject}\n\n{body}\n"
        )
        return

    await run_in_threadpool(_send_via_ses, to_email, subject, body, html_body)
