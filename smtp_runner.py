import asyncio
from aiosmtpd.controller import Controller
from database import init_db, save_email
import json
from email import message_from_bytes
from email.policy import default

# Load Config Helper
def load_json_file(filename, default_value):
    try:
        import os
        file_path = os.path.join(os.path.dirname(__file__), filename)
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return default_value

ALLOWED_DOMAINS = load_json_file('domains.json', [])

class DatabaseHandler:
    async def handle_DATA(self, server, session, envelope):
        data = envelope.content
        email_msg = message_from_bytes(data, policy=default)
        subject = email_msg['subject'] or "(No Subject)"
        mail_from = envelope.mail_from
        
        # Extract Body
        body = "No content"
        if email_msg.is_multipart():
            for part in email_msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    break
            if body == "No content":
                 for part in email_msg.walk():
                    if ctype == 'text/html':
                         body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                         break
        else:
            body = email_msg.get_payload(decode=True).decode(email_msg.get_content_charset() or 'utf-8', errors='replace')

        for recipient in envelope.rcpt_tos:
            clean_rcpt = recipient.strip().lower()
            domain_part = clean_rcpt.split('@')[-1]
            
            if domain_part in ALLOWED_DOMAINS:
                print(f"[SMTP] Saving email for: {clean_rcpt}")
                save_email(clean_rcpt, mail_from, subject, body)
            else:
                print(f"[SMTP] Rejected: {clean_rcpt}")
        return '250 Message accepted for delivery'

# --- FUNGSI UTAMA UNTUK LAUNCHER ---
def run_smtp_server():
    init_db()
    handler = DatabaseHandler()
    controller = Controller(handler, hostname='0.0.0.0', port=25)
    controller.start()
    print("[*] SMTP Service Started on Port 25")
    
    # Loop forever
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()

if __name__ == '__main__':
    run_smtp_server()