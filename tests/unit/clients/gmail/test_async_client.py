import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.gmail.async_client import (
    AsyncEmailMessage, AsyncEmailAddress, AsyncEmailAttachment, AsyncLabel,
    AsyncGmailError, AsyncGmailPermissionError, AsyncEmailNotFoundError
)


@pytest.mark.unit
@pytest.mark.gmail
class TestAsyncEmailAddress:
    """Test cases for the AsyncEmailAddress class."""
    
    def test_valid_email_creation(self):
        """Test creating a valid async email address."""
        email_addr = AsyncEmailAddress(
            email="john@example.com",
            name="John Doe"
        )
        assert email_addr.email == "john@example.com"
        assert email_addr.name == "John Doe"
    
    def test_email_minimal_creation(self):
        """Test creating email address with only email."""
        email_addr = AsyncEmailAddress(email="john@example.com")
        assert email_addr.email == "john@example.com"
        assert email_addr.name is None
    
    def test_invalid_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email address cannot be empty"):
            AsyncEmailAddress(email="")
    
    def test_invalid_email_format(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            AsyncEmailAddress(email="invalid-email")
    
    def test_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "user@domain.com",
            "user.name@domain.co.uk",
            "user+tag@domain.org",
            "user123@sub.domain.net"
        ]
        for email in valid_emails:
            email_addr = AsyncEmailAddress(email=email)
            assert email_addr.email == email
    
    def test_to_dict(self):
        """Test converting AsyncEmailAddress to dictionary."""
        email_addr = AsyncEmailAddress(email="john@example.com", name="John Doe")
        result = email_addr.to_dict()
        
        expected = {
            "email": "john@example.com",
            "name": "John Doe"
        }
        assert result == expected
    
    def test_str_representation(self):
        """Test string representation of AsyncEmailAddress."""
        email_addr = AsyncEmailAddress(email="john@example.com", name="John Doe")
        assert str(email_addr) == "John Doe <john@example.com>"
        
        email_addr_no_name = AsyncEmailAddress(email="john@example.com")
        assert str(email_addr_no_name) == "john@example.com"


class TestAsyncEmailAttachment:
    """Test cases for the AsyncEmailAttachment class."""
    
    def test_valid_attachment_creation(self):
        """Test creating a valid async email attachment."""
        attachment = AsyncEmailAttachment(
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
            AsyncEmailAttachment(
                filename="",
                content_type="application/pdf",
                size=1024,
                attachment_id="att_123",
                message_id="msg_456"
            )
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_get_attachment_data(self, mock_context):
        """Test getting attachment data asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock API response
        mock_attachment_response = {
            'data': 'VGVzdCBkYXRh'  # Base64 encoded "Test data"
        }
        mock_aiogoogle.as_user.return_value = mock_attachment_response
        
        attachment = AsyncEmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=9,
            attachment_id="att_123",
            message_id="msg_456"
        )
        
        result = await attachment._get_attachment_data()
        assert b"Test data" in result
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
        call_args = mock_aiogoogle.as_user.call_args[0][0]
        assert hasattr(call_args, 'users')
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_load_data(self, mock_context):
        """Test loading attachment data."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        mock_attachment_response = {
            'data': 'VGVzdCBkYXRh'  # Base64 encoded "Test data"
        }
        mock_aiogoogle.as_user.return_value = mock_attachment_response
        
        attachment = AsyncEmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=9,
            attachment_id="att_123",
            message_id="msg_456"
        )
        
        result = await attachment.load_data()
        assert result is True
        assert attachment.data is not None
        assert b"Test data" in attachment.data


class TestAsyncLabel:
    """Test cases for the AsyncLabel class."""
    
    def test_valid_label_creation(self):
        """Test creating a valid async label."""
        label = AsyncLabel(
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
            AsyncLabel(id="", name="Important", type="user")
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_list_labels(self, mock_context):
        """Test listing labels asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock API response
        mock_labels_response = {
            'labels': [
                {'id': 'INBOX', 'name': 'INBOX', 'type': 'system'},
                {'id': 'SENT', 'name': 'SENT', 'type': 'system'},
                {'id': 'label_123', 'name': 'Important', 'type': 'user'}
            ]
        }
        mock_aiogoogle.as_user.return_value = mock_labels_response
        
        labels = await AsyncLabel.list_labels()
        
        assert len(labels) == 3
        assert labels[0].id == 'INBOX'
        assert labels[0].name == 'INBOX'
        assert labels[0].type == 'system'
        assert labels[2].id == 'label_123'
        assert labels[2].name == 'Important'
        assert labels[2].type == 'user'
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_create_label(self, mock_context):
        """Test creating a label asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock API response
        mock_create_response = {
            'id': 'label_new',
            'name': 'My Custom Label',
            'type': 'user'
        }
        mock_aiogoogle.as_user.return_value = mock_create_response
        
        label = await AsyncLabel.create_label("My Custom Label")
        
        assert label.id == 'label_new'
        assert label.name == 'My Custom Label'
        assert label.type == 'user'
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
        call_args = mock_aiogoogle.as_user.call_args[0][0]
        assert hasattr(call_args, 'users')
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_delete_label(self, mock_context):
        """Test deleting a label asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        label = AsyncLabel(id="label_123", name="To Delete", type="user")
        result = await label.delete_label()
        
        assert result is True
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    def test_repr(self):
        """Test string representation of AsyncLabel."""
        label = AsyncLabel(id="label_123", name="Important", type="user")
        expected = "AsyncLabel(id=label_123, name=Important, type=user)"
        assert repr(label) == expected


class TestAsyncEmailMessage:
    """Test cases for the AsyncEmailMessage class."""
    
    def test_valid_email_creation(self):
        """Test creating a valid async email message."""
        sender = AsyncEmailAddress(email="sender@example.com", name="Sender")
        recipient = AsyncEmailAddress(email="recipient@example.com", name="Recipient")
        
        email = AsyncEmailMessage(
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
        email = AsyncEmailMessage()
        
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
        email = AsyncEmailMessage(subject="Valid subject")
        assert email.subject == "Valid subject"
        
        # Invalid subject - too long
        long_subject = "x" * 1000  # Exceeds MAX_SUBJECT_LENGTH (998)
        with pytest.raises(ValueError, match="Email subject cannot exceed"):
            AsyncEmailMessage(subject=long_subject)
    
    def test_get_plain_text_content_from_text(self):
        """Test getting plain text content from text body."""
        email = AsyncEmailMessage(body_text="Plain text content")
        result = email.get_plain_text_content()
        assert result == "Plain text content"
    
    def test_get_plain_text_content_from_html(self):
        """Test getting plain text content from HTML body."""
        email = AsyncEmailMessage(body_html="<p>HTML content</p>")
        result = email.get_plain_text_content()
        # html2text conversion - exact result may vary but should contain the text
        assert "HTML content" in result
    
    def test_has_attachments(self):
        """Test checking if email has attachments."""
        # No attachments
        email = AsyncEmailMessage()
        assert email.has_attachments() is False
        
        # With attachments
        attachment = AsyncEmailAttachment(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            attachment_id="att_123",
            message_id="msg_456"
        )
        email_with_attachment = AsyncEmailMessage(attachments=[attachment])
        assert email_with_attachment.has_attachments() is True
    
    def test_get_recipient_emails(self):
        """Test getting recipient email addresses."""
        recipients = [
            AsyncEmailAddress(email="user1@example.com", name="User 1"),
            AsyncEmailAddress(email="user2@example.com", name="User 2")
        ]
        email = AsyncEmailMessage(recipients=recipients)
        
        result = email.get_recipient_emails()
        assert result == ["user1@example.com", "user2@example.com"]
    
    def test_is_from_email(self):
        """Test checking if email is from specific sender."""
        sender = AsyncEmailAddress(email="sender@example.com")
        email = AsyncEmailMessage(sender=sender)
        
        assert email.is_from("sender@example.com") is True
        assert email.is_from("SENDER@EXAMPLE.COM") is True  # Case insensitive
        assert email.is_from("other@example.com") is False
    
    def test_is_from_me(self):
        """Test checking if email is from authenticated user."""
        # Email from me (has SENT label)
        email_from_me = AsyncEmailMessage(label_ids=["SENT", "INBOX"])
        assert email_from_me.is_from("me") is True
        
        # Email not from me (no SENT label)
        email_not_from_me = AsyncEmailMessage(label_ids=["INBOX"])
        assert email_not_from_me.is_from("me") is False
    
    def test_has_label(self):
        """Test checking if email has specific label."""
        email = AsyncEmailMessage(label_ids=["INBOX", "IMPORTANT", "STARRED"])
        
        assert email.has_label("INBOX") is True
        assert email.has_label("IMPORTANT") is True
        assert email.has_label("DRAFT") is False
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_list_emails(self, mock_context, sample_gmail_message):
        """Test listing emails asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock API responses
        mock_list_response = {
            'messages': [
                {'id': 'msg_123'},
                {'id': 'msg_456'}
            ]
        }
        mock_aiogoogle.as_user.return_value = mock_list_response
        
        # Mock the get_email method to avoid deep mocking
        with patch.object(AsyncEmailMessage, 'get_email') as mock_get_email:
            mock_email = Mock(spec=AsyncEmailMessage)
            mock_get_email.return_value = mock_email
            
            emails = await AsyncEmailMessage.list_emails(max_results=10)
            
            assert len(emails) == 2
            assert mock_get_email.call_count == 2
            mock_get_email.assert_any_call('msg_123')
            mock_get_email.assert_any_call('msg_456')
        
        # Verify list API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_get_email(self, mock_context, sample_gmail_message):
        """Test getting a specific email asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        mock_aiogoogle.as_user.return_value = sample_gmail_message
        
        email = await AsyncEmailMessage.get_email("msg_123")
        
        assert isinstance(email, AsyncEmailMessage)
        assert email.message_id == "msg_123"
        assert email.subject == "Test Email Subject"
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_send_email(self, mock_context):
        """Test sending an email asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock send response
        mock_send_response = {'id': 'msg_sent_123'}
        mock_aiogoogle.as_user.return_value = mock_send_response
        
        # Mock get_email for the sent message
        with patch.object(AsyncEmailMessage, 'get_email') as mock_get_email:
            mock_sent_email = Mock(spec=AsyncEmailMessage)
            mock_get_email.return_value = mock_sent_email
            
            result = await AsyncEmailMessage.send_email(
                to=["recipient@example.com"],
                subject="Test Subject",
                body_text="Test body"
            )
            
            assert result == mock_sent_email
            mock_get_email.assert_called_once_with('msg_sent_123')
        
        # Verify send API was called
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_mark_as_read(self, mock_context):
        """Test marking email as read asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        email = AsyncEmailMessage(message_id="msg_123", is_read=False)
        result = await email.mark_as_read()
        
        assert result is True
        assert email.is_read is True
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_add_label(self, mock_context):
        """Test adding labels to email asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        email = AsyncEmailMessage(message_id="msg_123", label_ids=["INBOX"])
        result = await email.add_label(["IMPORTANT", "STARRED"])
        
        assert result is True
        assert "IMPORTANT" in email.label_ids
        assert "STARRED" in email.label_ids
        
        # Verify API was called correctly
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_batch_get_emails(self, mock_context, sample_gmail_message):
        """Test batch getting emails asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock get_email method
        with patch.object(AsyncEmailMessage, 'get_email') as mock_get_email:
            mock_email1 = Mock(spec=AsyncEmailMessage)
            mock_email1.message_id = "msg_123"
            mock_email2 = Mock(spec=AsyncEmailMessage)
            mock_email2.message_id = "msg_456"
            
            mock_get_email.side_effect = [mock_email1, mock_email2]
            
            result = await AsyncEmailMessage.batch_get_emails(["msg_123", "msg_456"])
            
            assert len(result) == 2
            assert result[0].message_id == "msg_123"
            assert result[1].message_id == "msg_456"
            assert mock_get_email.call_count == 2
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_batch_send_emails(self, mock_context):
        """Test batch sending emails asynchronously."""
        # Setup mock async context manager  
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock send_email method
        with patch.object(AsyncEmailMessage, 'send_email') as mock_send_email:
            mock_email1 = Mock(spec=AsyncEmailMessage)
            mock_email1.message_id = "msg_sent_123"
            mock_email2 = Mock(spec=AsyncEmailMessage)
            mock_email2.message_id = "msg_sent_456"
            
            mock_send_email.side_effect = [mock_email1, mock_email2]
            
            email_data_list = [
                {"to": ["user1@example.com"], "subject": "Subject 1", "body_text": "Body 1"},
                {"to": ["user2@example.com"], "subject": "Subject 2", "body_text": "Body 2"}
            ]
            
            result = await AsyncEmailMessage.batch_send_emails(email_data_list)
            
            assert len(result) == 2
            assert result[0].message_id == "msg_sent_123"
            assert result[1].message_id == "msg_sent_456"
            assert mock_send_email.call_count == 2
    
    def test_repr(self):
        """Test string representation of AsyncEmailMessage."""
        sender = AsyncEmailAddress(email="sender@example.com", name="Sender")
        recipient = AsyncEmailAddress(email="recipient@example.com", name="Recipient")
        
        email = AsyncEmailMessage(
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