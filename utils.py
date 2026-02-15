import ssl
import smtplib
import imaplib
import email
import schedule
import time
import logging
import re
import pytz
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from sqlalchemy import text
from excel import BudgetExcelParser
from models import BudgetItem, Expense
from database import SessionLocal

def sendEmail(receiver_email: str, subject, body: str):
    app_password = 'rhoz hnjv gfrr pgcj'
    sender_email = 'conkenbudget@gmail.com'
    context = ssl.create_default_context()

    # print('send email function \n')
    # print('getting sent from', sender_email)
    # print('getting sent to', receiver_email)
    # print('subject', subject)
    # print('body \n',body)

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())      
        print("Email sent successfully!")
    
    except Exception as e:
        print(f"Error: {e}")

def check_emails():
    # Connect to IMAP server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login("conkenbudget@gmail.com", "rhoz hnjv gfrr pgcj")
    mail.select("inbox")
    
    # Search for unread emails
    status, messages = mail.search(None, 'UNSEEN')
    
    for mail_id in messages[0].split():
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        email_body = msg_data[0][1]
        msg = email.message_from_bytes(email_body)
        sender = get_sender_info(msg)

        subject = get_safe_subject(msg)
        
        # Get email body
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        
        # Process for your budget API
        process_budget_email(subject, body, sender)

def get_safe_subject(msg):
    """Safely extract subject from email, handles missing subjects"""
    try:
        subject_header = msg.get("Subject", "")
        if not subject_header:
            return "No Subject"
        
        decoded = decode_header(subject_header)
        if decoded and decoded[0][0]:
            subject = decoded[0][0]
            if isinstance(subject, bytes):
                return subject.decode()
            return str(subject)
        return "No Subject"
    except Exception as e:
        print(f"Error parsing subject: {e}")
        return "Error Getting Subject"
    
def get_sender_info(msg):
    """Extract sender information from email headers"""
    # Method 1: Get raw sender header
    raw_sender = msg.get("From", "")
    
    # Method 2: Parse name and email separately
    sender_name, sender_email = parseaddr(raw_sender)
    
    # Method 3: Get all sender-related headers
    sender_info = {
        "from": raw_sender,  # Raw "From" header
        "name": sender_name,  # Parsed sender name
        "email": sender_email,  # Parsed sender email
        "reply_to": msg.get("Reply-To", ""),  # Reply-To address
        "return_path": msg.get("Return-Path", ""),  # Return path
        "sender": msg.get("Sender", ""),  # Sender header (different from From)
        "to": msg.get("To", ""),  # Recipient
        "cc": msg.get("Cc", ""),  # CC recipients
        "date": msg.get("Date", ""),  # Email date
        "message_id": msg.get("Message-ID", ""),  # Unique message ID
    }
    
    return sender_info

def background_email_checker():
    """Run email checks in background"""
    print('checking emails every 5 seconds')
    schedule.every(5).seconds.do(check_emails)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def process_budget_email(subject, body, sender):
  db = SessionLocal()
#   print("sender",sender,"subject",subject,"body",body)
  asked = False
  expense = False
  for i in subject:
    if i == '?':
      asked = True  
    if i == '#':
      expense = True   
  for i in body:
    if i == '?':
      asked = True
    if i == '#':
      expense = True

  if asked == True:
    send_catalog(sender,db)
  elif expense == True:
    send_expense(sender,db)
  else:
    category,amount = extract_spending(body, db)
    if category == None or amount == None:
      no_info_body = """No category or amount detected in your email.

        Make sure your email includes:
        1. An amount (like $15.50 or 15.50)
        2. What it was for (groceries, gas, etc.)

        Examples:
        - "groceries 45.30"
        - "Gas $35"
        - "Chipotle $12.99"

        for insurance items put as follows:
        rav 4
        corolla
        triumph
        ninja 400
        renters

        for envelope kensey school put
        kensey classes
        for envelope costco membership put
        costco

        for education kensey debt put
        kensey debt
        Reply with '?' to see all budget categories."""
      no_info_subject = "Error"
      sendEmail(extract_sender(sender),no_info_subject,no_info_body)
    else:
      expense = save_expense_if_valid(category,amount,db,description=body[:100])
      if expense:
        print('subjcet', subject)
        # print('yay here is  amount: ', amount, '\nhere is category: ',category)
        if str(subject) == 'NEGATIVE':
          print('subject is negative')
          success, new_amount, old_amount = adjust_database(category, -amount, db)
        else:
          success, new_amount, old_amount = adjust_database(category, amount, db)
        if success:
          print('database adjusted, sending confirmation email')
          success_subject = "✅ EXPENSE RECORDED SUCCESSFULLY"
          success_body = f"""✅ EXPENSE RECORDED SUCCESSFULLY

          Amount: ${amount:.2f}
          Category: {category}
          Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

          📊 BUDGET UPDATE:
          Previous: ${old_amount:.2f}
          Spent: -${amount:.2f}
          Remaining: ${new_amount:.2f}\n💡 You have ${new_amount:.2f} left for {category} this period.

          Reply with '?' to see your full budget catalog. """
          sendEmail(extract_sender(sender),success_subject,success_body)

  db.close()

def send_expense(sender, db:Session):
    print('Sending Expense Report')
    expense_items = db.query(Expense).all()
    subject = 'Expense Report'
    description = ""
    i = 0
    for item in expense_items:
        i += 1
        description += f"Expense {i}: {(item.description)[:-2]} at {item.date} in category {item.category} of amount {item.amount}\n"
    sendEmail(extract_sender(sender),subject,description)

def adjust_database(category, amount, db:Session):
    budget_item = db.query(BudgetItem).filter(
        BudgetItem.bucket == category
    ).first()
    
    if budget_item:
        old_amount = budget_item.amount
        new_amount = max(0,old_amount-amount)
        budget_item.amount = max(0, budget_item.amount - amount)
        budget_item.updated_at = datetime.now()
        
        try:
            db.commit()
            print(f"✅ Budget updated: {category} now has ${budget_item.amount:.2f}")
            return True, new_amount, old_amount
        except:
            db.rollback()
            return False
    else:
        print(f"⚠️ No budget item named '{category}'")
        return False


def extract_spending(body: str, db:Session):
    if not body:
        return None, None
    body = body.strip().lower()
    amount_patterns = [
        r'\$(\d+\.?\d*)',          # $15.50
        r'(\d+\.?\d*)\s*dollars',  # 15.50 dollars
        r'(\d+\.?\d*)\s*usd',      # 15.50 usd
        r'(\d+\.?\d*)\s*bucks',    # 15.50 bucks
        r'spent\s*(\d+\.?\d*)',    # spent 15.50
        r'cost\s*(\d+\.?\d*)',     # cost 15.50
        r'paid\s*(\d+\.?\d*)',     # paid 15.50
        r'(\d+\.?\d*)\s*on',       # 15.50 on
        r'\$(\d+\.?\d*)',           # $15.50 or $15
        r'\$(\d+)[^\d.]',           # $14 (with non-digit after)
        r'\b(\d+)\b(?!\d*\.\d)',    # 14 (but not 14.50)
    ]
    amount = None
    for pattern in amount_patterns:
        matches = re.findall(pattern, body)
        if matches:
            try:
                amount = float(matches[0])
                break
            except ValueError:
                continue
    
    if amount is None:
        # Try to find any number that looks like money
        money_matches = re.findall(r'(\d+\.\d{2})', body)
        if money_matches:
            try:
                amount = float(money_matches[0])
            except ValueError:
                pass
    
    # Find category - look for budget bucket names
    category = find_category_in_body(body, db)
    
    if category is None:
        # Try to extract category from common patterns
        category = extract_category_from_patterns(body, db)
    
    return category, amount

def find_category_in_body(body: str, db: Session):
    """
    Check if any budget bucket name appears in the email body.
    """
    # Get all budget categories from database
    print('body',body)
    budget_items = db.query(BudgetItem).all()
    
    # Score each category based on match
    best_match = None
    best_score = 0
    
    for item in budget_items:
        # Clean category name for matching
        category_name = item.bucket.lower()
        
        # Remove prefixes for better matching
        clean_name = category_name
        prefixes = ['main - ', 'envelope - ', 'subscription - ', 'insurance - ', 'investment - ', 'education - ']
        for prefix in prefixes:
            if clean_name.startswith(prefix):
                clean_name = clean_name.replace(prefix, '')
                break
        
        # Check for exact match or partial match
        if clean_name in body:
            score = len(clean_name)  # Longer matches are better
            if score > best_score:
                best_score = score
                best_match = item.bucket
        
        # Also check for keywords within the category
        elif any(keyword in body for keyword in clean_name.split() if len(keyword) > 3):
            score = 1
            if score > best_score:
                best_score = score
                best_match = item.bucket
    
    return best_match

def extract_category_from_patterns(body: str, db: Session):
    """
    Try to guess category from common patterns.
    """
    # Common expense keywords mapping to budget categories
    category_keywords = {
        # Groceries
        'groceries': 'Groceries',
        'grocery': 'Groceries',
        'supermarket': 'Groceries',
        'kroger': 'Groceries',
        'king soopers': 'Groceries',
        'trader joes': 'Groceries',
        'walmart': 'Groceries',
        'target': 'Groceries',
        'aldi': 'Groceries',
        'target': 'Groceries',
        'costco': 'Envelope - Costco Membership',
        'kensey debt' : 'Kensey School Debt',
        'kensey school debt': 'Kensey School Debt',
        
        # Gas
        'gas': 'Gas',
        'gasoline': 'Gas',
        'exxon': 'Gas',
        'shell': 'Gas',
        'chevron': 'Gas',
        
        # Dining
        'restaurant': 'chipolte',  # or create a Dining category
        'dinner': 'chipolte',
        'lunch': 'chipolte',
        'breakfast': 'chipolte',
        'cafe': 'chipolte',
        'starbucks': 'chipolte',
        'mcdonald': 'chipolte',
        'chipotle': 'chipolte',
        
        # Shopping
        'amazon': 'Shopping',
        'purchase': 'Shopping',
        'buy': 'Shopping',
        'order': 'Shopping',
        
        # Subscriptions
        'netflix': 'Subscription - Netflix',
        'spotify': 'Subscription - Spotify',
        'gym': 'Subscription - Gym',
        'wifi': 'Subscription - Wifi',
        'train': 'Subscription - Train',
        'oura': 'Subscription - Oura rings',
        'apple': 'Subscription - Apple',
        
        # Utilities
        'electric': 'Subscription - Utilities',
        'water': 'Subscription - Utilities',
        'utility': 'Subscription - Utilities',
        
        # Insurance
        'insurance': 'Insurance',
        'geico': 'Insurance',
        'statefarm': 'Insurance',
        
    }
    
    # Check for keywords
    for keyword, category in category_keywords.items():
        if keyword in body:
            return category
    
    return None

def save_expense_if_valid(category: str, amount: float, db: Session, description: str = ""):
    """
    Save the expense to database if both category and amount are valid.
    """
    if category and amount and amount > 0:
        try:
            expense = Expense(
                date=datetime.now().date(),
                amount=amount,
                category=category,
                description=description[:200],  # Truncate if too long
                source='email'
            )
            db.add(expense)
            db.commit()
            return expense
        except Exception as e:
            db.rollback()
            print(f"Error saving expense: {e}")
            return None
    return None

def send_catalog(sender, db: Session):
    print('sending catalog to', sender)
    
    budget_items = db.query(BudgetItem).all()
    
    # Group by category type
    main_items = []
    envelope_items = []
    sub_items = []
    insurance_items = []
    investment_items = []
    other_items = []
    
    # Track which items we've already added to avoid duplicates
    processed_buckets = set()
    
    for item in budget_items:
        # Skip if we've already processed this bucket
        if item.bucket in processed_buckets:
            continue
            
        bucket_lower = item.bucket.lower()
        processed_buckets.add(item.bucket)
        
        # Skip totals that cause double counting
        if any(total in bucket_lower for total in ['subscriptions', 'stocks']):
            continue
        
        if bucket_lower.startswith("envelope"):
            clean_name = item.bucket.replace("Envelope - ", "")
            
            if "costco" in clean_name.lower():
                envelope_items.append(item)
            elif "kensey classes" in clean_name.lower():
                # Rename to "Kensey School" for clarity
                item.display_name = "Kensey School"
                envelope_items.append(item)
            else:
                envelope_items.append(item)
                
        elif bucket_lower.startswith("subscription"):
            clean_name = item.bucket.replace("Subscription - ", "")
            
            if "utilities" in clean_name.lower():
                # Add to main with cleaned name
                item.display_name = "Utilities"
                main_items.append(item)
            elif "wifi" in clean_name.lower() or "gym" in clean_name.lower():
                sub_items.append(item)
            elif "costco" in clean_name.lower():
                envelope_items.append(item)
            else:
                if 'insurance'  not in bucket_lower:
                    sub_items.append(item)
                
        elif bucket_lower.startswith("insurance"):
            insurance_items.append(item)
                
        elif bucket_lower.startswith("investment"):
            investment_items.append(item)
                
        elif bucket_lower.startswith("main - "):
            main_items.append(item)
            
        elif any(x in bucket_lower for x in ["groceries", "gas", "rent", "tithe", "shopping", "eating out"]):
            main_items.append(item)
            
        elif "kensey debt" in bucket_lower:
            # Kensey Debt goes to main, rename to "Kensey School Debt"
            item.display_name = "Kensey School Debt"
            main_items.append(item)
            
        elif "school" in bucket_lower:
            # School is covered by Kensey envelope, skip it
            continue
            
        else:
            other_items.append(item)
    
    # Build email
    body = "📊 YOUR BUDGET CATALOG\n"
    body += "=" * 50 + "\n\n"
    
    # Helper function to display items
    def display_section(section_name, items):
        if not items:
            return ""
        
        section = f"{section_name}\n"
        section += "-" * len(section_name) + "\n"
        total = sum(item.amount for item in items)
        section += f"Total: ${total:,.2f}\n\n"
        
        for item in items:
            # Use display_name if set, otherwise clean up the bucket name
            if hasattr(item, 'display_name'):
                name = item.display_name
            else:
                name = item.bucket
                # Remove prefixes
                for prefix in ["Main - ", "Envelope - ", "Subscription - ", "Insurance - ", "Investment - ", "Education - "]:
                    if name.startswith(prefix):
                        name = name.replace(prefix, "")
                        break
            
            section += f"  • {name}: ${item.amount:,.2f}\n"
        
        section += "\n"
        return section
    
    # Add each section
    body += display_section("MAIN BUDGET", main_items)
    body += display_section("ENVELOPE SAVINGS", envelope_items)
    body += display_section("SUBSCRIPTIONS", sub_items)
    body += display_section("INSURANCE", insurance_items)
    body += display_section("INVESTMENTS", investment_items)
    
    # Other Categories (should be minimal)
    # if other_items:
    #     body += "OTHER CATEGORIES\n"
    #     body += "-" * 16 + "\n\n"
    #     for item in other_items:
    #         body += f"• {item.bucket}: ${item.amount:,.2f}\n"
    #     body += "\n"
    
    # Calculate grand total
    all_items = main_items + envelope_items + sub_items + insurance_items + investment_items
   # all_items = main_items + envelope_items + sub_items + insurance_items + investment_items + other_items
    if all_items:
        grand_total = sum(item.amount for item in all_items)
        body += "=" * 50 + "\n"
        body += f"GRAND TOTAL: ${grand_total:,.2f}\n"
        body += "=" * 50 + "\n\n"
    
    body += "💡 Reply '?' anytime for this catalog\n"
    body += "📝 Reply with expenses to track spending\n"
    body += "💡 Reply '#' anytime to see expense report\n"
    
    sender_extracted = extract_sender(sender)
    print(f"Sending catalog to {sender_extracted}")
    # print("\n" + body)
    
    # return body, sender_extracted
    default_catalog_subject = "Budget Catalog"
    sendEmail(sender_extracted,default_catalog_subject,body)


def extract_sender(sender):
    email = sender.get('email', sender.get('from', 'unknown'))
    # print(f"DEBUG - Extracted email: {email}")
    return str(email)
    



logger = logging.getLogger(__name__)
def populate_db(db: Session, excel_path: str = "Budget.xlsx") -> dict:
    """
    Populate database from Excel file.
    Skips existing entries.
    Returns counts of inserted and skipped items.
    """
    parser = BudgetExcelParser(excel_path)
    
    if not parser.load_sheet():
        return {"error": "Failed to load Excel file"}
    
    # Get all budget items
    budget_items = parser.get_all_budget_items()
    
    inserted = 0
    skipped = 0
    
    for item in budget_items:
        # Check if bucket already exists
        existing = db.query(BudgetItem).filter(
            BudgetItem.bucket == item['bucket']
        ).first()
        
        
        if existing:
            continue
            # Update existing entry
            existing.amount = item['amount']
            existing.updated_at = datetime.now()
            skipped += 1
            logger.debug(f"Updated existing: {item['bucket']}")
        else:
            # Insert new entry
            db_item = BudgetItem(
                bucket=item['bucket'],
                amount=item['amount'],
                updated_at=datetime.now()
            )
            db.add(db_item)
            inserted += 1
            logger.debug(f"Inserted new: {item['bucket']}")
    
    try:
        db.commit()
        logger.info(f"Database populated: {inserted} inserted, {skipped} updated/skipped")
        return {
            "inserted": inserted,
            "skipped": skipped,
            "total": len(budget_items)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to populate database: {e}")
        return {"error": str(e)}
    
def archive_database(db: Session):
    '''Simple archive that just copies tables'''
    
    receiver = 'hconner158@gmail.com'
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Create archive tables
    budget_archive = f"Budget_{current_year}_{current_month:02d}"
    expense_archive = f"Expenses_{current_year}_{current_month:02d}"
    
    try:
        # Archive BudgetItems
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{budget_archive}" AS 
            SELECT *, NOW() as archived_at FROM "BudgetItems";
        """))
        
        # Archive Expenses
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{expense_archive}" AS 
            SELECT *, NOW() as archived_at FROM "Expenses";
        """))
        
        # Clear Expenses for new month
        expense_count = db.query(Expense).count()
        db.query(Expense).delete()
        
        # Repopulate BudgetItems from Excel
        db.query(BudgetItem).delete()
        populate_db(db)
        db.commit()
        # Send simple email
        email_body = f"""
        Monthly archive complete for {current_year}-{current_month:02d}

        Archived {expense_count} expenses to {expense_archive}
        Reset budget from spreadsheet
        Budget now ready for new month

        Reply '?' to see updated budget
        """
        sendEmail(receiver, "Monthly Archive Complete", email_body)
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Archive failed: {e}")
        return False
    
MOUNTAIN_TIME = pytz.timezone('America/Denver')

def schedule_monthly_archive():
    schedule.every().day.at("23:25").do(run_scheduled_archive).timezone = MOUNTAIN_TIME
    # schedule.every().day.at("12:46", tz=MOUNTAIN_TIME).do(run_scheduled_archive)

    
    logger.info(f"📅 Monthly archive scheduled for 11:55 PM Mountain Time on last day of month")
    logger.info(f"📅 Current MT time: {datetime.now(MOUNTAIN_TIME).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run the scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every 1 minutes

def run_scheduled_archive():
    """
    Run the archive only if it's the last day of the month
    """
    if is_last_day_of_month():
    # if True:
        logger.info("⏰ Last day of month detected! Running archive at 11:55 PM MT...")
        
        # Create database session
        db = SessionLocal()
        try:
            # Import your archive function
            from utils import archive_database
            
            success = archive_database(db)

            if success:
                logger.info(f"✅ Monthly archive completed successfully: {success}")
            else:
                logger.error(f"❌ Monthly archive failed: {success}")
                
        except Exception as e:
            logger.error(f"❌ Error in scheduled archive: {e}")
            sendEmail('hconner158@gmail.com','archive error',str(e))
        finally:
            db.close()
    else:
        # It's 11:55 PM but not the last day - skip
        current_time = datetime.now(MOUNTAIN_TIME).strftime('%Y-%m-%d %H:%M:%S')
        print('not the last day')
        logger.debug(f"Not last day of month (current MT: {current_time}), skipping archive")

def is_last_day_of_month():
    """Check if today is the last day of the month"""
    today = datetime.now(MOUNTAIN_TIME)
    tomorrow = today + timedelta(days=1)
    return tomorrow.day == 1