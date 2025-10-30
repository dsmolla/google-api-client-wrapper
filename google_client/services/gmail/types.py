from datetime import datetime
from typing import Optional, List

from html2text import html2text
from pydantic import BaseModel, Field

from google_client.utils.datetime import datetime_to_readable


class EmailAddress(BaseModel):
    """
    Represents an email address with name and email.
    """
    email: str = Field(..., description="The email address")
    name: Optional[str] = Field(None, description="The display name")

    def to_dict(self) -> dict:
        """
        Converts the EmailAddress instance to a dictionary representation.
        Returns:
            A dictionary containing the email address data.
        """
        result = {"email": self.email}
        if self.name:
            result["name"] = self.name
        return result

    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailAttachment(BaseModel):
    """
    Represents an email attachment.
    """
    filename: str = Field(..., description="The name of the attachment file")
    mime_type: str = Field(..., description="The MIME type of the attachment")
    size: int = Field(..., description="The size of the attachment in bytes")
    attachment_id: str = Field(..., description="The unique identifier for the attachment in Gmail")
    message_id: str = Field(..., description="The message id of the message the attachment is attached to")

    def to_dict(self) -> dict:
        """
        Converts the EmailAttachment instance to a dictionary representation.
        Returns:
            A dictionary containing the attachment data.
        """
        return {
            "filename": self.filename,
            "content_type": self.mime_type,
            "size": self.size,
            "attachment_id": self.attachment_id,
            "message_id": self.message_id,
        }

    def __repr__(self):
        return (f"Attachment(filename={self.filename}, mime_type={self.mime_type}, "
                f"size={self.size}), attachment_id={self.attachment_id}), message_id={self.message_id})"
                )


class Label(BaseModel):
    """
    Represents a Gmail label.
    """
    id: str = Field(..., description="The unique identifier for the label")
    name: str = Field(..., description="The name of the label")
    type: str = Field(..., description="The type of the label (e.g., system, user)")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
        }

    def __repr__(self):
        return f"Label(id={self.id}, name={self.name}, type={self.type})"


class EmailThread(BaseModel):
    """
    Represents a Gmail thread containing multiple related messages.
    """
    thread_id: Optional[str] = Field(None, description="Unique identifier for the thread")
    messages: List["EmailMessage"] = Field(default_factory=list,
                                           description="List of EmailMessage objects in this thread")
    snippet: Optional[str] = Field(None, description="A short snippet of the thread content")
    history_id: Optional[str] = Field(None, description="The history ID of the thread")

    def get_latest_message(self) -> Optional["EmailMessage"]:
        """
        Gets the most recent message in the thread.
        Returns:
            The latest EmailMessage or None if no messages exist.
        """
        if not self.messages:
            return None
        return max(self.messages, key=lambda msg: msg.date_time or datetime.min)

    def get_unread_count(self) -> int:
        """
        Gets the number of unread messages in the thread.
        Returns:
            Count of unread messages.
        """
        return sum(1 for msg in self.messages if not msg.is_read)

    def has_unread_messages(self) -> bool:
        """
        Checks if the thread has any unread messages.
        Returns:
            True if there are unread messages, False otherwise.
        """
        return any(not msg.is_read for msg in self.messages)

    def get_participants(self) -> List[EmailAddress]:
        """
        Gets all unique participants in the thread.
        Returns:
            List of unique EmailAddress objects from all messages.
        """
        participants = set()
        for message in self.messages:
            if message.sender:
                participants.add((message.sender.email, message.sender.name))
            for recipient in message.recipients + message.cc_recipients + message.bcc_recipients:
                participants.add((recipient.email, recipient.name))

        return [EmailAddress(email=email, name=name) for email, name in participants]

    def __repr__(self):
        latest = self.get_latest_message()
        return (
            f"Thread ID: {self.thread_id}\n"
            f"Messages: {len(self.messages)}\n"
            f"Unread: {self.get_unread_count()}\n"
            f"Latest: {latest.subject if latest else 'No messages'}\n"
            f"Snippet: {self.snippet}\n"
        )


class EmailMessage(BaseModel):
    """
    Represents a Gmail message with various attributes.
    """
    message_id: Optional[str] = Field(None, description="Unique identifier for the message")
    thread_id: Optional[str] = Field(None, description="The thread ID this message belongs to")

    reply_to_id: Optional[str] = Field(None, description="The ID of the message to use when replying to this message")
    references: Optional[str] = Field(None, description="References header for message threading")

    subject: Optional[str] = Field(None, description="The subject line of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email")
    body_text: Optional[str] = Field(None, description="Plain text body of the email")
    attachments: List[EmailAttachment] = Field(default_factory=list, description="List of attachments in the email")

    sender: Optional[EmailAddress] = Field(None, description="The sender's email address information")
    recipients: List[EmailAddress] = Field(default_factory=list,
                                           description="List of recipient email addresses (To field)")
    cc_recipients: List[EmailAddress] = Field(default_factory=list, description="List of CC recipient email addresses")
    bcc_recipients: List[EmailAddress] = Field(default_factory=list,
                                               description="List of BCC recipient email addresses")

    date_time: Optional[datetime] = Field(None, description="When the message was sent or received")

    labels: List[str] = Field(default_factory=list, description="List of Gmail labels applied to the message")
    is_read: bool = Field(False, description="Whether the message has been read")
    is_starred: bool = Field(False, description="Whether the message is starred")
    is_important: bool = Field(False, description="Whether the message is marked as important")

    snippet: Optional[str] = Field(None, description="A short snippet of the message content")

    def get_plain_text_content(self) -> str:
        """
        Retrieves the plain text content of the email message, converting HTML if necessary.
        Returns:
            The plain text content if available, empty string otherwise.
        """
        if self.body_text:
            return self.body_text.strip()
        elif self.body_html:
            return html2text(self.body_html)
        return ""

    def has_attachments(self) -> bool:
        """
        Checks if the message has attachments.
        Returns:
            True if the message has attachments, False otherwise.
        """
        return len(self.attachments) > 0

    def get_recipient_emails(self) -> List[str]:
        """
        Retrieves a list of recipient emails (To).
        Returns:
            A list of recipient email addresses.
        """
        return [recipient.email for recipient in self.recipients]

    def get_all_recipient_emails(self) -> List[str]:
        """
        Retrieves a list of all recipient email addresses (To, CC, BCC).
        Returns:
            A list of email addresses.
        """
        emails = []
        for recipient in self.recipients + self.cc_recipients + self.bcc_recipients:
            emails.append(recipient.email)
        return emails

    def is_from(self, email: str) -> bool:
        """
        Checks if the message is from a specific email address.
        Use "me" to check if the message is from the authenticated user.
        Args:
            email: The email address to check.

        Returns:
            True if the message is from the specified email, False otherwise.
        """
        if email.lower() == "me":
            # Special case for checking if the message is from the authenticated user
            return 'SENT' in self.labels

        return self.sender and self.sender.email.lower() == email.lower()

    def has_label(self, label: str) -> bool:
        """
        Checks if the message has a specific label.
        Args:
            label: The label to check for.

        Returns:
            True if the message has the label, False otherwise.
        """
        return label in self.labels

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "sender": self.sender.email,
            "recipients": [recipient.email for recipient in self.recipients],
            "date_time": datetime_to_readable(self.date_time),
            "subject": self.subject,
            "labels": self.labels,
            "snippet": self.snippet.encode("ascii", "ignore").decode("ascii"),
            "body": self.get_plain_text_content().encode("ascii", "ignore").decode("ascii"),
            "attachments": [attachment.to_dict() for attachment in self.attachments],
        }

    def __repr__(self):
        return (
            f"Subject: {self.subject!r}\n"
            f"From: {self.sender}\n"
            f"To: {', '.join(str(r) for r in self.recipients)}\n"
            f"Date: {datetime_to_readable(self.date_time) if self.date_time else 'Unknown'}\n"
            f"Snippet: {self.snippet}\n"
            f"Labels: {', '.join(self.labels)}\n"
        )

    def __str__(self):
        return (
            f"Subject: {self.subject!r}\n"
            f"From: {self.sender}\n"
            f"To: {', '.join(str(r) for r in self.recipients)}\n"
            f"Date: {datetime_to_readable(self.date_time) if self.date_time else 'Unknown'}\n"
            f"Snippet: {self.snippet}\n"
            f"Labels: {', '.join(self.labels)}\n"
        )
