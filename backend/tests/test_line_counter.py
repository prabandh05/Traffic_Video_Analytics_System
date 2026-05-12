"""
Unit tests for the core line crossing logic.

Tests the LineCrossingCounter to verify:
- Crossings are detected correctly
- Each track is counted at most once (no double counting)
- Non-crossings are not counted
- Direction detection works
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.processing.line_counter import LineCrossingCounter


def test_basic_crossing():
    """A vehicle moving from above to below a horizontal line should be counted."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    # Track 1: moving downward, crosses the line at y=300
    crossed = counter.check_crossing(
        track_id=1,
        prev_center=(400, 280),   # above line
        curr_center=(400, 320),   # below line
        vehicle_category="Four Wheeler",
        timestamp=1.0,
    )

    assert crossed is True, "Should detect crossing"
    assert counter.counts["Four Wheeler"] == 1
    assert counter.get_total_count() == 1
    print("✅ test_basic_crossing passed")


def test_no_double_counting():
    """Same track crossing the line again should NOT be counted twice."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    # First crossing
    counter.check_crossing(1, (400, 280), (400, 320), "Four Wheeler", 1.0)

    # Same track, crosses again (e.g., moving back)
    crossed = counter.check_crossing(1, (400, 320), (400, 280), "Four Wheeler", 2.0)

    assert crossed is False, "Same track should not be double counted"
    assert counter.counts["Four Wheeler"] == 1
    assert counter.get_total_count() == 1
    print("✅ test_no_double_counting passed")


def test_no_crossing():
    """A vehicle moving parallel to the line should NOT be counted."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    # Track moving horizontally, staying above the line
    crossed = counter.check_crossing(
        track_id=2,
        prev_center=(100, 250),
        curr_center=(200, 250),
        vehicle_category="Two Wheeler",
    )

    assert crossed is False, "Parallel movement should not trigger crossing"
    assert counter.get_total_count() == 0
    print("✅ test_no_crossing passed")


def test_multiple_vehicles():
    """Multiple different vehicles crossing should all be counted."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    # Track 1: car
    counter.check_crossing(1, (100, 280), (100, 320), "Four Wheeler", 1.0)
    # Track 2: motorcycle
    counter.check_crossing(2, (300, 290), (300, 310), "Two Wheeler", 1.5)
    # Track 3: truck
    counter.check_crossing(3, (500, 280), (500, 320), "Commercial", 2.0)

    assert counter.counts["Four Wheeler"] == 1
    assert counter.counts["Two Wheeler"] == 1
    assert counter.counts["Commercial"] == 1
    assert counter.get_total_count() == 3
    print("✅ test_multiple_vehicles passed")


def test_diagonal_line():
    """Counting should work with a diagonal line too."""
    # Diagonal line from bottom-left to top-right
    counter = LineCrossingCounter(line_start=(100, 500), line_end=(700, 100))

    # Vehicle crossing from left to right across the diagonal
    # At x=200, y_line ≈ 433. At x=500, y_line ≈ 233. 
    # y=350 is between them, so (200, 350) is on one side and (500, 350) is on the other.
    crossed = counter.check_crossing(
        track_id=10,
        prev_center=(200, 350),
        curr_center=(500, 350),
        vehicle_category="Four Wheeler",
    )

    # This should cross since the point moves from one side of the diagonal to the other
    assert crossed is True, "Should detect crossing on diagonal line"
    print("✅ test_diagonal_line passed")


def test_none_positions():
    """None positions should not cause errors or false counts."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    crossed = counter.check_crossing(1, None, (400, 320), "Four Wheeler")
    assert crossed is False

    crossed = counter.check_crossing(2, (400, 280), None, "Four Wheeler")
    assert crossed is False

    assert counter.get_total_count() == 0
    print("✅ test_none_positions passed")


def test_crossing_log():
    """Crossing log should record all crossing details."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))

    counter.check_crossing(1, (400, 280), (400, 320), "Four Wheeler", 1.5)
    counter.check_crossing(2, (200, 290), (200, 310), "Two Wheeler", 3.0)

    log = counter.get_crossing_log()
    assert len(log) == 2
    assert log[0]["track_id"] == 1
    assert log[0]["vehicle_type"] == "Four Wheeler"
    assert log[0]["timestamp"] == 1.5
    assert log[1]["track_id"] == 2
    print("✅ test_crossing_log passed")


def test_reset():
    """Reset should clear all state."""
    counter = LineCrossingCounter(line_start=(0, 300), line_end=(800, 300))
    counter.check_crossing(1, (400, 280), (400, 320), "Four Wheeler", 1.0)

    assert counter.get_total_count() == 1

    counter.reset()

    assert counter.get_total_count() == 0
    assert len(counter.counted_ids) == 0
    assert len(counter.crossing_log) == 0
    print("✅ test_reset passed")


if __name__ == "__main__":
    test_basic_crossing()
    test_no_double_counting()
    test_no_crossing()
    test_multiple_vehicles()
    test_diagonal_line()
    test_none_positions()
    test_crossing_log()
    test_reset()
    print("\n🎉 All line crossing tests passed!")
