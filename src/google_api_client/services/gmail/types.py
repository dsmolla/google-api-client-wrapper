
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from html2text import html2text

from src.google_api_client.utils.datetime import convert_datetime_to_readable


@dataclass
class EmailAddress:
    """
    Represents an email address with name and email.
    Args:
        email: The email address.
        name: The display name (optional).
    """
    email: str
    name: Optional[str] = None


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


@dataclass
class EmailAttachment:
    """
    Represents an email attachment.
    Args:
        filename: The name of the attachment file.
        content_type: The MIME type of the attachment.
        size: The size of the attachment in bytes.
        attachment_id: The unique identifier for the attachment in Gmail.
        message_id: The message id of the message the attachment is attached to.
    """
    filename: str
    content_type: str
    size: int
    attachment_id: str
    message_id: str


    def to_dict(self) -> dict:
        """
        Converts the EmailAttachment instance to a dictionary representation.
        Returns:
            A dictionary containing the attachment data.
        """
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "attachment_id": self.attachment_id,
            "message_id": self.message_id,
        }


@dataclass
class Label:
    """
    Represents a Gmail label.
    Args:
        id: The unique identifier for the label.
        name: The name of the label.
        type: The type of the label (e.g., system, user).
    """
    id: str
    name: str
    type: str

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
        }

    def __repr__(self):
        return f"Label(id={self.id}, name={self.name}, type={self.type})"


@dataclass
class EmailMessage:
    """
    Represents a Gmail message with various attributes.
    Args:
        message_id: Unique identifier for the message.
        thread_id: The thread ID this message belongs to.
        subject: The subject line of the email.
        sender: The sender's email address information.
        recipients: List of recipient email addresses (To field).
        cc_recipients: List of CC recipient email addresses.
        bcc_recipients: List of BCC recipient email addresses.
        date_time: When the message was sent or received.
        body_text: Plain text body of the email.
        body_html: HTML body of the email.
        attachments: List of attachments in the email.
        labels: List of Gmail labels applied to the message.
        is_read: Whether the message has been read.
        is_starred: Whether the message is starred.
        is_important: Whether the message is marked as important.
        snippet: A short snippet of the message content.
        reply_to_id: The ID of the message to use when replying to this message.
    """
    message_id: Optional[str] = None
    thread_id: Optional[str] = None

    reply_to_id: Optional[str] = None
    references: Optional[str] = None

    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)

    sender: Optional[EmailAddress] = None
    recipients: List[EmailAddress] = field(default_factory=list)
    cc_recipients: List[EmailAddress] = field(default_factory=list)
    bcc_recipients: List[EmailAddress] = field(default_factory=list)

    date_time: Optional[datetime] = None

    labels: List[str] = field(default_factory=list)
    is_read: bool = False
    is_starred: bool = False
    is_important: bool = False

    snippet: Optional[str] = None

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

    def __repr__(self):
        return (
            f"Subject: {self.subject!r}\n"
            f"From: {self.sender}\n"
            f"To: {', '.join(str(r) for r in self.recipients)}\n"
            f"Date: {convert_datetime_to_readable(self.date_time) if self.date_time else 'Unknown'}\n"
            f"Snippet: {self.snippet}\n"
            f"Labels: {', '.join(self.labels)}\n"
        )
