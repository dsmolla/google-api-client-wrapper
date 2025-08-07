from datetime import datetime
from typing import Optional, List, Self, Dict, Any
from ...auth.manager import auth_manager
from ...utils.datetime import convert_datetime_to_readable, convert_datetime_to_local_timezone
from dataclasses import dataclass, field
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import getaddresses, parsedate_to_datetime
import mimetypes
import html
import os
from html2text import html2text
from googleapiclient.errors import HttpError
from contextlib import contextmanager
import re

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 2500
MAX_SUBJECT_LENGTH = 998  # RFC 2822 practical limit
MAX_BODY_LENGTH = 25000000  # ~25MB Gmail limit
DEFAULT_MAX_RESULTS = 30

# Import exceptions from centralized location
from ...exceptions.gmail import GmailError, GmailPermissionError, EmailNotFoundError

@contextmanager
def gmail_service():
    """Context manager for Gmail service connections with error handling."""
    service = None
    try:
        service = auth_manager.get_gmail_service()
        yield service
    except HttpError as e:
        if e.resp.status == 403:
            raise GmailPermissionError(f"Permission denied: {e}")
        elif e.resp.status == 404:
            raise EmailNotFoundError(f"Email or label not found: {e}")
        else:
            raise GmailError(f"Gmail API error: {e}")
    except Exception as e:
        raise GmailError(f"Unexpected Gmail service error: {e}")
    finally:
        # Clean up if needed (service doesn't require explicit cleanup)
        pass


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

    def __post_init__(self):
        if not self.email:
            raise ValueError("Email address cannot be empty.")
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format using regex."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

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
        data: The attachment data (optional, loaded on demand).
    """
    filename: str
    content_type: str
    size: int
    attachment_id: str
    message_id: str
    data: Optional[bytes] = None

    def __post_init__(self):
        if not self.filename:
            raise ValueError("Attachment filename cannot be empty")
        if not self.attachment_id:
            raise ValueError("Attachment ID cannot be empty")
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")

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

    def load_data(self) -> bool:
        """
        Downloads the attachment from the Gmail API and loads it into the data variable.
        Returns:
            True if the attachment was successfully loaded.
        """
        self.data = self._get_attachment_data()
        return True

    def download_attachment(self, directory: str) -> bool:
        """
        Downloads the attachment from the Gmail API and saves it into the specified directory with the original filename.
        Args:
            directory: The destination directory for the attachment.

        Returns:
            True if the attachment was successfully downloaded.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        if not os.path.isdir(directory):
            raise ValueError(f"Provided path '{directory}' is not a directory.")

        file_path = os.path.join(directory, self.filename)
        logger.info("Downloading attachment %s[%s] from message %s to %s",
                    self.attachment_id, self.filename, self.message_id, file_path)
        try:
            with open(file_path, 'wb') as f:
                f.write(self._get_attachment_data())
        except Exception as e:
            logger.error("Error downloading attachment: %s", e)
            raise

        return True

    def _get_attachment_data(self) -> bytes:
        """
        Retrieves the attachment in bytes from a message.

        Returns:
            The attachment data as bytes.
        """
        logger.info("Retrieving attachment %s from message %s", self.attachment_id, self.message_id)
        
        with gmail_service() as service:
            try:
                attachment = service.users().messages().attachments().get(
                    userId='me',
                    messageId=self.message_id,
                    id=self.attachment_id
                ).execute()

                data = attachment['data']
                return base64.urlsafe_b64decode(data + '===')
            except Exception as e:
                logger.error("Error downloading attachment: %s", e)
                raise


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

    def __post_init__(self):
        if not self.id:
            raise ValueError("Label ID cannot be empty")
        if not self.name:
            raise ValueError("Label name cannot be empty")

    @classmethod
    def list_labels(cls) -> List["Label"]:
        """
        Fetches a list of labels from Gmail.
        Returns:
            A list of Label objects representing the labels.
        """
        logger.info("Fetching labels from Gmail")
        
        with gmail_service() as service:
            try:
                labels_response = service.users().labels().list(userId='me').execute()
                labels = labels_response.get('labels', [])
                logger.info("Found %d labels", len(labels))

                labels_list = []
                for label in labels:
                    labels_list.append(cls(
                        id=label.get('id'),
                        name=label.get('name'),
                        type=label.get('type')
                    ))

                return labels_list
            except Exception as e:
                logger.error("Failed to fetch labels: %s", e)
                raise

    @classmethod
    def create_label(cls, name: str) -> "Label":
        """
        Creates a new label in Gmail.
        Args:
            name: The name of the label to create.

        Returns:
            A Label object representing the created label including its ID, name, and type.
        """
        logger.info("Creating label with name: %s", name)
        
        with gmail_service() as service:
            try:
                label = service.users().labels().create(
                    userId='me',
                    body={'name': name, 'type': 'user'}
                ).execute()
                return cls(
                    id=label.get('id'),
                    name=label.get('name'),
                    type=label.get('type', 'user')
                )
            except Exception as e:
                logger.error("Error creating label: %s", e)
                raise

    @classmethod
    def get_label(cls, label_id: str) -> "Label":
        """
        Retrieves a specific label by its ID.
        Args:
            label_id: The unique identifier of the label to retrieve.

        Returns:
            A Label object representing the label including its ID, name, and type.
        """
        logger.info("Retrieving label with ID: %s", label_id)
        
        with gmail_service() as service:
            try:
                label = service.users().labels().get(userId='me', id=label_id).execute()
                return cls(
                    id=label.get('id'),
                    name=label.get('name'),
                    type=label.get('type')
                )
            except Exception as e:
                logger.error("Error retrieving label: %s", e)
                raise

    def delete_label(self) -> bool:
        """
        Deletes this label.

        Returns:
            True if the label was successfully deleted, False otherwise.
        """
        logger.info("Deleting label with ID: %s", self.id)
        
        with gmail_service() as service:
            try:
                service.users().labels().delete(userId='me', id=self.id).execute()
                logger.info("Label deleted successfully")
                return True
            except Exception as e:
                logger.error("Error deleting label: %s", e)
                return False

    def update_label(self, new_name: str) -> "Label":
        """
        Updates the name of this label.
        Args:
            new_name: The new name for the label.

        Returns:
            The updated Label object.
        """
        logger.info("Updating label %s to new name: %s", self.id, new_name)
        
        with gmail_service() as service:
            try:
                updated_label = service.users().labels().patch(
                    userId='me',
                    id=self.id,
                    body={'name': new_name}
                ).execute()
                self.name = updated_label.get('name')
                return self
            except Exception as e:
                logger.error("Error updating label: %s", e)
                raise

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
        label_ids: List of Gmail labels applied to the message.
        is_read: Whether the message has been read.
        is_starred: Whether the message is starred.
        is_important: Whether the message is marked as important.
        snippet: A short snippet of the message content.
        reply_to_id: The ID of the message to use when replying to this message.
    """
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    reply_to_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[EmailAddress] = None
    recipients: List[EmailAddress] = field(default_factory=list)
    cc_recipients: List[EmailAddress] = field(default_factory=list)
    bcc_recipients: List[EmailAddress] = field(default_factory=list)
    date_time: Optional[datetime] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    label_ids: List[str] = field(default_factory=list)
    is_read: bool = False
    is_starred: bool = False
    is_important: bool = False
    snippet: Optional[str] = None

    def __post_init__(self):
        self._validate_text_field(self.subject, MAX_SUBJECT_LENGTH, "subject")
        self._validate_text_field(self.body_text, MAX_BODY_LENGTH, "body_text")
        self._validate_text_field(self.body_html, MAX_BODY_LENGTH, "body_html")

    def _validate_text_field(self, value: Optional[str], max_length: int, field_name: str) -> None:
        """Validates text field length and content."""
        if value and len(value) > max_length:
            raise ValueError(f"Email {field_name} cannot exceed {max_length} characters")

    @staticmethod
    def _extract_body(payload: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts plain text and HTML body from Gmail message payload.
        Returns:
            A tuple of (plain_text, html_text)
        """
        body_text = None
        body_html = None

        def decode_body(data: str) -> str:
            """Decode base64url encoded body data."""
            try:
                return base64.urlsafe_b64decode(data + '===').decode('utf-8')
            except:
                return ""

        def extract_from_parts(parts: List[dict]):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body_text = decode_body(part['body']['data'])
                elif mime_type == 'text/html' and part.get('body', {}).get('data'):
                    body_html = decode_body(part['body']['data'])
                elif part.get('parts'):
                    extract_from_parts(part['parts'])

        # Handle different payload structures
        if payload.get('parts'):
            extract_from_parts(payload['parts'])
        elif payload.get('body', {}).get('data'):
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain':
                body_text = decode_body(payload['body']['data'])
            elif mime_type == 'text/html':
                body_html = decode_body(payload['body']['data'])

        return body_text, body_html

    @staticmethod
    def _extract_attachments(message_id: str, payload: dict) -> List[EmailAttachment]:
        """
        Extracts attachment information from Gmail message payload.
        Returns:
            A list of EmailAttachment objects.
        """
        attachments = []

        def extract_from_parts(parts: List[dict]):
            for part in parts:
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    try:
                        attachment = EmailAttachment(
                            filename=part['filename'],
                            content_type=part.get('mimeType', 'application/octet-stream'),
                            size=part.get('body', {}).get('size', 0),
                            attachment_id=part['body']['attachmentId'],
                            message_id=message_id
                        )
                        attachments.append(attachment)
                    except ValueError as e:
                        logger.warning("Skipping invalid attachment: %s", e)
                elif part.get('parts'):
                    extract_from_parts(part['parts'])

        if payload.get('parts'):
            extract_from_parts(payload['parts'])

        return attachments

    @staticmethod
    def _from_gmail_message(gmail_message: dict) -> "EmailMessage":
        """
        Creates an EmailMessage instance from a Gmail API response.
        Args:
            gmail_message: A dictionary containing message data from Gmail API.

        Returns:
            An EmailMessage instance populated with the data from the dictionary.
        """
        headers = {}
        payload = gmail_message.get('payload', {})

        # Extract headers
        for header in payload.get('headers', []):
            headers[header['name'].lower()] = header['value']

        # Parse email addresses
        def parse_email_addresses(header_value: str) -> List[EmailAddress]:
            if not header_value:
                return []

            addresses = []
            for name, email in getaddresses([header_value]):
                if email and EmailAddress._is_valid_email(email):
                    try:
                        addresses.append(EmailAddress(email=email, name=name if name else None))
                    except ValueError as e:
                        logger.warning("Skipping invalid email address: %s", e)
            return addresses

        sender = None
        if headers.get('from'):
            sender_list = parse_email_addresses(headers['from'])
            sender = sender_list[0] if sender_list else None

        recipients = parse_email_addresses(headers.get('to', ''))
        cc_recipients = parse_email_addresses(headers.get('cc', ''))
        bcc_recipients = parse_email_addresses(headers.get('bcc', ''))

        # Extract body
        body_text, body_html = EmailMessage._extract_body(payload)

        # Extract attachments
        message_id = gmail_message.get('id')
        attachments = EmailMessage._extract_attachments(message_id, payload)

        # Parse date
        date_received = None
        if headers.get('date'):
            try:
                # Parse RFC 2822 date format
                date_received = parsedate_to_datetime(headers['date'])
                date_received = convert_datetime_to_local_timezone(date_received)
            except:
                logger.warning("Failed to parse date: %s", headers.get('date'))

        # Extract labels
        labels = gmail_message.get('labelIds', [])

        # Determine read status, starred, important
        is_read = 'UNREAD' not in labels
        is_starred = 'STARRED' in labels
        is_important = 'IMPORTANT' in labels

        return EmailMessage(
            message_id=gmail_message.get('id'),
            thread_id=gmail_message.get('threadId'),
            subject=headers.get('subject', "").strip(),
            sender=sender,
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            date_time=date_received,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            label_ids=labels,
            is_read=is_read,
            is_starred=is_starred,
            is_important=is_important,
            snippet=html.unescape(gmail_message.get('snippet')).strip(),
            reply_to_id=headers.get('message-id')
        )

    @staticmethod
    def _create_message(
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachments: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None

    ) -> str:
        """
        Creates a MIMEText email message.
        Args:
            to: List of recipient email addresses.
            subject: The subject line of the email.
            body_text: Plain text body of the email (optional).
            body_html: HTML body of the email (optional).
            cc: List of CC recipient email addresses (optional).
            bcc: List of BCC recipient email addresses (optional).
            attachments: List of file paths to attach (optional).
            reply_to_message_id: ID of message this is replying to (optional).

        Returns:
            A MIMEText object representing the email message.
        """
        if not to:
            raise ValueError("At least one recipient is required.")

        # Validate inputs
        if subject and len(subject) > MAX_SUBJECT_LENGTH:
            raise ValueError(f"Subject cannot exceed {MAX_SUBJECT_LENGTH} characters")
        if body_text and len(body_text) > MAX_BODY_LENGTH:
            raise ValueError(f"Body text cannot exceed {MAX_BODY_LENGTH} characters")
        if body_html and len(body_html) > MAX_BODY_LENGTH:
            raise ValueError(f"Body HTML cannot exceed {MAX_BODY_LENGTH} characters")

        if body_html and body_text:
            message = MIMEMultipart('alternative')
            message.attach(MIMEText(body_text, 'plain'))
            message.attach(MIMEText(body_html, 'html'))
        elif body_html:
            message = MIMEText(body_html, 'html')
        else:
            message = MIMEText(body_text or '', 'plain')

        message['to'] = ', '.join(to)
        message['subject'] = subject

        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)

        # Add attachments
        if attachments:
            # Convert to multipart if needed
            if not isinstance(message, MIMEMultipart):
                original_message = message
                message = MIMEMultipart()
                message.attach(original_message)
                message['to'] = ', '.join(to)
                message['subject'] = subject
                if cc:
                    message['cc'] = ', '.join(cc)
                if bcc:
                    message['bcc'] = ', '.join(bcc)

            for file_path in attachments:
                if os.path.isfile(file_path):
                    content_type, encoding = mimetypes.guess_type(file_path)
                    if content_type is None or encoding is not None:
                        content_type = 'application/octet-stream'

                    main_type, sub_type = content_type.split('/', 1)

                    with open(file_path, 'rb') as fp:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(fp.read())
                        encoders.encode_base64(attachment)
                        attachment.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        message.attach(attachment)

        # Add reply headers if this is a reply
        if reply_to_message_id:
            message['In-Reply-To'] = reply_to_message_id
            message['References'] = reply_to_message_id

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return raw_message

    @classmethod
    def query(cls) -> "EmailQueryBuilder":
        """
        Create a new EmailQueryBuilder for building complex email queries with a fluent API.
        
        Returns:
            EmailQueryBuilder instance for method chaining
            
        Example:
            emails = (EmailMessage.query()
                .limit(50)
                .from_sender("sender@example.com")
                .search("meeting")
                .with_attachments()
                .execute())
        """
        from .query_builder import EmailQueryBuilder
        return EmailQueryBuilder(cls)

    @classmethod
    def list_emails(
            cls,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            query: Optional[str] = None,
            include_spam_trash: bool = False,
            label_ids: Optional[List[str]] = None
    ) -> List[Self]:
        """
        Fetches a list of messages from Gmail with optional filtering.

        Args:
            max_results: Maximum number of messages to retrieve. Defaults to 30.
            query: Gmail search query string (same syntax as Gmail search).
            include_spam_trash: Whether to include messages from spam and trash.
            label_ids: List of label IDs to filter by.

        Returns:
            A list of EmailMessage objects representing the messages found.
            If no messages are found, an empty list is returned.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        logger.info("Fetching messages with max_results=%s, query=%s, include_spam_trash=%s, label_ids=%s",
                    max_results, query, include_spam_trash, label_ids)

        with gmail_service() as service:
            # Get list of message IDs
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'includeSpamTrash': include_spam_trash
            }

            if query:
                request_params['q'] = query
            if label_ids:
                request_params['labelIds'] = label_ids

            try:
                result = service.users().messages().list(**request_params).execute()
                messages = result.get('messages', [])

                logger.info("Found %d message IDs", len(messages))

                # Fetch full message details
                email_messages = []
                for message in messages:
                    try:
                        email_messages.append(cls.get_email(message['id']))
                    except Exception as e:
                        logger.warning("Failed to fetch message: %s", e)

                logger.info("Successfully fetched %d complete messages", len(email_messages))
                return email_messages

            except Exception as e:
                logger.error("An error occurred while fetching messages: %s", e)
                raise

    @classmethod
    def get_email(cls, message_id: str) -> "EmailMessage":
        """
        Retrieves a specific message from Gmail using its unique identifier.

        Args:
            message_id: The unique identifier of the message to be retrieved.

        Returns:
            An EmailMessage object representing the message with the specified ID.
        """
        logger.info("Retrieving message with ID: %s", message_id)
        
        with gmail_service() as service:
            try:
                gmail_message = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                logger.info("Message retrieved successfully")
                return cls._from_gmail_message(gmail_message)
            except Exception as e:
                logger.error("Error retrieving message: %s", e)
                raise

    @classmethod
    def send_email(
            cls,
            to: List[str],
            subject: Optional[str] = None,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachments: Optional[List[str]] = None,
            reply_to_message_id: Optional[str] = None,
            thread_id: Optional[str] = None
    ) -> Self:
        """
        Sends a new email message.

        Args:
            to: List of recipient email addresses.
            subject: The subject line of the email.
            body_text: Plain text body of the email (optional).
            body_html: HTML body of the email (optional).
            cc: List of CC recipient email addresses (optional).
            bcc: List of BCC recipient email addresses (optional).
            attachments: List of file paths to attach (optional).
            reply_to_message_id: ID of message this is replying to (optional).
            thread_id: ID of the thread to which this message belongs (optional).

        Returns:
            An EmailMessage object representing the message sent.
        """
        logger.info("Sending message with subject=%s, to=%s", subject, to)

        # Create message
        raw_message = cls._create_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            reply_to_message_id=reply_to_message_id
        )

        with gmail_service() as service:
            try:
                send_result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message, 'threadId': thread_id}
                ).execute()

                logger.info("Message sent successfully with ID: %s", send_result.get('id'))
                return cls.get_email(send_result['id'])

            except Exception as e:
                logger.error("Error sending message: %s", e)
                raise

    @classmethod
    def batch_get_emails(cls, message_ids: List[str]) -> List["EmailMessage"]:
        """
        Retrieves multiple emails.
        
        Args:
            message_ids: List of message IDs to retrieve
            
        Returns:
            List of EmailMessage objects
        """
        logger.info("Batch retrieving %d messages", len(message_ids))
        
        email_messages = []
        for message_id in message_ids:
            try:
                email_messages.append(cls.get_email(message_id))
            except Exception as e:
                logger.warning("Failed to fetch message %s: %s", message_id, e)
                
        return email_messages

    @classmethod
    def batch_send_emails(cls, email_data_list: List[Dict[str, Any]]) -> List["EmailMessage"]:
        """
        Sends multiple emails.
        
        Args:
            email_data_list: List of dictionaries containing email parameters
            
        Returns:
            List of sent EmailMessage objects
        """
        logger.info("Batch sending %d emails", len(email_data_list))
        
        sent_messages = []
        for email_data in email_data_list:
            try:
                sent_messages.append(cls.send_email(**email_data))
            except Exception as e:
                logger.warning("Failed to send email: %s", e)
                
        return sent_messages

    def reply(
            self,
            body_text: Optional[str] = None,
            body_html: Optional[str] = None,
            attachments: Optional[List[str]] = None
    ) -> Self:
        """
        Sends a reply to the current email message.
        Args:
            body_text: Plain text body of the email.
            body_html: HTML body of the email.
            attachments: List of file paths to attach (optional).
        Returns:
            An EmailMessage object representing the message sent.
        """
        if self.is_from('me'):
            to = self.get_recipient_emails()
        else:
            to = [self.sender.email]

        logger.info("Replying to message %s", self.message_id)
        return EmailMessage.send_email(
            to=to,
            subject=self.subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            reply_to_message_id=self.reply_to_id,
            thread_id=self.thread_id
        )

    def mark_as_read(self) -> bool:
        """
        Marks a message as read by removing the UNREAD label.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as read: %s", self.message_id)
        
        with gmail_service() as service:
            try:
                service.users().messages().modify(
                    userId='me',
                    id=self.message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                self.is_read = True
                logger.info("Message marked as read successfully")
                return True
            except Exception as e:
                logger.error("Error marking message as read: %s", e)
                return False

    def mark_as_unread(self) -> bool:
        """
        Marks a message as unread by adding the UNREAD label.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Marking message as unread: %s", self.message_id)
        
        with gmail_service() as service:
            try:
                service.users().messages().modify(
                    userId='me',
                    id=self.message_id,
                    body={'addLabelIds': ['UNREAD']}
                ).execute()
                self.is_read = False
                logger.info("Message marked as unread successfully")
                return True
            except Exception as e:
                logger.error("Error marking message as unread: %s", e)
                return False

    def add_label(self, label_ids: List[str]) -> bool:
        """
        Adds labels to a message.

        Args:
            label_ids: List of label IDs to add.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Adding labels %s to message: %s", label_ids, self.message_id)
        
        with gmail_service() as service:
            try:
                service.users().messages().modify(
                    userId='me',
                    id=self.message_id,
                    body={'addLabelIds': label_ids}
                ).execute()
                # Update local state
                for label_id in label_ids:
                    if label_id not in self.label_ids:
                        self.label_ids.append(label_id)
                logger.info("Labels added successfully")
                return True
            except Exception as e:
                logger.error("Error adding labels: %s", e)
                return False

    def remove_label(self, label_ids: List[str]) -> bool:
        """
        Removes labels from a message.

        Args:
            label_ids: List of label IDs to remove.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Removing labels %s from message: %s", label_ids, self.message_id)
        
        with gmail_service() as service:
            try:
                service.users().messages().modify(
                    userId='me',
                    id=self.message_id,
                    body={'removeLabelIds': label_ids}
                ).execute()
                # Update local state
                for label_id in label_ids:
                    if label_id in self.label_ids:
                        self.label_ids.remove(label_id)
                logger.info("Labels removed successfully")
                return True
            except Exception as e:
                logger.error("Error removing labels: %s", e)
                return False

    def delete_email(self, permanent: bool = False) -> bool:
        """
        Deletes a message (moves to trash or permanently deletes).

        Args:
            permanent: If True, permanently deletes the message. If False, moves to trash.

        Returns:
            True if the operation was successful, False otherwise.
        """
        logger.info("Deleting message: %s, permanent=%s", self.message_id, permanent)
        
        with gmail_service() as service:
            try:
                if permanent:
                    service.users().messages().delete(userId='me', id=self.message_id).execute()
                    logger.info("Message permanently deleted")
                else:
                    service.users().messages().trash(userId='me', id=self.message_id).execute()
                    logger.info("Message moved to trash")
                return True
            except Exception as e:
                logger.error("Error deleting message: %s", e)
                return False

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
            return 'SENT' in self.label_ids

        return self.sender and self.sender.email.lower() == email.lower()

    def has_label(self, label: str) -> bool:
        """
        Checks if the message has a specific label.
        Args:
            label: The label to check for.

        Returns:
            True if the message has the label, False otherwise.
        """
        return label in self.label_ids

    def __repr__(self):
        return (
            f"Subject: {self.subject!r}\n"
            f"From: {self.sender}\n"
            f"To: {', '.join(str(r) for r in self.recipients)}\n"
            f"Date: {convert_datetime_to_readable(self.date_time) if self.date_time else 'Unknown'}\n"
            f"Snippet: {self.snippet}\n"
            f"Labels: {', '.join(self.label_ids)}\n"
        )
