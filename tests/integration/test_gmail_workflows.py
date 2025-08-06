import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.gmail.client import EmailMessage, EmailAddress, Label
from src.google_api_client.clients.gmail.async_client import AsyncEmailMessage, AsyncEmailAddress, AsyncLabel


@pytest.mark.integration
@pytest.mark.gmail


@pytest.mark.integration
class TestGmailIntegration:
    """Integration tests for Gmail functionality with mocked API calls."""
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_end_to_end_email_lifecycle(self, mock_context, sample_gmail_message):
        """Test complete email lifecycle: send, read, label, delete."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock responses for different operations
        sent_email_response = {
            "id": "msg_sent_123",
            "threadId": "thread_456"
        }
        
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = sent_email_response
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        # Test: Send email
        sent_email = EmailMessage.send_email(
            to=["recipient@example.com"],
            subject="Integration Test Email",
            body_text="This is a test email for integration testing.",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )
        
        assert sent_email.message_id == "msg_123"  # From sample_gmail_message
        assert sent_email.subject == "Test Email Subject"
        mock_service.users.return_value.messages.return_value.send.assert_called_once()
        
        # Test: Get email
        retrieved_email = EmailMessage.get_email("msg_123")
        assert retrieved_email.message_id == "msg_123"
        assert retrieved_email.subject == "Test Email Subject"
        mock_service.users.return_value.messages.return_value.get.assert_called()
        
        # Test: Mark as read
        result = retrieved_email.mark_as_read()
        assert result is True
        assert retrieved_email.is_read is True
        mock_service.users.return_value.messages.return_value.modify.assert_called()
        
        # Test: Add label
        result = retrieved_email.add_label(["IMPORTANT"])
        assert result is True
        assert "IMPORTANT" in retrieved_email.label_ids
        
        # Test: Delete email
        result = retrieved_email.delete_email()
        assert result is True
        mock_service.users.return_value.messages.return_value.trash.assert_called_once()
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_label_management_workflow(self, mock_context):
        """Test complete label management workflow."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock responses
        created_label_response = {
            "id": "label_new_123",
            "name": "Integration Test Label",
            "type": "user"
        }
        
        updated_label_response = {
            "id": "label_new_123",
            "name": "Updated Integration Test Label",
            "type": "user"
        }
        
        labels_list_response = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "label_new_123", "name": "Updated Integration Test Label", "type": "user"}
            ]
        }
        
        mock_service.users.return_value.labels.return_value.create.return_value.execute.return_value = created_label_response
        mock_service.users.return_value.labels.return_value.patch.return_value.execute.return_value = updated_label_response
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = labels_list_response
        
        # Test: Create label
        new_label = Label.create_label("Integration Test Label")
        assert new_label.id == "label_new_123"
        assert new_label.name == "Integration Test Label"
        assert new_label.type == "user"
        mock_service.users.return_value.labels.return_value.create.assert_called_once()
        
        # Test: Update label
        updated_label = new_label.update_label("Updated Integration Test Label")
        assert updated_label.name == "Updated Integration Test Label"
        mock_service.users.return_value.labels.return_value.patch.assert_called_once()
        
        # Test: List labels
        labels = Label.list_labels()
        assert len(labels) == 2
        assert any(label.id == "label_new_123" for label in labels)
        mock_service.users.return_value.labels.return_value.list.assert_called_once()
        
        # Test: Delete label
        result = updated_label.delete_label()
        assert result is True
        mock_service.users.return_value.labels.return_value.delete.assert_called_once()
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_email_search_and_filtering_workflow(self, mock_context, sample_gmail_message):
        """Test complex email search and filtering workflow."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock search responses
        search_response = {
            "messages": [
                {"id": "msg_123"},
                {"id": "msg_456"},
                {"id": "msg_789"}
            ]
        }
        
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = search_response
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        # Test: Basic search using query builder
        emails = (EmailMessage.query()
                 .limit(50)
                 .from_sender("important@example.com")
                 .search("meeting")
                 .is_unread()
                 .with_attachments()
                 .execute())
        
        assert len(emails) == 3
        mock_service.users.return_value.messages.return_value.list.assert_called_once()
        list_call_args = mock_service.users.return_value.messages.return_value.list.call_args
        assert list_call_args[1]['maxResults'] == 50
        assert 'q' in list_call_args[1]
        query_string = list_call_args[1]['q']
        assert "from:important@example.com" in query_string
        assert "meeting" in query_string
        assert "is:unread" in query_string
        assert "has:attachment" in query_string
        
        # Test: Date-based filtering
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        
        # Reset mock for new call
        mock_service.reset_mock()
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = search_response
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        recent_emails = (EmailMessage.query()
                        .in_date_range(yesterday, today)
                        .is_starred()
                        .execute())
        
        assert len(recent_emails) == 3
        mock_service.users.return_value.messages.return_value.list.assert_called_once()
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_batch_operations_workflow(self, mock_context, sample_gmail_message):
        """Test batch operations workflow."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock responses
        send_response_1 = {"id": "msg_sent_123"}
        send_response_2 = {"id": "msg_sent_456"}
        
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = [
            send_response_1, send_response_2
        ]
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        # Test: Batch send emails
        email_data_list = [
            {
                "to": ["recipient1@example.com"],
                "subject": "Batch Email 1",
                "body_text": "This is batch email 1"
            },
            {
                "to": ["recipient2@example.com"],
                "subject": "Batch Email 2",
                "body_text": "This is batch email 2"
            }
        ]
        
        sent_emails = EmailMessage.batch_send_emails(email_data_list)
        
        assert len(sent_emails) == 2
        assert mock_service.users.return_value.messages.return_value.send.call_count == 2
        
        # Test: Batch get emails
        message_ids = ["msg_123", "msg_456", "msg_789"]
        
        # Reset mock for batch get
        mock_service.reset_mock()
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        
        retrieved_emails = EmailMessage.batch_get_emails(message_ids)
        
        assert len(retrieved_emails) == 3
        assert mock_service.users.return_value.messages.return_value.get.call_count == 3
    
    @patch('src.google_api_client.clients.gmail.client.gmail_service')
    def test_reply_workflow(self, mock_context, sample_gmail_message):
        """Test email reply workflow."""
        # Setup mock service
        mock_service = Mock()
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock responses
        reply_response = {"id": "msg_reply_123"}
        
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = sample_gmail_message
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = reply_response
        
        # Test: Get original email and reply
        original_email = EmailMessage.get_email("msg_123")
        assert original_email.sender.email == "sender@example.com"
        
        # Reply to the email
        reply_email = original_email.reply(
            body_text="Thank you for your email. This is my reply.",
            body_html="<p>Thank you for your email. This is my reply.</p>"
        )
        
        assert reply_email.message_id == "msg_123"  # From sample response
        mock_service.users.return_value.messages.return_value.send.assert_called_once()
        
        # Verify reply was sent to original sender
        send_call = mock_service.users.return_value.messages.return_value.send.call_args
        assert send_call[1]['userId'] == 'me'
        assert 'raw' in send_call[1]['body']


@pytest.mark.integration  
@pytest.mark.gmail
@pytest.mark.asyncio
class TestAsyncGmailIntegration:
    """Async integration tests for Gmail functionality with mocked API calls."""
    
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_async_end_to_end_email_lifecycle(self, mock_context, sample_gmail_message):
        """Test complete async email lifecycle: send, read, label, delete."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock responses
        sent_email_response = {
            "id": "msg_sent_123",
            "threadId": "thread_456"
        }
        
        # Set up sequential responses for aiogoogle.as_user calls
        mock_aiogoogle.as_user.side_effect = [
            sent_email_response,  # send_email
            sample_gmail_message,  # get_email (for sent email)
            sample_gmail_message,  # get_email (retrieve)
            None,  # mark_as_read
            None,  # add_label
            None   # delete_email
        ]
        
        # Test: Send email
        sent_email = await AsyncEmailMessage.send_email(
            to=["recipient@example.com"],
            subject="Async Integration Test Email",
            body_text="This is an async test email for integration testing.",
            cc=["cc@example.com"]
        )
        
        assert sent_email.message_id == "msg_123"  # From sample_gmail_message
        assert sent_email.subject == "Test Email Subject"
        
        # Test: Get email
        retrieved_email = await AsyncEmailMessage.get_email("msg_123")
        assert retrieved_email.message_id == "msg_123"
        assert retrieved_email.subject == "Test Email Subject"
        
        # Test: Mark as read
        result = await retrieved_email.mark_as_read()
        assert result is True
        assert retrieved_email.is_read is True
        
        # Test: Add label
        result = await retrieved_email.add_label(["IMPORTANT"])
        assert result is True
        assert "IMPORTANT" in retrieved_email.label_ids
        
        # Test: Delete email
        result = await retrieved_email.delete_email()
        assert result is True
        
        # Verify all API calls were made
        assert mock_aiogoogle.as_user.call_count == 6
    
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_async_label_management_workflow(self, mock_context):
        """Test complete async label management workflow."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock responses
        created_label_response = {
            "id": "label_new_123",
            "name": "Async Integration Test Label",
            "type": "user"
        }
        
        updated_label_response = {
            "id": "label_new_123",
            "name": "Updated Async Integration Test Label", 
            "type": "user"
        }
        
        labels_list_response = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "label_new_123", "name": "Updated Async Integration Test Label", "type": "user"}
            ]
        }
        
        mock_aiogoogle.as_user.side_effect = [
            created_label_response,  # create_label
            updated_label_response,  # update_label
            labels_list_response,    # list_labels
            None                     # delete_label
        ]
        
        # Test: Create label
        new_label = await AsyncLabel.create_label("Async Integration Test Label")
        assert new_label.id == "label_new_123"
        assert new_label.name == "Async Integration Test Label"
        assert new_label.type == "user"
        
        # Test: Update label
        updated_label = await new_label.update_label("Updated Async Integration Test Label")
        assert updated_label.name == "Updated Async Integration Test Label"
        
        # Test: List labels
        labels = await AsyncLabel.list_labels()
        assert len(labels) == 2
        assert any(label.id == "label_new_123" for label in labels)
        
        # Test: Delete label
        result = await updated_label.delete_label()
        assert result is True
        
        # Verify all API calls were made
        assert mock_aiogoogle.as_user.call_count == 4
    
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_async_batch_operations_workflow(self, mock_context, sample_gmail_message):
        """Test async batch operations workflow."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Test batch get emails using the class method directly
        message_ids = ["msg_123", "msg_456", "msg_789"]
        
        # Mock the get_email method to return our sample messages
        with patch.object(AsyncEmailMessage, 'get_email') as mock_get_email:
            mock_email_1 = Mock(spec=AsyncEmailMessage)
            mock_email_1.message_id = "msg_123"
            mock_email_2 = Mock(spec=AsyncEmailMessage) 
            mock_email_2.message_id = "msg_456"
            mock_email_3 = Mock(spec=AsyncEmailMessage)
            mock_email_3.message_id = "msg_789"
            
            mock_get_email.side_effect = [mock_email_1, mock_email_2, mock_email_3]
            
            retrieved_emails = await AsyncEmailMessage.batch_get_emails(message_ids)
            
            assert len(retrieved_emails) == 3
            assert retrieved_emails[0].message_id == "msg_123"
            assert retrieved_emails[1].message_id == "msg_456"
            assert retrieved_emails[2].message_id == "msg_789"
            assert mock_get_email.call_count == 3
        
        # Test batch send emails
        with patch.object(AsyncEmailMessage, 'send_email') as mock_send_email:
            mock_sent_1 = Mock(spec=AsyncEmailMessage)
            mock_sent_1.message_id = "msg_sent_123"
            mock_sent_2 = Mock(spec=AsyncEmailMessage)
            mock_sent_2.message_id = "msg_sent_456"
            
            mock_send_email.side_effect = [mock_sent_1, mock_sent_2]
            
            email_data_list = [
                {
                    "to": ["recipient1@example.com"],
                    "subject": "Async Batch Email 1",
                    "body_text": "This is async batch email 1"
                },
                {
                    "to": ["recipient2@example.com"],
                    "subject": "Async Batch Email 2", 
                    "body_text": "This is async batch email 2"
                }
            ]
            
            sent_emails = await AsyncEmailMessage.batch_send_emails(email_data_list)
            
            assert len(sent_emails) == 2
            assert sent_emails[0].message_id == "msg_sent_123"
            assert sent_emails[1].message_id == "msg_sent_456"
            assert mock_send_email.call_count == 2
    
    @patch('src.google_api_client.clients.gmail.async_client.async_gmail_service')
    async def test_async_query_builder_workflow(self, mock_context, sample_gmail_message):
        """Test async query builder workflow."""
        # Setup mock async context manager
        mock_aiogoogle = AsyncMock()
        mock_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_service)
        
        # Mock search response
        search_response = {
            "messages": [
                {"id": "msg_123"},
                {"id": "msg_456"}
            ]
        }
        
        # Mock responses for list_emails and individual get_email calls
        mock_aiogoogle.as_user.side_effect = [
            search_response,      # list_emails
            sample_gmail_message, # get_email for msg_123
            sample_gmail_message  # get_email for msg_456
        ]
        
        # Test: Complex async query
        emails = await (AsyncEmailMessage.query()
                       .limit(25)
                       .from_sender("important@example.com")
                       .search("urgent")
                       .is_unread()
                       .last_days(7)
                       .execute())
        
        assert len(emails) == 2
        
        # Verify the correct number of API calls
        # 1 call for list_emails + 2 calls for individual get_email
        assert mock_aiogoogle.as_user.call_count == 3
        
        # Test utility methods
        # Reset mock for new operations
        mock_aiogoogle.reset_mock()
        mock_aiogoogle.as_user.side_effect = [
            {"messages": [{"id": "msg_first"}]},  # first() query
            sample_gmail_message                   # get_email for first result
        ]
        
        first_email = await (AsyncEmailMessage.query()
                           .search("meeting")
                           .first())
        
        assert first_email.message_id == "msg_123"
        assert mock_aiogoogle.as_user.call_count == 2
        
        # Test exists method
        mock_aiogoogle.reset_mock()
        mock_aiogoogle.as_user.side_effect = [
            {"messages": [{"id": "msg_exists"}]},  # exists() query
            sample_gmail_message                   # get_email for exists check
        ]
        
        exists = await (AsyncEmailMessage.query()
                       .search("meeting")
                       .exists())
        
        assert exists is True
        assert mock_aiogoogle.as_user.call_count == 2


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail API message response for integration tests."""
    return {
        "id": "msg_123",
        "threadId": "thread_456",
        "snippet": "This is a test email snippet for integration testing...",
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
                "data": "VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keSBmb3IgaW50ZWdyYXRpb24gdGVzdGluZy4="  # Base64
            },
            "mimeType": "text/plain",
            "parts": [
                {
                    "filename": "test_attachment.pdf",
                    "mimeType": "application/pdf",
                    "body": {
                        "attachmentId": "att_123",
                        "size": 2048
                    }
                }
            ]
        }
    }