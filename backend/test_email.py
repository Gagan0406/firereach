#!/usr/bin/env python3
"""
FireReach – Email Testing Script
Tests SendGrid configuration independently from the agent pipeline.
Run: python test_email.py
"""
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

def test_sendgrid_config():
    """Test 1: Check if SendGrid keys are configured."""
    print("=" * 60)
    print("TEST 1: SendGrid Configuration")
    print("=" * 60)

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")
    from_name = os.getenv("SENDGRID_FROM_NAME")

    if not api_key:
        print("❌ SENDGRID_API_KEY not found in .env")
        return False
    else:
        print(f"✅ SENDGRID_API_KEY found: {api_key[:10]}...")

    if not from_email:
        print("❌ SENDGRID_FROM_EMAIL not found in .env")
        return False
    else:
        print(f"✅ SENDGRID_FROM_EMAIL: {from_email}")

    if not from_name:
        print("❌ SENDGRID_FROM_NAME not found in .env")
        return False
    else:
        print(f"✅ SENDGRID_FROM_NAME: {from_name}")

    return True


def test_sendgrid_library():
    """Test 2: Check if sendgrid library is installed."""
    print("\n" + "=" * 60)
    print("TEST 2: SendGrid Library Installation")
    print("=" * 60)

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        print("✅ sendgrid library is installed")
        print(f"✅ sendgrid version: {sendgrid.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import sendgrid: {e}")
        print("   Run: pip install sendgrid")
        return False


def test_sendgrid_connection():
    """Test 3: Test actual SendGrid API connection."""
    print("\n" + "=" * 60)
    print("TEST 3: SendGrid API Connection")
    print("=" * 60)

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content

        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            print("❌ SENDGRID_API_KEY not configured")
            return False

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        print("✅ SendGridAPIClient initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize SendGrid: {e}")
        return False


def test_send_email():
    """Test 4: Send a test email."""
    print("\n" + "=" * 60)
    print("TEST 4: Send Test Email")
    print("=" * 60)

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content

        api_key = os.getenv("SENDGRID_API_KEY")
        from_email = os.getenv("SENDGRID_FROM_EMAIL")
        from_name = os.getenv("SENDGRID_FROM_NAME")

        if not all([api_key, from_email, from_name]):
            print("❌ Missing SendGrid configuration")
            return False

        # Test email - send to yourself or test recipient
        test_to_email = from_email  # Send to yourself for testing

        print(f"Preparing to send test email...")
        print(f"  From: {from_name} <{from_email}>")
        print(f"  To:   {test_to_email}")

        sg = sendgrid.SendGridAPIClient(api_key=api_key)

        message = Mail(
            from_email=Email(from_email, from_name),
            to_emails=To(test_to_email),
            subject="🔥 FireReach Test Email",
            plain_text_content=Content(
                "text/plain",
                "This is a test email from FireReach.\n\n"
                "If you received this, SendGrid is working correctly! ✅"
            ),
            html_content=Content(
                "text/html",
                "<h2>🔥 FireReach Test Email</h2>"
                "<p>This is a test email from FireReach.</p>"
                "<p style='color: green;'><strong>If you received this, SendGrid is working correctly! ✅</strong></p>"
            ),
        )

        response = sg.client.mail.send.post(request_body=message.get())

        status_code = response.status_code
        print(f"\nSendGrid Response:")
        print(f"  Status Code: {status_code}")

        if status_code in (200, 201, 202):
            message_id = response.headers.get("X-Message-Id", "N/A")
            print(f"  Message ID: {message_id}")
            print(f"\n✅ Email sent successfully!")
            print(f"   Check your inbox at {test_to_email}")
            return True
        else:
            print(f"❌ Failed to send email. Status: {status_code}")
            print(f"   Response headers: {response.headers}")
            print(f"   Response body: {response.body}")
            return False

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n🔥 FireReach Email Testing Suite\n")

    results = {
        "Configuration": test_sendgrid_config(),
        "Library": test_sendgrid_library(),
        "Connection": test_sendgrid_connection(),
        "Send Email": test_send_email(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed! SendGrid is configured correctly.")
        print("\nThe email sending issue is likely in the agent pipeline.")
        print("Check:")
        print("  1. Agent status is reaching 'sending' stage")
        print("  2. Email content is being generated properly")
        print("  3. Check backend logs for errors")
    else:
        print("\n⚠️  Some tests failed. Fix SendGrid configuration.")
        print("\nSteps to fix:")
        print("  1. Verify SENDGRID_API_KEY is valid at https://app.sendgrid.com/settings/api_keys")
        print("  2. Verify SENDGRID_FROM_EMAIL is a verified sender")
        print("  3. Check .env file has correct values")
        print("  4. Restart your backend server")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
