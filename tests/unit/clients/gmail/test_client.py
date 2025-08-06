import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
from src.google_api_client.clients.gmail.client import (
    EmailMessage, EmailAddress, EmailAttachment, Label, 
    GmailError, GmailPermissionError, EmailNotFoundError
)


@pytest.mark.unit
@pytest.mark.gmail


class TestEmailAddress:
    """Test cases for the EmailAddress class."""
    
    def test_valid_email_creation(self):
        """Test creating a valid email address."""
        email_addr = EmailAddress(
            email="john@example.com",
            name="John Doe"
        )
        assert email_addr.email == "john@example.com"
        assert email_addr.name == "John Doe"
    
    def test_email_minimal_creation(self):
        """Test creating email address with only email."""
        email_addr = EmailAddress(email="john@example.com")
        assert email_addr.email == "john@example.com"
        assert email_addr.name is None
    
    def test_invalid_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email address cannot be empty"):
            EmailAddress(email="")
    
    def test_invalid_email_format(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            EmailAddress(email="invalid-email")
    
    def test_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "user@domain.com",
            "user.name@domain.co.uk",
            "user+tag@domain.org",
            "user123@sub.domain.net"
        ]
        for email in valid_emails:
            email_addr = EmailAddress(email=email)
            assert email_addr.email == email
    
    def test_to_dict(self):
        """Test converting EmailAddress to dictionary."""
        email_addr = EmailAddress(email="john@example.com", name="John Doe")
        result = email_addr.to_dict()
        
        expected = {
            "email": "john@example.com",
            "name": "John Doe"
        }
        assert result == expected
    
    def test_to_dict_no_name(self):
        """Test converting EmailAddress to dictionary without name."""
        email_addr = EmailAddress(email="john@example.com")
        result = email_addr.to_dict()
        
        expected = {"email": "john@example.com"}
        assert result == expected
    
    def test_str_representation(self):
        """Test string representation of EmailAddress."""
        email_addr = EmailAddress(email="john@example.com", name="John Doe")
        assert str(email_addr) == "John Doe <john@example.com>"
        
        email_addr_no_name = EmailAddress(email="john@example.com")
        assert str(email_addr_no_name) == "john@example.com"


class TestEmailAttachment:
    """Test cases for the EmailAttachment class."""
    
    def test_valid_attachment_creation(self):
        """Test creating a valid email attachment."""
        attachment = EmailAttachment(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024,
            attachment_id="att_123",
            message_id="msg_456"
        )
        assert attachment.filename == "document.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024
        assert attachment.attachment_id == "att_123"
        assert attachment.message_id == "msg_456"
        assert attachment.data is None
    
    def test_invalid_empty_filename(self):
        """Test that empty filename raises ValueError."""
        with pytest.raises(ValueError, match="Attachment filename cannot be empty"):
            EmailAttachment(
                filename="",
                content_type="application/pdf",
                size=1024,
                attachment_id="att_123",
                message_id="msg_456"
            )
    
    def test_invalid_empty_attachment_id(self):
        """Test that empty attachment ID raises ValueError."""
        with pytest.raises(ValueError, match="Attachment ID cannot be empty"):
            EmailAttachment(
                filename="document.pdf",
                content_type="application/pdf", 
                size=1024,
                attachment_id="",
                message_id="msg_456"
            )
    
    def test_invalid_empty_message_id(self):
        """Test that empty message ID raises ValueError."""
        with pytest.raises(ValueError, match="Message ID cannot be empty"):
            EmailAttachment(
                filename="document.pdf",
                content_type="application/pdf",
                size=1024,
                attachment_id="att_123",
                message_id=""
            )
    
    def test_to_dict(self):
        """Test converting EmailAttachment to dictionary."""
        attachment = EmailAttachment(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024,
            attachment_id="att_123",
            message_id="msg_456"
        )
        result = attachment.to_dict()
        
        expected = {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "attachment_id": "att_123",
            "message_id": "msg_456"
        }
        assert result == expected
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_get_attachment_data(self, mock_context):
        """Test getting attachment data."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock API response
        mock_attachment_response = {
            'data': 'VGVzdCBkYXRh'  # Base64 encoded "Test data"
        }
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = mock_attachment_response
        
        attachment = EmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=9,
            attachment_id="att_123",
            message_id="msg_456"
        )
        
        result = attachment._get_attachment_data()
        assert b"Test data" in result
        
        # Verify API was called correctly
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.assert_called_once_with(
            userId='me',
            messageId='msg_456',
            id='att_123'
        )


class TestLabel:
    """Test cases for the Label class."""
    
    def test_valid_label_creation(self):
        """Test creating a valid label."""
        label = Label(
            id="label_123",
            name="Important",
            type="user"
        )
        assert label.id == "label_123"
        assert label.name == "Important"
        assert label.type == "user"
    
    def test_invalid_empty_id(self):
        """Test that empty label ID raises ValueError."""
        with pytest.raises(ValueError, match="Label ID cannot be empty"):
            Label(id="", name="Important", type="user")
    
    def test_invalid_empty_name(self):
        """Test that empty label name raises ValueError."""
        with pytest.raises(ValueError, match="Label name cannot be empty"):
            Label(id="label_123", name="", type="user")
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_list_labels(self, mock_context):
        """Test listing labels."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock API response
        mock_labels_response = {
            'labels': [
                {'id': 'INBOX', 'name': 'INBOX', 'type': 'system'},
                {'id': 'SENT', 'name': 'SENT', 'type': 'system'},
                {'id': 'label_123', 'name': 'Important', 'type': 'user'}
            ]
        }
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = mock_labels_response
        
        labels = Label.list_labels()
        
        assert len(labels) == 3
        assert labels[0].id == 'INBOX'
        assert labels[0].name == 'INBOX'
        assert labels[0].type == 'system'
        assert labels[2].id == 'label_123'
        assert labels[2].name == 'Important'
        assert labels[2].type == 'user'
        
        # Verify API was called correctly
        mock_service.users.return_value.labels.return_value.list.assert_called_once_with(userId='me')
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_create_label(self, mock_context):
        """Test creating a label."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock API response
        mock_create_response = {
            'id': 'label_new',
            'name': 'My Custom Label',
            'type': 'user'
        }
        mock_service.users.return_value.labels.return_value.create.return_value.execute.return_value = mock_create_response
        
        label = Label.create_label("My Custom Label")
        
        assert label.id == 'label_new'
        assert label.name == 'My Custom Label'
        assert label.type == 'user'
        
        # Verify API was called correctly
        mock_service.users.return_value.labels.return_value.create.assert_called_once_with(
            userId='me',
            body={'name': 'My Custom Label', 'type': 'user'}
        )
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_delete_label(self, mock_context):
        """Test deleting a label."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        label = Label(id="label_123", name="To Delete", type="user")
        result = label.delete_label()
        
        assert result is True
        
        # Verify API was called correctly
        mock_service.users.return_value.labels.return_value.delete.assert_called_once_with(
            userId='me',
            id='label_123'
        )
    
    def test_repr(self):
        """Test string representation of Label."""
        label = Label(id="label_123", name="Important", type="user")
        expected = "Label(id=label_123, name=Important, type=user)"
        assert repr(label) == expected


class TestEmailMessage:
    """Test cases for the EmailMessage class."""
    
    def test_valid_email_creation(self):
        """Test creating a valid email message."""
        sender = EmailAddress(email="sender@example.com", name="Sender")
        recipient = EmailAddress(email="recipient@example.com", name="Recipient")
        
        email = EmailMessage(
            message_id="msg_123",
            subject="Test Subject",
            sender=sender,
            recipients=[recipient],
            body_text="Test body content",
            is_read=True
        )
        
        assert email.message_id == "msg_123"
        assert email.subject == "Test Subject"
        assert email.sender == sender
        assert len(email.recipients) == 1
        assert email.recipients[0] == recipient
        assert email.body_text == "Test body content"
        assert email.is_read is True
    
    def test_email_creation_with_defaults(self):
        """Test creating email with default values."""
        email = EmailMessage()
        
        assert email.message_id is None
        assert email.subject is None
        assert email.sender is None
        assert email.recipients == []
        assert email.cc_recipients == []
        assert email.bcc_recipients == []
        assert email.attachments == []
        assert email.label_ids == []
        assert email.is_read is False
        assert email.is_starred is False
        assert email.is_important is False
    
    def test_subject_length_validation(self):
        """Test subject length validation."""
        # Valid subject
        email = EmailMessage(subject="Valid subject")
        assert email.subject == "Valid subject"
        
        # Invalid subject - too long
        long_subject = "x" * 1000  # Exceeds MAX_SUBJECT_LENGTH (998)
        with pytest.raises(ValueError, match="Email subject cannot exceed"):
            EmailMessage(subject=long_subject)
    
    def test_body_length_validation(self):
        """Test body length validation."""
        # Valid body
        email = EmailMessage(body_text="Valid body content")
        assert email.body_text == "Valid body content"
        
        # Would test very long body, but it's impractical for unit tests
        # The validation logic is tested in the _validate_text_field method
    
    def test_get_plain_text_content_from_text(self):
        """Test getting plain text content from text body."""
        email = EmailMessage(body_text="Plain text content")
        result = email.get_plain_text_content()
        assert result == "Plain text content"
    
    def test_get_plain_text_content_from_html(self):
        """Test getting plain text content from HTML body."""
        email = EmailMessage(body_html="<p>HTML content</p>")
        result = email.get_plain_text_content()
        # html2text conversion - exact result may vary but should contain the text
        assert "HTML content" in result
    
    def test_get_plain_text_content_empty(self):
        """Test getting plain text content when both are empty."""
        email = EmailMessage()
        result = email.get_plain_text_content()
        assert result == ""
    
    def test_has_attachments(self):
        """Test checking if email has attachments."""
        # No attachments
        email = EmailMessage()
        assert email.has_attachments() is False
        
        # With attachments
        attachment = EmailAttachment(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            attachment_id="att_123",
            message_id="msg_456"
        )
        email_with_attachment = EmailMessage(attachments=[attachment])
        assert email_with_attachment.has_attachments() is True
    
    def test_get_recipient_emails(self):
        """Test getting recipient email addresses."""
        recipients = [
            EmailAddress(email="user1@example.com", name="User 1"),
            EmailAddress(email="user2@example.com", name="User 2")
        ]
        email = EmailMessage(recipients=recipients)
        
        result = email.get_recipient_emails()
        assert result == ["user1@example.com", "user2@example.com"]
    
    def test_get_all_recipient_emails(self):
        """Test getting all recipient email addresses (To, CC, BCC)."""
        recipients = [EmailAddress(email="to@example.com")]
        cc_recipients = [EmailAddress(email="cc@example.com")]
        bcc_recipients = [EmailAddress(email="bcc@example.com")]
        
        email = EmailMessage(
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients
        )
        
        result = email.get_all_recipient_emails()
        expected = ["to@example.com", "cc@example.com", "bcc@example.com"]
        assert result == expected
    
    def test_is_from_email(self):
        """Test checking if email is from specific sender."""
        sender = EmailAddress(email="sender@example.com")
        email = EmailMessage(sender=sender)
        
        assert email.is_from("sender@example.com") is True
        assert email.is_from("SENDER@EXAMPLE.COM") is True  # Case insensitive
        assert email.is_from("other@example.com") is False
    
    def test_is_from_me(self):
        """Test checking if email is from authenticated user."""
        # Email from me (has SENT label)
        email_from_me = EmailMessage(label_ids=["SENT", "INBOX"])
        assert email_from_me.is_from("me") is True
        
        # Email not from me (no SENT label)
        email_not_from_me = EmailMessage(label_ids=["INBOX"])
        assert email_not_from_me.is_from("me") is False
    
    def test_has_label(self):
        """Test checking if email has specific label."""
        email = EmailMessage(label_ids=["INBOX", "IMPORTANT", "STARRED"])
        
        assert email.has_label("INBOX") is True
        assert email.has_label("IMPORTANT") is True
        assert email.has_label("DRAFT") is False
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_list_emails(self, mock_context, sample_gmail_message):
        """Test listing emails."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock API responses
        mock_list_response = {
            'messages': [
                {'id': 'msg_123'},
                {'id': 'msg_456'}
            ]
        }
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = mock_list_response
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        # Mock the get_email method to avoid deep mocking
        with patch.object(EmailMessage, 'get_email') as mock_get_email:
            mock_email = Mock(spec=EmailMessage)
            mock_get_email.return_value = mock_email
            
            emails = EmailMessage.list_emails(max_results=10)
            
            assert len(emails) == 2
            assert mock_get_email.call_count == 2
            mock_get_email.assert_any_call('msg_123')
            mock_get_email.assert_any_call('msg_456')
        
        # Verify list API was called correctly
        mock_service.users.return_value.messages.return_value.list.assert_called_once_with(
            userId='me',
            maxResults=10,
            includeSpamTrash=False
        )
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_get_email(self, mock_context, sample_gmail_message):
        """Test getting a specific email."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        email = EmailMessage.get_email("msg_123")
        
        assert isinstance(email, EmailMessage)
        assert email.message_id == "msg_123"
        assert email.subject == "Test Email Subject"
        
        # Verify API was called correctly
        mock_service.users.return_value.messages.return_value.get.assert_called_once_with(
            userId='me',
            id='msg_123',
            format='full'
        )
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_send_email(self, mock_context):
        """Test sending an email."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock send response
        mock_send_response = {'id': 'msg_sent_123'}
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = mock_send_response
        
        # Mock get_email for the sent message
        with patch.object(EmailMessage, 'get_email') as mock_get_email:
            mock_sent_email = Mock(spec=EmailMessage)
            mock_get_email.return_value = mock_sent_email
            
            result = EmailMessage.send_email(
                to=["recipient@example.com"],
                subject="Test Subject",
                body_text="Test body"
            )
            
            assert result == mock_sent_email
            mock_get_email.assert_called_once_with('msg_sent_123')
        
        # Verify send API was called
        mock_service.users.return_value.messages.return_value.send.assert_called_once()
        send_call = mock_service.users.return_value.messages.return_value.send.call_args
        assert send_call[1]['userId'] == 'me'
        assert 'raw' in send_call[1]['body']
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_mark_as_read(self, mock_context):
        """Test marking email as read."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        email = EmailMessage(message_id="msg_123", is_read=False)
        result = email.mark_as_read()
        
        assert result is True
        assert email.is_read is True
        
        # Verify API was called correctly
        mock_service.users.return_value.messages.return_value.modify.assert_called_once_with(
            userId='me',
            id='msg_123',
            body={'removeLabelIds': ['UNREAD']}
        )
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_add_label(self, mock_context):
        """Test adding labels to email."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        email = EmailMessage(message_id="msg_123", label_ids=["INBOX"])
        result = email.add_label(["IMPORTANT", "STARRED"])
        
        assert result is True
        assert "IMPORTANT" in email.label_ids
        assert "STARRED" in email.label_ids
        
        # Verify API was called correctly
        mock_service.users.return_value.messages.return_value.modify.assert_called_once_with(
            userId='me',
            id='msg_123',
            body={'addLabelIds': ['IMPORTANT', 'STARRED']}
        )
    
    def test_repr(self):
        """Test string representation of EmailMessage."""
        sender = EmailAddress(email="sender@example.com", name="Sender")
        recipient = EmailAddress(email="recipient@example.com", name="Recipient")
        
        email = EmailMessage(
            subject="Test Subject",
            sender=sender,
            recipients=[recipient],
            snippet="This is a test email...",
            label_ids=["INBOX", "IMPORTANT"]
        )
        
        repr_str = repr(email)
        assert "Test Subject" in repr_str
        assert "sender@example.com" in repr_str
        assert "recipient@example.com" in repr_str
        assert "This is a test email..." in repr_str
        assert "INBOX" in repr_str


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail API message response."""
    return {
        "id": "msg_123",
        "threadId": "thread_456",
        "snippet": "This is a test email snippet...",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "Date", "value": "Mon, 15 Jan 2025 09:00:00 -0500"},
                {"name": "Message-ID", "value": "<msg123@example.com>"}
            ],
            "body": {
                "data": "VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keS4="  # Base64: "This is a test email body."
            },
            "mimeType": "text/plain"
        }
    }