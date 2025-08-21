import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import getaddresses, parsedate_to_datetime
import mimetypes
import html
from typing import Optional, List
import base64
from .types import EmailMessage, EmailAttachment, EmailAddress, EmailThread
from ...utils.datetime import convert_datetime_to_local_timezone, convert_datetime_to_readable
from .constants import MAX_SUBJECT_LENGTH, MAX_BODY_LENGTH


# Import from shared utilities
from ...utils.validation import is_valid_email, sanitize_header_value


def extract_body(payload: dict) -> tuple[Optional[str], Optional[str]]:
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


def extract_attachments(message_id: str, payload: dict) -> List[EmailAttachment]:
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
                        mime_type=part.get('mimeType', 'application/octet-stream'),
                        size=part.get('body', {}).get('size', 0),
                        attachment_id=part['body']['attachmentId'],
                        message_id=message_id
                    )
                    attachments.append(attachment)
                except ValueError:
                    pass
            elif part.get('parts'):
                extract_from_parts(part['parts'])

    if payload.get('parts'):
        extract_from_parts(payload['parts'])

    return attachments


def from_gmail_message(gmail_message: dict) -> "EmailMessage":
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
            if email and is_valid_email(email):
                try:
                    addresses.append(EmailAddress(email=email, name=name if name else None))
                except ValueError:
                    pass
        return addresses

    sender = None
    if headers.get('from'):
        sender_list = parse_email_addresses(headers['from'])
        sender = sender_list[0] if sender_list else None

    recipients = parse_email_addresses(headers.get('to', ''))
    cc_recipients = parse_email_addresses(headers.get('cc', ''))
    bcc_recipients = parse_email_addresses(headers.get('bcc', ''))

    # Extract body
    body_text, body_html = extract_body(payload)

    # Extract attachments
    message_id = gmail_message.get('id')
    attachments = extract_attachments(message_id, payload)

    # Parse date
    date_received = None
    if headers.get('date'):
        try:
            # Parse RFC 2822 date format
            date_received = parsedate_to_datetime(headers['date'])
            date_received = convert_datetime_to_local_timezone(date_received)
        except:
            pass

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
        labels=labels,
        is_read=is_read,
        is_starred=is_starred,
        is_important=is_important,
        snippet=html.unescape(gmail_message.get('snippet')).strip(),
        reply_to_id=headers.get('message-id'),
        references=headers.get('references')
    )


def create_message(
        to: List[str],
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachment_paths: Optional[List[str]] = None,
        attachment_data_list: Optional[List[tuple]] = None,
        reply_to_message_id: Optional[str] = None,
        references: Optional[str] = None

) -> str:
    """
    Creates a MIMEText email message.

    Security: Attachment filenames are sanitized to prevent header injection attacks.
    Filenames containing control characters (CRLF, etc.) that could inject additional
    headers are automatically cleaned.

    Args:
        to: List of recipient email addresses.
        subject: The subject line of the email.
        body_text: Plain text body of the email (optional).
        body_html: HTML body of the email (optional).
        cc: List of CC recipient email addresses (optional).
        bcc: List of BCC recipient email addresses (optional).
        attachment_paths: List of file paths to attach (optional).
        attachment_data_list: List of tuples (filename, mime_type, data_bytes) for in-memory attachments (optional).
        reply_to_message_id: ID of message this is replying to (optional).
        references: List of references to attach (optional).

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

    # Create the message content (text and/or HTML)
    if body_html and body_text:
        # Both text and HTML - create alternative container
        content_part = MIMEMultipart('alternative')
        content_part.attach(MIMEText(body_text, 'plain'))
        content_part.attach(MIMEText(body_html, 'html'))
        message = content_part
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
    if attachment_paths or attachment_data_list:
        # Create mixed container for content + attachments
        content_message = message  # Save the content part
        message = MIMEMultipart('mixed')
        
        # Attach the content (text/HTML/alternative) as first part
        message.attach(content_message)
        
        # Set headers on the mixed container
        message['to'] = ', '.join(to)
        message['subject'] = subject
        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)

        # Add file attachments
        if attachment_paths:
            for file_path in attachment_paths:
                if os.path.isfile(file_path):
                    content_type, encoding = mimetypes.guess_type(file_path)
                    if content_type is None or encoding is not None:
                        content_type = 'application/octet-stream'

                    main_type, sub_type = content_type.split('/', 1)

                    with open(file_path, 'rb') as fp:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(fp.read())
                        encoders.encode_base64(attachment)
                        # Sanitize filename to prevent header injection
                        safe_filename = sanitize_header_value(os.path.basename(file_path))
                        attachment.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{safe_filename}"'
                        )
                        message.attach(attachment)
        
        # Add in-memory attachments
        if attachment_data_list:
            for filename, mime_type, data_bytes in attachment_data_list:
                
                main_type, sub_type = mime_type.split('/', 1) if '/' in mime_type else ('application', 'octet-stream')
                attachment = MIMEBase(main_type, sub_type)
                
                # data_bytes from get_attachment_payload is already raw binary data
                # so we need to encode it to base64
                attachment.set_payload(data_bytes)
                encoders.encode_base64(attachment)
                
                # Sanitize filename to prevent header injection
                safe_filename = sanitize_header_value(filename)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{safe_filename}"'
                )
                
                # Add Content-Type header explicitly
                attachment.add_header('Content-Type', mime_type)
                
                message.attach(attachment)
                

    # Add reply headers if this is a reply
    if reply_to_message_id:
        message['In-Reply-To'] = reply_to_message_id
        message['References'] = references or reply_to_message_id


    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return raw_message


def from_gmail_thread(gmail_thread: dict) -> EmailThread:
    """
    Creates an EmailThread instance from a Gmail API thread response.
    Args:
        gmail_thread: A dictionary containing thread data from Gmail API.

    Returns:
        An EmailThread instance populated with the data from the dictionary.
    """
    thread_id = gmail_thread.get('id')
    snippet = html.unescape(gmail_thread.get('snippet', '')).strip()
    history_id = gmail_thread.get('historyId')
    
    # Convert messages to EmailMessage objects
    messages = []
    for gmail_message in gmail_thread.get('messages', []):
        try:
            email_message = from_gmail_message(gmail_message)
            messages.append(email_message)
        except Exception:
            pass
    
    return EmailThread(
        thread_id=thread_id,
        messages=messages,
        snippet=snippet,
        history_id=history_id
    )


def build_references_header(email: EmailMessage) -> Optional[str]:
    """
    Builds a References header by appending the original message's Message-ID to existing references.
    
    Args:
        email: The email being replied to
        
    Returns:
        A properly formatted References header string or None
    """
    references_parts = []
    
    # Add existing references (already contains the proper thread chain)
    if email.references:
        references_parts.append(email.references.strip())
    
    # Add the original message's Message-ID to continue the chain
    if email.reply_to_id:
        references_parts.append(email.reply_to_id.strip())
    
    return " ".join(references_parts) if references_parts else None


def prepare_forward_body_text(email: EmailMessage) -> str:
    if email.body_text:
        forwarded_body_text = "\n".join([
            email.body_text,
            "\n\n---------- Forwarded message ---------",
            f"From: {email.sender}",
            f"Date: {convert_datetime_to_readable(email.date_time)}",
            f"Subject: {email.subject}",
            f"To: {", ".join([str(recipient) for recipient in email.recipients])}",
            ""
        ])
    else:
        forwarded_body_text = "\n".join([
            "\n\n---------- Forwarded message ---------",
            f"From: {email.sender}",
            f"Date: {convert_datetime_to_readable(email.date_time)}",
            f"Subject: {email.subject}",
            f"To: {", ".join([str(recipient) for recipient in email.recipients])}",
            ""
        ])

    return forwarded_body_text


def prepare_forward_body_html(email: EmailMessage) -> Optional[str]:
    """
    Prepares the HTML body for a forwarded email.
    """
    if not email.body_html:
        return None
        
    forward_content = ["---------- Forwarded message ---------<br>", f"<b>From:</b> {email.sender}<br>",
                       f"<b>Date:</b> {convert_datetime_to_readable(email.date_time)}<br>",
                       f"<b>Subject:</b> {email.subject}<br>"
                       ]

    if email.recipients:
        to_list = ", ".join([str(recipient) for recipient in email.recipients])
        forward_content.append(f"<b>To:</b> {to_list}<br>")
    
    forward_content.append("<br>")  # Empty line before original content
    
    # Add original message content
    if email.body_html:
        forward_content.append(email.body_html)
    elif email.body_text:
        # Convert plain text to HTML
        html_text = email.body_text.replace('\n', '<br>')
        forward_content.append(html_text)
    
    return "".join(forward_content)

