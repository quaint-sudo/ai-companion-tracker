"""Smoke tests for ingestion modules."""

import os
import json
import tempfile
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from ingestion.config import APPSTORE_COLUMNS, REDDIT_COLUMNS


class TestAppStoreIngestion:
    """Tests for the App Store RSS scraper using mocked HTTP responses."""

    MOCK_RSS_RESPONSE = {
        "feed": {
            "entry": [
                {
                    "content": {"label": "This app is so helpful for my anxiety!"},
                    "im:rating": {"label": "5"},
                },
                {
                    "content": {"label": "I feel addicted and obsessed with talking to it"},
                    "im:rating": {"label": "2"},
                },
                {
                    "content": {"label": "Nice colors and smooth animations"},
                    "im:rating": {"label": "4"},
                },
            ]
        }
    }

    @patch("ingestion.appstore_rss.requests.get")
    def test_fetch_reviews(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_RSS_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from ingestion.appstore_rss import fetch_reviews
        reviews = fetch_reviews("123456", max_pages=1)

        assert len(reviews) == 3
        assert "helpful" in reviews[0].lower()
        assert "addicted" in reviews[1].lower()

    @patch("ingestion.appstore_rss.requests.get")
    def test_fetch_reviews_empty_feed(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"feed": {"entry": []}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from ingestion.appstore_rss import fetch_reviews
        reviews = fetch_reviews("123456", max_pages=1)

        assert len(reviews) == 0

    @patch("ingestion.appstore_rss.requests.get")
    def test_fetch_reviews_network_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("Connection timeout")

        from ingestion.appstore_rss import fetch_reviews
        reviews = fetch_reviews("123456", max_pages=1)

        assert len(reviews) == 0

    def test_appstore_csv_columns(self):
        """Verify CSV schema is consistent."""
        expected = ["week", "app", "review_count", "benefit_count", "harm_count",
                     "benefit_rate", "harm_rate", "net_sentiment"]
        assert APPSTORE_COLUMNS == expected

    def test_reddit_csv_columns(self):
        """Verify CSV schema is consistent."""
        expected = ["week", "subreddit", "post_count", "comment_count",
                     "benefit_count", "harm_count", "benefit_rate", "harm_rate",
                     "net_sentiment", "sentiment_velocity"]
        assert REDDIT_COLUMNS == expected
