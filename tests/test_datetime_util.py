import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import patch
import tzlocal
from utils.datetime_util import (
    current_datetime_local_timezone,
    convert_datetime_to_iso,
    convert_datetime_to_readable,
    convert_datetime_to_local_timezone,
    combine_with_timezone,
    today_start,
    today_end,
    date_start,
    date_end,
    days_from_today
)


class TestDatetimeUtil:
    """Test cases for datetime utility functions."""
    
    def test_current_datetime_local_timezone(self):
        """Test current_datetime_local_timezone returns timezone-aware datetime."""
        result = current_datetime_local_timezone()
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None  # Should be timezone-aware
        assert result.tzinfo == tzlocal.get_localzone()
    
    def test_convert_datetime_to_iso(self):
        """Test convert_datetime_to_iso function."""
        # Create a timezone-aware datetime
        local_tz = tzlocal.get_localzone()
        dt = datetime(2025, 1, 15, 14, 30, 0).replace(tzinfo=local_tz)
        
        result = convert_datetime_to_iso(dt)
        
        assert isinstance(result, str)
        assert "2025-01-15" in result
        assert "14:30:00" in result
        # Should contain timezone info
        assert "+" in result or "-" in result or "Z" in result
    
    def test_convert_datetime_to_readable_single(self):
        """Test convert_datetime_to_readable with single datetime."""
        dt = datetime(2025, 1, 15, 14, 30, 0)
        
        result = convert_datetime_to_readable(dt)
        
        assert isinstance(result, str)
        assert "Wed, 15 Jan 2025" in result
        assert "02:30 PM" in result
        assert " - " not in result  # No end time
    
    def test_convert_datetime_to_readable_range_same_day(self):
        """Test convert_datetime_to_readable with same-day range."""
        start = datetime(2025, 1, 15, 14, 30, 0)
        end = datetime(2025, 1, 15, 16, 0, 0)
        
        result = convert_datetime_to_readable(start, end)
        
        assert isinstance(result, str)
        assert "Wed, 15 Jan 2025 02:30 PM - 04:00 PM" == result
    
    def test_convert_datetime_to_readable_range_different_days(self):
        """Test convert_datetime_to_readable with different-day range."""
        start = datetime(2025, 1, 15, 14, 30, 0)
        end = datetime(2025, 1, 16, 16, 0, 0)
        
        result = convert_datetime_to_readable(start, end)
        
        assert isinstance(result, str)
        assert "Wed, 15 Jan 2025 02:30 PM" in result
        assert "Thu, 16 Jan 2025 04:00 PM" in result
        assert " - " in result
    
    def test_convert_datetime_to_local_timezone(self):
        """Test convert_datetime_to_local_timezone function."""
        # Create a UTC datetime
        utc_dt = datetime(2025, 1, 15, 19, 30, 0, tzinfo=datetime.now().astimezone().tzinfo)
        
        result = convert_datetime_to_local_timezone(utc_dt)
        
        assert isinstance(result, datetime)
        assert result.tzinfo == tzlocal.get_localzone()
    
    def test_combine_with_timezone(self):
        """Test combine_with_timezone function."""
        test_date = date(2025, 1, 15)
        test_time = time(14, 30, 0)
        
        result = combine_with_timezone(test_date, test_time)
        
        assert isinstance(result, datetime)
        assert result.date() == test_date
        assert result.time() == test_time
        assert result.tzinfo is not None  # Should be timezone-aware
        assert result.tzinfo == tzlocal.get_localzone()
    
    def test_today_start(self):
        """Test today_start function."""
        result = today_start()
        
        assert isinstance(result, datetime)
        assert result.date() == date.today()
        assert result.time() == time.min
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_today_end(self):
        """Test today_end function."""
        result = today_end()
        
        assert isinstance(result, datetime)
        assert result.date() == date.today()
        assert result.time() == time.max
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_date_start(self):
        """Test date_start function."""
        test_date = date(2025, 1, 15)
        result = date_start(test_date)
        
        assert isinstance(result, datetime)
        assert result.date() == test_date
        assert result.time() == time.min
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_date_end(self):
        """Test date_end function."""
        test_date = date(2025, 1, 15)
        result = date_end(test_date)
        
        assert isinstance(result, datetime)
        assert result.date() == test_date
        assert result.time() == time.max
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_days_from_today_positive(self):
        """Test days_from_today with positive days (future)."""
        result = days_from_today(7)
        
        assert isinstance(result, datetime)
        expected_date = date.today() + timedelta(days=7)
        assert result.date() == expected_date
        assert result.time() == time.min
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_days_from_today_negative(self):
        """Test days_from_today with negative days (past)."""
        result = days_from_today(-3)
        
        assert isinstance(result, datetime)
        expected_date = date.today() - timedelta(days=3)
        assert result.date() == expected_date
        assert result.time() == time.min
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_days_from_today_zero(self):
        """Test days_from_today with zero days (today)."""
        result = days_from_today(0)
        
        assert isinstance(result, datetime)
        assert result.date() == date.today()
        assert result.time() == time.min
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_timezone_consistency(self):
        """Test that all timezone-aware functions use the same timezone."""
        funcs_to_test = [
            today_start(),
            today_end(),
            date_start(date.today()),
            date_end(date.today()),
            days_from_today(1),
            current_datetime_local_timezone()
        ]
        
        # All should use the same timezone
        local_tz = tzlocal.get_localzone()
        for dt in funcs_to_test:
            assert dt.tzinfo == local_tz
    
    def test_timezone_aware_comparison(self):
        """Test that timezone-aware datetimes can be compared safely."""
        start = today_start()
        end = today_end()
        tomorrow = days_from_today(1)
        
        # These comparisons should not raise exceptions
        assert start < end
        assert start < tomorrow
        assert end < tomorrow
        
        # Test with current time
        now = current_datetime_local_timezone()
        # These should work without timezone warnings
        if now.date() == date.today():
            assert start <= now <= end
    
    @patch('utils.datetime_util.date')
    def test_date_functions_with_mocked_date(self, mock_date):
        """Test date functions with a mocked current date."""
        # Mock date.today() to return a specific date
        test_date = date(2025, 6, 15)  # A specific test date
        mock_date.today.return_value = test_date
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        
        result = today_start()
        assert result.date() == test_date
        
        result = today_end()
        assert result.date() == test_date
        
        result = days_from_today(5)
        expected_date = test_date + timedelta(days=5)
        assert result.date() == expected_date
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test leap year
        leap_day = date(2024, 2, 29)
        result = date_start(leap_day)
        assert result.date() == leap_day
        
        # Test year boundary
        new_years_eve = date(2024, 12, 31)
        result = date_end(new_years_eve)
        assert result.date() == new_years_eve
        
        # Test large day differences
        result = days_from_today(365)
        expected_date = date.today() + timedelta(days=365)
        assert result.date() == expected_date
        
        result = days_from_today(-365)
        expected_date = date.today() - timedelta(days=365)
        assert result.date() == expected_date
    
    def test_time_precision(self):
        """Test that time precision is maintained correctly."""
        # Test that time.min is exactly midnight
        result = today_start()
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0
        
        # Test that time.max is end of day
        result = today_end()
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999