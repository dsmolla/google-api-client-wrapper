import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.gmail.async_query_builder import AsyncEmailQueryBuilder
from src.google_api_client.clients.gmail.async_client import AsyncEmailMessage


@pytest.mark.unit
@pytest.mark.gmail
class TestAsyncEmailQueryBuilder:
    """Test cases for the AsyncEmailQueryBuilder class."""
    
    def test_builder_creation(self):
        """Test creating an async query builder."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        assert builder._async_email_message_class == AsyncEmailMessage
        assert builder._max_results == 30  # DEFAULT_MAX_RESULTS
        assert builder._query_parts == []
        assert builder._include_spam_trash is False
        assert builder._label_ids == []
    
    def test_limit_method(self):
        """Test limit method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.limit(50)
        
        assert result is builder  # Method chaining
        assert builder._max_results == 50
    
    def test_limit_validation(self):
        """Test limit method validation."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(0)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(3000)
    
    def test_search_method(self):
        """Test search method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.search("meeting")
        
        assert result is builder  # Method chaining
        assert "meeting" in builder._query_parts
    
    def test_from_sender_method(self):
        """Test from_sender method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.from_sender("john@example.com")
        
        assert result is builder
        assert "from:john@example.com" in builder._query_parts
    
    def test_to_recipient_method(self):
        """Test to_recipient method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.to_recipient("jane@example.com")
        
        assert result is builder
        assert "to:jane@example.com" in builder._query_parts
    
    def test_with_subject_method(self):
        """Test with_subject method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.with_subject("important meeting")
        
        assert result is builder
        assert "subject:important meeting" in builder._query_parts
    
    def test_with_attachments_method(self):
        """Test with_attachments method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.with_attachments()
        
        assert result is builder
        assert "has:attachment" in builder._query_parts
    
    def test_without_attachments_method(self):
        """Test without_attachments method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.without_attachments()
        
        assert result is builder
        assert "-has:attachment" in builder._query_parts
    
    def test_is_read_method(self):
        """Test is_read method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.is_read()
        
        assert result is builder
        assert "-is:unread" in builder._query_parts
    
    def test_is_unread_method(self):
        """Test is_unread method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.is_unread()
        
        assert result is builder
        assert "is:unread" in builder._query_parts
    
    def test_is_starred_method(self):
        """Test is_starred method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.is_starred()
        
        assert result is builder
        assert "is:starred" in builder._query_parts
    
    def test_is_important_method(self):
        """Test is_important method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.is_important()
        
        assert result is builder
        assert "is:important" in builder._query_parts
    
    def test_in_folder_method(self):
        """Test in_folder method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.in_folder("inbox")
        
        assert result is builder
        assert "in:inbox" in builder._query_parts
    
    def test_with_label_method(self):
        """Test with_label method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.with_label("important")
        
        assert result is builder
        assert "label:important" in builder._query_parts
    
    def test_in_date_range_method(self):
        """Test in_date_range method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)
        
        result = builder.in_date_range(start_date, end_date)
        
        assert result is builder
        assert "after:2025/01/01" in builder._query_parts
        assert "before:2025/01/31" in builder._query_parts
    
    def test_in_date_range_validation(self):
        """Test in_date_range method validation."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        start_date = datetime(2025, 1, 31)
        end_date = datetime(2025, 1, 1)  # End before start
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            builder.in_date_range(start_date, end_date)
    
    def test_after_date_method(self):
        """Test after_date method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        test_date = datetime(2025, 1, 15)
        
        result = builder.after_date(test_date)
        
        assert result is builder
        assert "after:2025/01/15" in builder._query_parts
    
    def test_before_date_method(self):
        """Test before_date method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        test_date = datetime(2025, 1, 15)
        
        result = builder.before_date(test_date)
        
        assert result is builder
        assert "before:2025/01/15" in builder._query_parts
    
    @patch('src.google_api_client.clients.gmail.async_query_builder.datetime')
    def test_today_method(self, mock_datetime):
        """Test today method."""
        # Mock datetime.now() to return a fixed date
        mock_now = Mock()
        mock_now.date.return_value = date(2025, 1, 15)
        mock_datetime.now.return_value = mock_now
        
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.today()
        
        assert result is builder
        assert "after:2025/01/15" in builder._query_parts
    
    @patch('src.google_api_client.clients.gmail.async_query_builder.datetime')
    def test_yesterday_method(self, mock_datetime):
        """Test yesterday method."""
        # Mock datetime.now() to return a fixed date
        mock_now = Mock()
        mock_now.date.return_value = date(2025, 1, 16)
        mock_datetime.now.return_value = mock_now
        
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.yesterday()
        
        assert result is builder
        assert "after:2025/01/15" in builder._query_parts  # Yesterday
        assert "before:2025/01/16" in builder._query_parts  # Today
    
    def test_last_days_method(self):
        """Test last_days method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with patch('src.google_api_client.clients.gmail.async_query_builder.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 15, 12, 0)
            mock_datetime.now.return_value = mock_now
            
            result = builder.last_days(7)
            
            assert result is builder
            assert "after:2025/01/08" in builder._query_parts  # 7 days ago
    
    def test_last_days_validation(self):
        """Test last_days method validation."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.last_days(0)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.last_days(-1)
    
    def test_this_week_method(self):
        """Test this_week method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with patch.object(builder, 'last_days', return_value=builder) as mock_last_days:
            result = builder.this_week()
            mock_last_days.assert_called_once_with(date.today().weekday() + 1)  # Monday to today
            # +1 because last_days expects the number of days including today
            assert result is builder
    
    def test_this_month_method(self):
        """Test this_month method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with patch.object(builder, 'last_days', return_value=builder) as mock_last_days:
            result = builder.this_month()
            mock_last_days.assert_called_once_with(date.today().day) # Days in current month
            assert result is builder
    
    def test_larger_than_method(self):
        """Test larger_than method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.larger_than(5)
        
        assert result is builder
        assert "larger:5M" in builder._query_parts
    
    def test_larger_than_validation(self):
        """Test larger_than method validation."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        with pytest.raises(ValueError, match="Size must be positive"):
            builder.larger_than(0)
    
    def test_smaller_than_method(self):
        """Test smaller_than method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.smaller_than(10)
        
        assert result is builder
        assert "smaller:10M" in builder._query_parts
    
    def test_include_spam_trash_method(self):
        """Test include_spam_trash method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.include_spam_trash(True)
        
        assert result is builder
        assert builder._include_spam_trash is True
        
        # Test setting to False
        result2 = builder.include_spam_trash(False)
        assert result2 is builder
        assert builder._include_spam_trash is False
    
    def test_with_label_ids_method(self):
        """Test with_label_ids method."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        result = builder.with_label_ids(["INBOX", "IMPORTANT"])
        
        assert result is builder
        assert "INBOX" in builder._label_ids
        assert "IMPORTANT" in builder._label_ids
    
    def test_method_chaining(self):
        """Test method chaining with multiple methods."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        result = (builder
                 .limit(50)
                 .from_sender("john@example.com")
                 .search("meeting")
                 .with_attachments()
                 .is_unread())
        
        assert result is builder
        assert builder._max_results == 50
        assert "from:john@example.com" in builder._query_parts
        assert "meeting" in builder._query_parts
        assert "has:attachment" in builder._query_parts
        assert "is:unread" in builder._query_parts
    
    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test execute method."""
        mock_emails = [Mock(), Mock(), Mock()]
        
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = mock_emails
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            builder.limit(50).search("meeting").from_sender("john@example.com")
            
            result = await builder.execute()
            
            assert result == mock_emails
            mock_list_emails.assert_called_once_with(
                max_results=50,
                query="meeting from:john@example.com",
                include_spam_trash=False,
                label_ids=None
            )
    
    @pytest.mark.asyncio
    async def test_execute_method_with_labels(self):
        """Test execute method with label IDs."""
        mock_emails = [Mock()]
        
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = mock_emails
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            builder.with_label_ids(["INBOX", "IMPORTANT"])
            
            result = await builder.execute()
            
            assert result == mock_emails
            mock_list_emails.assert_called_once_with(
                max_results=30,  # DEFAULT_MAX_RESULTS
                query=None,  # No query parts
                include_spam_trash=False,
                label_ids=["INBOX", "IMPORTANT"]
            )
    
    @pytest.mark.asyncio
    async def test_count_method(self):
        """Test count method."""
        mock_emails = [Mock()]
        
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = mock_emails
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            builder.limit(100).search("meeting")
            
            result = await builder.count()
            
            assert result == 1  # Length of mock_emails
            # Should call with limit 1 to minimize data transfer
            mock_list_emails.assert_called_once_with(
                max_results=1,
                query="meeting",
                include_spam_trash=False,
                label_ids=None
            )
            # Verify original limit was restored
            assert builder._max_results == 100
    
    @pytest.mark.asyncio
    async def test_first_method(self):
        """Test first method."""
        mock_email = Mock()
        
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = [mock_email]
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            builder.search("meeting")
            
            result = await builder.first()
            
            assert result == mock_email
            mock_list_emails.assert_called_once_with(
                max_results=1,
                query="meeting",
                include_spam_trash=False,
                label_ids=None
            )
    
    @pytest.mark.asyncio
    async def test_first_method_no_results(self):
        """Test first method with no results."""
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = []
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            result = await builder.first()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_exists_method_true(self):
        """Test exists method when emails exist."""
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = [Mock()]
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            result = await builder.exists()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_method_false(self):
        """Test exists method when no emails exist."""
        with patch.object(AsyncEmailMessage, 'list_emails', new_callable=AsyncMock) as mock_list_emails:
            mock_list_emails.return_value = []
            
            builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
            result = await builder.exists()
            
            assert result is False
    
    def test_repr_method(self):
        """Test string representation of AsyncEmailQueryBuilder."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        builder.limit(50).search("meeting").from_sender("john@example.com")
        
        repr_str = repr(builder)
        
        assert "AsyncEmailQueryBuilder" in repr_str
        assert "meeting from:john@example.com" in repr_str
        assert "limit=50" in repr_str
    
    def test_repr_method_no_query(self):
        """Test string representation with no query parts."""
        builder = AsyncEmailQueryBuilder(AsyncEmailMessage)
        
        repr_str = repr(builder)
        
        assert "AsyncEmailQueryBuilder" in repr_str
        assert "query='None'" in repr_str
        assert "limit=30" in repr_str