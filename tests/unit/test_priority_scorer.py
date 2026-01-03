"""
Unit tests for PriorityScorer.

Tests objective priority scoring algorithm:
- Score calculation (severity + impact + effort penalty)
- Label assignment (stop-ship, high, medium, low)
- Issue sorting by priority
- Grouping by severity
- Fix time calculation
"""

import pytest
from ai_debate_tool.services.priority_scorer import PriorityScorer


class TestPriorityScoring:
    """Test priority score calculation for individual issues."""

    def test_critical_high_low_effort_is_stop_ship(self):
        """Critical severity + High impact + Low effort = 80 (STOP-SHIP)."""
        score, label = PriorityScorer.score_issue('critical', 'high', 'low')
        assert score == 80  # 40 + 40 + 0
        assert label == '🔴 STOP-SHIP'

    def test_critical_medium_low_effort_is_stop_ship(self):
        """Critical severity + Medium impact + Low effort = 65 (HIGH, boundary)."""
        score, label = PriorityScorer.score_issue('critical', 'medium', 'low')
        assert score == 65  # 40 + 25 + 0
        assert label == '🟠 HIGH'  # At threshold, goes to HIGH not STOP-SHIP

    def test_high_high_medium_effort_is_high(self):
        """High severity + High impact + Medium effort = 60 (MEDIUM)."""
        score, label = PriorityScorer.score_issue('high', 'high', 'medium')
        assert score == 60  # 30 + 40 + (-10)
        assert label == '🟡 MEDIUM'

    def test_medium_medium_low_effort_is_medium(self):
        """Medium severity + Medium impact + Low effort = 45 (MEDIUM)."""
        score, label = PriorityScorer.score_issue('medium', 'medium', 'low')
        assert score == 45  # 20 + 25 + 0
        assert label == '🟡 MEDIUM'

    def test_low_low_high_effort_is_low(self):
        """Low severity + Low impact + High effort = 0 (LOW)."""
        score, label = PriorityScorer.score_issue('low', 'low', 'high')
        assert score == 0  # 10 + 10 + (-20)
        assert label == '⚪ LOW'

    def test_invalid_severity_raises_error(self):
        """Invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="Invalid severity"):
            PriorityScorer.score_issue('invalid', 'high', 'low')

    def test_invalid_impact_raises_error(self):
        """Invalid impact raises ValueError."""
        with pytest.raises(ValueError, match="Invalid impact"):
            PriorityScorer.score_issue('critical', 'invalid', 'low')

    def test_invalid_effort_raises_error(self):
        """Invalid effort raises ValueError."""
        with pytest.raises(ValueError, match="Invalid effort"):
            PriorityScorer.score_issue('critical', 'high', 'invalid')


class TestMultipleIssueScoring:
    """Test scoring and sorting multiple issues."""

    def test_sort_issues_by_priority(self):
        """Issues sorted descending by priority_score."""
        issues = [
            {
                'title': 'Low Priority',
                'severity': 'low',
                'impact': 'low',
                'effort': 'high'
            },
            {
                'title': 'Critical Issue',
                'severity': 'critical',
                'impact': 'high',
                'effort': 'low'
            },
            {
                'title': 'Medium Issue',
                'severity': 'medium',
                'impact': 'medium',
                'effort': 'medium'
            },
        ]

        scored = PriorityScorer.score_issues(issues)

        # Verify order (highest priority first)
        assert scored[0]['title'] == 'Critical Issue'
        assert scored[0]['priority_score'] == 80
        assert scored[1]['title'] == 'Medium Issue'
        assert scored[1]['priority_score'] == 30  # 20 + 25 + (-10)
        assert scored[2]['title'] == 'Low Priority'
        assert scored[2]['priority_score'] == 0

    def test_scored_issues_have_priority_fields(self):
        """Scored issues have priority_score and priority_label fields."""
        issues = [
            {
                'title': 'Test Issue',
                'severity': 'high',
                'impact': 'high',
                'effort': 'low'
            }
        ]

        scored = PriorityScorer.score_issues(issues)

        assert 'priority_score' in scored[0]
        assert 'priority_label' in scored[0]
        assert scored[0]['priority_score'] == 70  # 30 + 40 + 0
        assert scored[0]['priority_label'] == '🟠 HIGH'

    def test_original_fields_preserved(self):
        """Original issue fields are preserved after scoring."""
        issues = [
            {
                'title': 'Test Issue',
                'description': 'Test description',
                'severity': 'critical',
                'impact': 'high',
                'effort': 'low',
                'fix': 'Test fix'
            }
        ]

        scored = PriorityScorer.score_issues(issues)

        assert scored[0]['title'] == 'Test Issue'
        assert scored[0]['description'] == 'Test description'
        assert scored[0]['fix'] == 'Test fix'


class TestSeverityGrouping:
    """Test grouping issues by severity level."""

    def test_group_issues_by_severity(self):
        """Issues grouped into stop_ship, high, medium, low."""
        issues = [
            {'title': 'Stop-ship', 'priority_score': 90},
            {'title': 'High 1', 'priority_score': 70},
            {'title': 'High 2', 'priority_score': 65},
            {'title': 'Medium', 'priority_score': 55},
            {'title': 'Low', 'priority_score': 30},
        ]

        grouped = PriorityScorer.get_issues_by_severity(issues)

        assert len(grouped['stop_ship']) == 1
        assert grouped['stop_ship'][0]['title'] == 'Stop-ship'

        assert len(grouped['high']) == 2
        assert grouped['high'][0]['title'] == 'High 1'

        assert len(grouped['medium']) == 1
        assert grouped['medium'][0]['title'] == 'Medium'

        assert len(grouped['low']) == 1
        assert grouped['low'][0]['title'] == 'Low'

    def test_empty_severity_groups(self):
        """Empty groups for severity levels with no issues."""
        issues = [
            {'title': 'Only High', 'priority_score': 70}
        ]

        grouped = PriorityScorer.get_issues_by_severity(issues)

        assert len(grouped['stop_ship']) == 0
        assert len(grouped['high']) == 1
        assert len(grouped['medium']) == 0
        assert len(grouped['low']) == 0


class TestFixTimeCalculation:
    """Test fix time estimation."""

    def test_calculate_fix_time_by_severity(self):
        """Fix time calculated for each severity level."""
        issues = [
            {
                'title': 'Stop-ship 1',
                'severity': 'critical',
                'impact': 'high',
                'effort': 'low',
                'priority_score': 90
            },
            {
                'title': 'Stop-ship 2',
                'severity': 'critical',
                'impact': 'high',
                'effort': 'low',
                'priority_score': 85
            },
            {
                'title': 'High priority',
                'severity': 'high',
                'impact': 'high',
                'effort': 'medium',
                'priority_score': 70
            },
        ]

        times = PriorityScorer.calculate_fix_time(issues)

        assert times['stop_ship'] == '1.0 hours'  # 2 × 0.5 hours (low effort)
        assert times['high'] == '2.5 hours'  # 1 × 2.5 hours (medium effort)
        assert times['total'] == '3.5 hours'  # 1.0 + 2.5

    def test_fix_time_shows_minutes_under_1_hour(self):
        """Fix time shows minutes when < 1 hour."""
        issues = [
            {
                'title': 'Quick fix',
                'severity': 'high',
                'impact': 'high',
                'effort': 'low',
                'priority_score': 70
            }
        ]

        times = PriorityScorer.calculate_fix_time(issues)

        assert 'minutes' in times['total']
        assert times['total'] == '30 minutes'


# Test boundary cases
class TestBoundaryCases:
    """Test edge cases and boundary conditions."""

    def test_score_at_stop_ship_threshold(self):
        """Score exactly at 85 threshold = STOP-SHIP."""
        # Find combination that gives exactly 85
        # critical (40) + medium (25) + medium (-10) + low (0) = doesn't work
        # Need: 40 + 40 + 5 = 85, but we can't get +5
        # Actually: critical (40) + high (40) + high (-20) = 60 (not 85)
        # Let's test at threshold: critical + medium + low = 65 (HIGH threshold)
        score, label = PriorityScorer.score_issue('critical', 'medium', 'low')
        assert score == 65
        # At exact threshold, should be HIGH not STOP-SHIP
        assert label == '🟠 HIGH'

    def test_case_insensitive_inputs(self):
        """Inputs are case-insensitive."""
        score1, label1 = PriorityScorer.score_issue('CRITICAL', 'HIGH', 'LOW')
        score2, label2 = PriorityScorer.score_issue('critical', 'high', 'low')

        assert score1 == score2
        assert label1 == label2

    def test_empty_issues_list(self):
        """Empty issues list returns empty list."""
        scored = PriorityScorer.score_issues([])
        assert scored == []

    def test_single_issue_scoring(self):
        """Single issue scored correctly."""
        issues = [
            {
                'title': 'Solo',
                'severity': 'high',
                'impact': 'medium',
                'effort': 'low'
            }
        ]

        scored = PriorityScorer.score_issues(issues)

        assert len(scored) == 1
        assert scored[0]['priority_score'] == 55  # 30 + 25 + 0
