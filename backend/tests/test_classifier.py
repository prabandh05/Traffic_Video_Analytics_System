"""
Unit tests for the vehicle classifier.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.utils.classifier import classify_vehicle, get_all_categories


def test_two_wheelers():
    """Bicycle and motorcycle should classify as Two Wheeler."""
    assert classify_vehicle(1, "bicycle") == "Two Wheeler"
    assert classify_vehicle(3, "motorcycle") == "Two Wheeler"
    print("✅ test_two_wheelers passed")


def test_four_wheeler():
    """Car should classify as Four Wheeler."""
    assert classify_vehicle(2, "car") == "Four Wheeler"
    print("✅ test_four_wheeler passed")


def test_commercial():
    """Bus and truck should classify as Commercial."""
    assert classify_vehicle(5, "bus") == "Commercial"
    assert classify_vehicle(7, "truck") == "Commercial"
    print("✅ test_commercial passed")


def test_unknown():
    """Unknown class IDs should return Unknown."""
    assert classify_vehicle(0, "person") == "Unknown"
    assert classify_vehicle(15, "cat") == "Unknown"
    assert classify_vehicle(99, "") == "Unknown"
    print("✅ test_unknown passed")


def test_categories_list():
    """All expected categories should be present."""
    cats = get_all_categories()
    assert "Two Wheeler" in cats
    assert "Four Wheeler" in cats
    assert "Commercial" in cats
    assert "Auto" in cats
    assert "Unknown" in cats
    print("✅ test_categories_list passed")


if __name__ == "__main__":
    test_two_wheelers()
    test_four_wheeler()
    test_commercial()
    test_unknown()
    test_categories_list()
    print("\n🎉 All classifier tests passed!")
