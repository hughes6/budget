import imaplib
import email
import time
from email.header import decode_header
from email.utils import parseaddr

def simple_email_checker(email_address, app_password, check_interval=5):
    """
    Simplest possible email checker
    Just shows you what emails are in your inbox every X seconds
    """
    print(f"🚀 Starting email checker for: {email_address}")
    print(f"⏱️  Checking every {check_interval} seconds")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            print(f"\n[{time.strftime('%H:%M:%S')}] Checking...")
            
            # 1. Connect
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_address, app_password)
            mail.select("inbox")
            
            # 2. Get unread emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if messages[0]:
                email_ids = messages[0].split()
                print(f"📧 Found {len(email_ids)} new email(s)")
                
                for mail_id in email_ids:
                    # 3. Fetch email
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)
                    
                    # 4. Get basic info
                    sender_name, sender_email = parseaddr(msg.get("From", ""))
                    
                    # Get subject
                    subject_raw = decode_header(msg.get("Subject", ""))[0][0]
                    subject = subject_raw.decode() if isinstance(subject_raw, bytes) else str(subject_raw)
                    
                    # Get body preview
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    continue
                        else:
                            body = ""
                    else:
                        body = msg.get_payload(decode=True)
                        body = body.decode() if body else ""
                    
                    # 5. Show it to you
                    print(f"\n{'━'*40}")
                    print(f"From: {sender_name} <{sender_email}>")
                    print(f"Subject: {subject[:50]}{'...' if len(subject) > 50 else ''}")
                    print(f"Preview: {body[:80]}{'...' if len(body) > 80 else ''}")
                    print(f"{'━'*40}")
                    
                    # 6. Mark as read (optional - comment out if you don't want this)
                    # mail.store(mail_id, '+FLAGS', '\\Seen')
            else:
                print("📭 No new emails")
            
            # 7. Close connection
            mail.close()
            mail.logout()
            
        except imaplib.IMAP4.error as e:
            print(f"❌ LOGIN ERROR: {e}")
            print("Check your email and app password!")
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            print("Retrying in 10 seconds...")
            time.sleep(10)
            continue
        
        # 8. Wait before checking again
        print(f"⏳ Waiting {check_interval} seconds...")
        time.sleep(check_interval)

# ============ JUST PUT YOUR INFO HERE AND RUN ============
if __name__ == "__main__":
    # 👇 REPLACE THESE WITH YOUR ACTUAL INFO 👇
    YOUR_EMAIL = "conkenbudget@gmail.com"
    YOUR_APP_PASSWORD = "rhoz hnjv gfrr pgcj"  # Get from Google App Passwords
    
    # 👇 CHANGE CHECK INTERVAL IF YOU WANT (seconds) 👇
    CHECK_EVERY = 5  # seconds
    
    # Run it!
    simple_email_checker(YOUR_EMAIL, YOUR_APP_PASSWORD, CHECK_EVERY)