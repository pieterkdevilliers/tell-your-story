from app.services import email_templates


def test_render_escapes_html_but_not_plain_text():
    html, text = email_templates.render(
        "Hi <b>there</b>", ['Account "<script>alert(1)</script>"']
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" in text


def test_render_includes_cta_link_in_both_bodies():
    html, text = email_templates.render(
        "Heading", ["Body text"], cta_text="Click me", cta_link="https://example.com/x"
    )

    assert 'href="https://example.com/x"' in html
    assert "Click me" in html
    assert "https://example.com/x" in text


def test_signup_confirmation_storyteller_mentions_account_name():
    subject, html, text = email_templates.signup_confirmation_storyteller("My Family")

    assert subject
    assert "My Family" in html
    assert "My Family" in text


def test_signup_confirmation_story_requester_mentions_account_name():
    subject, html, text = email_templates.signup_confirmation_story_requester(
        "My Family"
    )

    assert subject
    assert "My Family" in html
    assert "My Family" in text


def test_invite_storyteller_includes_link_and_expiry():
    subject, html, text = email_templates.invite_storyteller(
        "My Family", "https://example.com/invite/abc", 60
    )

    assert "My Family" in subject
    assert "https://example.com/invite/abc" in html
    assert "https://example.com/invite/abc" in text
    assert "60 minutes" in text


def test_invite_viewer_includes_link_and_expiry():
    subject, html, text = email_templates.invite_viewer(
        "My Family", "https://example.com/invite/xyz", 60
    )

    assert "My Family" in subject
    assert "https://example.com/invite/xyz" in html
    assert "https://example.com/invite/xyz" in text
    assert "60 minutes" in text


def test_password_reset_includes_link_and_account_names():
    subject, html, text = email_templates.password_reset(
        "Account A, Account B", "https://example.com/reset?token=abc", 30
    )

    assert subject
    assert "Account A, Account B" in html
    assert "https://example.com/reset?token=abc" in text
    assert "30 minutes" in text
