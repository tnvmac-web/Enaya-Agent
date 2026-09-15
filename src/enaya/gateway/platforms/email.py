#!/usr/bin/env python3
"""
Enaya Agent - Email Adapter
Email (IMAP/SMTP) integration for the gateway.
"""

from __future__ import annotations

import asyncio
import email
import imaplib
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any, Optional

from enaya.gateway.runner import GatewayRunner, MessageEvent


class EmailAdapter:
    """Email (IMAP/SMTP) adapter for the gateway."""
    
    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.imap_host = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
        self.smtp_host = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        self.email_address = os.environ.get("EMAIL_ADDRESS")
        self.email_password = os.environ.get("EMAIL_PASSWORD")
        self.allowed_users = set(
            os.environ.get("EMAIL_ALLOWED_USERS", "").split(",")
        ) if os.environ.get("EMAIL_ALLOWED_USERS") else set()
        self.allow_all = os.environ.get("EMAIL_ALLOW_ALL_USERS", "false").lower() == "true"
        self.poll_interval = int(os.environ.get("EMAIL_POLL_INTERVAL", "30"))
        
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the email polling."""
        if not self.email_address or not self.email_password:
            print("EMAIL_ADDRESS or EMAIL_PASSWORD not set, skipping Email adapter")
            return
        
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        print("Email adapter started")
    
    async def stop(self) -> None:
        """Stop the email polling."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        print("Email adapter stopped")
    
    def authorize_user(self, email_addr: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return email_addr.lower() in {e.lower() for e in self.allowed_users}
    
    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized (by email)."""
        if self.allow_all:
            return True
        return user_id.lower() in {e.lower() for e in self.allowed_users}
    
    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._check_email()
            except Exception as e:
                print(f"Email poll error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _check_email(self) -> None:
        """Check for new emails."""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            imap.login(self.email_address, self.email_password)
            imap.select("INBOX")
            
            # Search for unread messages
            status, messages = imap.search(None, "UNSEEN")
            if status != "OK":
                imap.close()
                imap.logout()
                return
            
            for msg_num in messages[0].split():
                status, msg_data = imap.fetch(msg_num, "(RFC822)")
                if status != "OK":
                    continue
                
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                from_addr = parseaddr(msg["From"])[1]
                
                # Check authorization
                if not self.authorize_user(from_addr):
                    # Send rejection reply
                    await self._send_rejection(from_addr, msg["Message-ID"])
                    continue
                
                # Extract body
                body = self._extract_body(msg)
                
                # Create message event
                msg_event = MessageEvent(
                    platform="email",
                    chat_type="dm",
                    chat_id=from_addr,
                    user_id=from_addr,
                    username=parseaddr(msg["From"])[0],
                    text=body,
                    message_id=msg["Message-ID"] or msg_num.decode(),
                    raw={
                        "subject": msg["Subject"],
                        "to": msg["To"],
                        "date": msg["Date"],
                    },
                )
                
                # Process through gateway
                await self.runner.handle_message(msg_event)
                
                # Mark as read
                imap.store(msg_num, "+FLAGS", "\\Seen")
            
            imap.close()
            imap.logout()
            
        except Exception as e:
            print(f"Email check failed: {e}")
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract text body from email."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        return ""
    
    async def _send_rejection(self, to_addr: str, in_reply_to: str) -> None:
        """Send rejection email."""
        msg = EmailMessage()
        msg["From"] = self.email_address
        msg["To"] = to_addr
        msg["Subject"] = "Re: Unauthorized access"
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
        msg.set_content(
            "You are not authorized to use this bot.\n"
            "Please contact the administrator to be added to the allowlist."
        )
        
        await self._send_email(msg)
    
    async def send_message(self, chat_id: str, text: str, reply_to: Optional[str] = None) -> None:
        """Send an email reply."""
        msg = EmailMessage()
        msg["From"] = self.email_address
        msg["To"] = chat_id
        msg["Subject"] = "Re: Enaya Agent Response"
        if reply_to:
            msg["In-Reply-To"] = reply_to
            msg["References"] = reply_to
        msg.set_content(text)
        
        await self._send_email(msg)
    
    async def _send_email(self, msg: EmailMessage) -> None:
        """Send email via SMTP."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self.email_address, self.email_password)
                smtp.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")


def setup_email(runner: GatewayRunner) -> Optional[EmailAdapter]:
    """Set up Email adapter if configured."""
    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")
    if not email_address or not email_password:
        return None
    
    adapter = EmailAdapter(runner)
    runner.register_adapter("email", adapter)
    return adapter