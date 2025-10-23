import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("email-server")


# Email configuration - USE ENVIRONMENT VARIABLES FOR SECURITY
EMAIL_CONFIG = {
    'imap_server': 'imap.gmail.com',
    'imap_port': 993,
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': os.getenv('EMAIL_ADDRESS'),
    'password': os.getenv('EMAIL_PASSWORD'),  # Use App Password
}


@mcp.tool()
async def send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Send an email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured. Please set EMAIL_CONFIG."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = to
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server and send
        try:
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.set_debuglevel(1)  # Enable debug output
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
            
            recipients = [to]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(',')])
            
            text = msg.as_string()
            server.sendmail(EMAIL_CONFIG['email'], recipients, text)
            server.quit()
            
            return f"✅ Email sent successfully to {to}"
        
        except smtplib.SMTPAuthenticationError as auth_err:
            return f"❌ Authentication failed: {str(auth_err)}\nPlease verify:\n1. 2FA is enabled\n2. App Password is correct (16 chars, no spaces)\n3. 'Less secure app access' is NOT needed with App Passwords"
        
        except smtplib.SMTPException as smtp_err:
            return f"❌ SMTP Error: {str(smtp_err)}"
        
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


@mcp.tool()
async def read_emails(folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> str:
    """Read emails from a folder.
    
    Args:
        folder: Email folder (INBOX, SENT, etc.)
        limit: Number of emails to retrieve
        unread_only: Only fetch unread emails
    
    Returns:
        List of emails with basic information
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured. Please set EMAIL_CONFIG."
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.select(folder)
        
        # Search for emails
        search_criteria = 'UNSEEN' if unread_only else 'ALL'
        status, messages = mail.search(None, search_criteria)
        
        if status != 'OK':
            return f"❌ Error searching emails in {folder}"
        
        email_ids = messages[0].split()
        
        if not email_ids:
            return f"📧 No {'unread ' if unread_only else ''}emails in {folder}"
        
        # Get recent emails (reverse order - newest first)
        recent_emails = list(reversed(email_ids[-limit:] if len(email_ids) >= limit else email_ids))
        
        result = f"📧 Recent {len(recent_emails)} {'unread ' if unread_only else ''}emails from {folder}:\n"
        result += "=" * 60 + "\n\n"
        
        for email_id in recent_emails:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                    
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract basic info
                from_addr = email_message.get('From', 'Unknown')
                to_addr = email_message.get('To', 'Unknown')
                subject = email_message.get('Subject', 'No Subject')
                date = email_message.get('Date', 'Unknown')
                
                # Get email body preview
                body_preview = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body_preview = part.get_payload(decode=True).decode()[:200]
                                break
                            except:
                                pass
                else:
                    try:
                        body_preview = email_message.get_payload(decode=True).decode()[:200]
                    except:
                        pass
                
                result += f"📨 Email ID: {email_id.decode()}\n"
                result += f"From: {from_addr}\n"
                result += f"To: {to_addr}\n"
                result += f"Subject: {subject}\n"
                result += f"Date: {date}\n"
                if body_preview:
                    result += f"Preview: {body_preview}...\n"
                result += "-" * 40 + "\n\n"
            except Exception as e:
                result += f"⚠️ Error processing email {email_id.decode()}: {str(e)}\n\n"
        
        mail.close()
        mail.logout()
        
        return result
        
    except imaplib.IMAP4.error as imap_err:
        return f"❌ IMAP Error: {str(imap_err)}\nPlease verify your credentials and IMAP access is enabled."
    except Exception as e:
        return f"❌ Error reading emails: {str(e)}"


@mcp.tool()
async def get_unread_count(folder: str = "INBOX") -> str:
    """Get count of unread emails.
    
    Args:
        folder: Email folder to check
    
    Returns:
        Unread email count
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured."
        
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.select(folder)
        
        status, messages = mail.search(None, 'UNSEEN')
        unread_count = len(messages[0].split()) if messages[0] else 0
        
        mail.close()
        mail.logout()
        
        return f"📊 {folder}: {unread_count} unread email(s)"
        
    except Exception as e:
        return f"❌ Error getting unread count: {str(e)}"


@mcp.tool()
async def mark_as_read(email_id: str, folder: str = "INBOX") -> str:
    """Mark an email as read.
    
    Args:
        email_id: Email ID to mark as read
        folder: Folder containing the email
    """
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.select(folder)
        
        mail.store(email_id, '+FLAGS', '\\Seen')
        
        mail.close()
        mail.logout()
        
        return f"✅ Email {email_id} marked as read"
        
    except Exception as e:
        return f"❌ Error marking email as read: {str(e)}"


@mcp.tool()
async def search_emails(query: str, folder: str = "INBOX", limit: int = 10) -> str:
    """Search emails by query.
    
    Args:
        query: Search query
        folder: Email folder to search
        limit: Number of results to return
    
    Returns:
        Search results
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured. Please set EMAIL_CONFIG."
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.select(folder)
        
        # Search for emails
        status, messages = mail.search(None, f'SUBJECT "{query}"')
        email_ids = messages[0].split()
        
        if not email_ids:
            return f"No emails found matching '{query}' in {folder}"
        
        # Get matching emails
        matching_emails = list(reversed(email_ids[-limit:] if len(email_ids) >= limit else email_ids))
        
        result = f"🔍 Search results for '{query}' in {folder} ({len(email_ids)} total matches):\n"
        result += "=" * 60 + "\n\n"
        
        for email_id in matching_emails:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            from_addr = email_message.get('From', 'Unknown')
            subject = email_message.get('Subject', 'No Subject')
            date = email_message.get('Date', 'Unknown')
            
            result += f"📨 Email ID: {email_id.decode()}\n"
            result += f"From: {from_addr}\n"
            result += f"Subject: {subject}\n"
            result += f"Date: {date}\n"
            result += "-" * 40 + "\n\n"
        
        mail.close()
        mail.logout()
        
        return result
        
    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"


@mcp.tool()
async def get_email_folders() -> str:
    """Get list of email folders.
    
    Returns:
        List of available email folders
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured. Please set EMAIL_CONFIG."
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        
        # List folders
        status, folders = mail.list()
        
        result = "📁 Available Email Folders:\n"
        result += "=" * 40 + "\n\n"
        
        for folder in folders:
            folder_info = folder.decode()
            result += f"📂 {folder_info}\n"
        
        mail.logout()
        
        return result
        
    except Exception as e:
        return f"❌ Error getting folders: {str(e)}"


@mcp.tool()
async def delete_email(email_id: str, folder: str = "INBOX") -> str:
    """Delete an email by ID.
    
    Args:
        email_id: Email ID to delete
        folder: Folder containing the email
    
    Returns:
        Deletion status
    """
    try:
        if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
            return "Error: Email credentials not configured. Please set EMAIL_CONFIG."
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.select(folder)
        
        # Delete email
        mail.store(email_id, '+FLAGS', '\\Deleted')
        mail.expunge()
        
        mail.close()
        mail.logout()
        
        return f"✅ Email {email_id} deleted successfully from {folder}"
        
    except Exception as e:
        return f"❌ Error deleting email: {str(e)}"


@mcp.tool()
async def test_connection() -> str:
    """Test email server connection.
    
    Returns:
        Connection status
    """
    results = []
    
    # Test SMTP
    try:
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.quit()
        results.append("✅ SMTP connection successful")
    except Exception as e:
        results.append(f"❌ SMTP connection failed: {str(e)}")
    
    # Test IMAP
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port'])
        mail.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        mail.logout()
        results.append("✅ IMAP connection successful")
    except Exception as e:
        results.append(f"❌ IMAP connection failed: {str(e)}")
    
    return "\n".join(results)


@mcp.resource("email://{resource}")
def email_resource(resource: str) -> str:
    """Access email resources"""
    return f"Email resource: {resource}"


if __name__ == "__main__":
    # Run the server
    import asyncio
    asyncio.run(mcp.run())
