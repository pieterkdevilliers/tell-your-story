import html as html_lib
from typing import Optional

APP_NAME = "Tell Your Story"

# Everything below this line is the one place to edit email content —
# both the shared visual design (_LAYOUT/_PARAGRAPH/_CTA) and the copy
# for each individual email (the functions at the bottom). render()
# builds the HTML and plain-text bodies from the same input strings so
# the two can't drift out of sync with each other.

_LAYOUT = """\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;">
            <tr>
              <td style="background-color:#111827;padding:20px 32px;">
                <span style="color:#ffffff;font-size:18px;font-weight:600;">{app_name}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h1 style="margin:0 0 16px;font-size:20px;color:#111827;">{heading}</h1>
                {body_html}
                {cta_html}
              </td>
            </tr>
            <tr>
              <td style="padding:20px 32px;border-top:1px solid #e5e7eb;">
                <span style="font-size:12px;color:#9ca3af;">You're receiving this email because of activity on your {app_name} account.</span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

_PARAGRAPH = (
    '<p style="margin:0 0 16px;font-size:15px;line-height:1.5;color:#374151;">'
    "{text}</p>"
)

_CTA = """\
<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:8px;">
  <tr>
    <td style="border-radius:6px;background-color:#111827;">
      <a href="{link}" style="display:inline-block;padding:12px 24px;font-size:14px;color:#ffffff;text-decoration:none;font-weight:600;">{text}</a>
    </td>
  </tr>
</table>
"""


def render(
    heading: str,
    paragraphs: list[str],
    cta_text: Optional[str] = None,
    cta_link: Optional[str] = None,
) -> tuple[str, str]:
    """Builds (html, text) bodies for an email from the same content."""
    body_html = "\n".join(
        _PARAGRAPH.format(text=html_lib.escape(p)) for p in paragraphs
    )
    cta_html = ""
    if cta_link:
        cta_html = _CTA.format(
            link=html_lib.escape(cta_link), text=html_lib.escape(cta_text or "")
        )
    html = _LAYOUT.format(
        app_name=APP_NAME,
        heading=html_lib.escape(heading),
        body_html=body_html,
        cta_html=cta_html,
    )

    text_parts = [heading, "", *paragraphs]
    if cta_link:
        text_parts += ["", f"{cta_text}: {cta_link}"]
    text = "\n".join(text_parts)

    return html, text


def signup_confirmation_storyteller(account_name: str) -> tuple[str, str, str]:
    subject = f"Welcome to {APP_NAME}"
    heading = "Your account is ready"
    paragraphs = [
        f'Welcome to {APP_NAME}! You\'ve created "{account_name}" to tell your '
        "own story.",
        "Head to your questions whenever you're ready to start answering — in "
        "text, audio, or video, at your own pace — and generate a memoir from "
        "your answers whenever you feel ready.",
    ]
    html, text = render(heading, paragraphs)
    return subject, html, text


def signup_confirmation_story_requester(account_name: str) -> tuple[str, str, str]:
    subject = f"Welcome to {APP_NAME}"
    heading = "Your account is ready"
    paragraphs = [
        f'Welcome to {APP_NAME}! You\'ve created "{account_name}" to collect '
        "someone else's story.",
        "Next, invite the storyteller whose story you'd like to capture. "
        "They'll get their own questions to answer in their own words, and "
        "you'll be able to generate a memoir from their answers once they're "
        "ready.",
    ]
    html, text = render(heading, paragraphs)
    return subject, html, text


def invite_storyteller(
    account_name: str, invite_link: str, expires_minutes: int
) -> tuple[str, str, str]:
    subject = f"You're invited to join {account_name}"
    heading = f"Tell your story on {APP_NAME}"
    paragraphs = [
        f'You\'ve been invited to join "{account_name}" on {APP_NAME} as the '
        "storyteller.",
        "Accept your invite below to set a password and start answering "
        "questions in your own words — by text, audio, or video.",
        f"This link expires in {expires_minutes} minutes.",
    ]
    html, text = render(
        heading, paragraphs, cta_text="Accept invite", cta_link=invite_link
    )
    return subject, html, text


def invite_viewer(
    account_name: str, invite_link: str, expires_minutes: int
) -> tuple[str, str, str]:
    subject = f"You're invited to join {account_name}"
    heading = f"You've been invited to {account_name}"
    paragraphs = [
        f'You\'ve been invited to join "{account_name}" on {APP_NAME} as a viewer.',
        "Accept your invite below to set a password. You'll be able to read "
        "the memoir once it's ready.",
        f"This link expires in {expires_minutes} minutes.",
    ]
    html, text = render(
        heading, paragraphs, cta_text="Accept invite", cta_link=invite_link
    )
    return subject, html, text


def password_reset(
    account_names: str, reset_link: str, expires_minutes: int
) -> tuple[str, str, str]:
    subject = "Reset your password"
    heading = "Reset your password"
    paragraphs = [
        "We received a request to reset your password.",
        f"This will reset your password for: {account_names}.",
        f"This link expires in {expires_minutes} minutes. If you didn't "
        "request this, you can safely ignore this email.",
    ]
    html, text = render(
        heading, paragraphs, cta_text="Reset password", cta_link=reset_link
    )
    return subject, html, text
