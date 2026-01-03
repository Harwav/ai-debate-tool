"""
Unit tests for FastModerator - Rule-based consensus analysis.

Tests:
1. Consensus score calculation and agreement level determination
2. Recommendation generation based on consensus
"""

import pytest
from ai_debate_tool.services.fast_moderator import FastModerator


class TestFastModerator:
    """Test suite for FastModerator component."""

    def test_consensus_calculation_strong_agreement(self):
        """Test consensus with strong agreement (scores within 10 points)."""
        claude_result = {'score': 85, 'response': 'Good plan with minor concerns'}
        codex_result = {'score': 82, 'response': 'Agree, well-designed approach'}

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Consensus score = average
        assert analysis['consensus_score'] == 83  # (85 + 82) // 2

        # Score difference
        assert analysis['score_difference'] == 3

        # Strong agreement (diff <= 10)
        assert analysis['interpretation'] == "Strong Agreement"

        # Recommendation
        assert "PROCEED" in analysis['recommendation']

        # Performance (should be very fast)
        assert analysis['analysis_time'] < 1.0  # Less than 1 second

    def test_consensus_calculation_moderate_agreement(self):
        """Test consensus with moderate agreement (scores 10-20 points apart)."""
        claude_result = {'score': 75, 'response': 'Proceed with caution'}
        codex_result = {'score': 60, 'response': 'Concerns about testing strategy'}

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Consensus score
        assert analysis['consensus_score'] == 67  # (75 + 60) // 2

        # Score difference
        assert analysis['score_difference'] == 15

        # Moderate agreement (10 < diff <= 20)
        assert analysis['interpretation'] == "Moderate Agreement"

        # Recommendation (proceed with caution)
        assert "CAUTION" in analysis['recommendation'] or "DISCUSS" in analysis['recommendation']

    def test_consensus_calculation_significant_disagreement(self):
        """Test consensus with significant disagreement (scores >20 points apart)."""
        claude_result = {'score': 80, 'response': 'Excellent refactoring plan'}
        codex_result = {'score': 45, 'response': 'Major risks not addressed, disagree with approach'}

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Consensus score
        assert analysis['consensus_score'] == 62  # (80 + 45) // 2

        # Score difference
        assert analysis['score_difference'] == 35

        # Significant disagreement (diff > 20)
        assert analysis['interpretation'] == "Significant Disagreements"

        # Recommendation (discuss first)
        assert "DISCUSS" in analysis['recommendation'] or "RECONSIDER" in analysis['recommendation']

    def test_recommendation_with_pattern_issues(self):
        """Test recommendation generation with known pattern issues."""
        claude_result = {'score': 90}  # Above 85 threshold for "proceed confidently"
        codex_result = {'score': 88}

        # No pattern issues - proceed confidently
        analysis1 = FastModerator.analyze(claude_result, codex_result)
        assert "PROCEED" in analysis1['recommendation']  # Should recommend proceeding

        # With stop-ship pattern issue (priority >= 85)
        pattern_issues = [
            {'title': 'Critical security vulnerability', 'priority_score': 90}
        ]
        analysis2 = FastModerator.analyze(claude_result, codex_result, pattern_issues)
        assert "STOP-SHIP" in analysis2['recommendation']

        # With high-priority issue (not stop-ship)
        pattern_issues = [
            {'title': 'Missing validation', 'priority_score': 70}
        ]
        analysis3 = FastModerator.analyze(claude_result, codex_result, pattern_issues)
        # Should still proceed (issue not stop-ship level)
        assert "STOP-SHIP" not in analysis3['recommendation']

    def test_disagreement_extraction(self):
        """Test extracting disagreement points from responses."""
        claude_result = {
            'score': 75,
            'response': '''
                The plan is good overall. However, I disagree with the timeline.
                There are concerns about the testing strategy.
                The refactoring approach is risky without transaction boundaries.
            '''
        }

        codex_result = {
            'score': 65,
            'response': '''
                I agree with the module structure. But the service layer is missing transaction handling.
                This is a critical issue that must be addressed.
                The rollback procedure is incomplete.
            '''
        }

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Should extract disagreements
        disagreements = analysis['disagreements']
        assert len(disagreements) > 0

        # Should have source attribution
        for disagreement in disagreements:
            assert 'source' in disagreement
            assert disagreement['source'] in ['Claude', 'Codex']
            assert 'text' in disagreement

        # Should find key concerns
        disagreement_text = ' '.join([d['text'] for d in disagreements]).lower()
        assert 'disagree' in disagreement_text or 'concern' in disagreement_text or 'issue' in disagreement_text

    def test_agreement_extraction(self):
        """Test extracting agreement points from responses."""
        claude_result = {
            'score': 85,
            'response': '''
                The module granularity is excellent and well-designed.
                I agree with the service-first approach.
                The backward compatibility strategy is smart.
            '''
        }

        codex_result = {
            'score': 80,
            'response': '''
                I agree, the module structure is appropriate.
                Good decision on using feature branches.
                The test-first approach is correct.
            '''
        }

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Should extract agreements
        agreements = analysis['agreements']
        assert len(agreements) > 0

        # Should find positive statements
        agreement_text = ' '.join(agreements).lower()
        assert 'agree' in agreement_text or 'good' in agreement_text or 'excellent' in agreement_text

    def test_summary_generation(self):
        """Test generating human-readable summary."""
        claude_result = {'score': 85, 'response': 'Good plan'}
        codex_result = {'score': 80, 'response': 'I agree, well-designed'}

        analysis = FastModerator.analyze(claude_result, codex_result)

        summary = FastModerator.generate_summary(analysis)

        # Should contain key information
        assert 'Consensus Score' in summary
        assert '82/100' in summary or '83/100' in summary  # Average
        assert 'Agreement Level' in summary
        assert 'Strong Agreement' in summary
        assert 'Recommendation' in summary
        assert 'Analysis Time' in summary

    def test_edge_case_equal_scores(self):
        """Test edge case where both AIs give identical scores."""
        claude_result = {'score': 75}
        codex_result = {'score': 75}

        analysis = FastModerator.analyze(claude_result, codex_result)

        assert analysis['consensus_score'] == 75
        assert analysis['score_difference'] == 0
        assert analysis['interpretation'] == "Strong Agreement"

    def test_edge_case_extreme_disagreement(self):
        """Test edge case with extreme disagreement (max difference)."""
        claude_result = {'score': 95}
        codex_result = {'score': 30}

        analysis = FastModerator.analyze(claude_result, codex_result)

        assert analysis['consensus_score'] == 62  # (95 + 30) // 2
        assert analysis['score_difference'] == 65
        assert analysis['interpretation'] == "Significant Disagreements"
        # Consensus 62 means "DISCUSS FIRST" (50-69 range)
        assert "DISCUSS" in analysis['recommendation']

    def test_edge_case_missing_response_text(self):
        """Test edge case where response text is missing."""
        claude_result = {'score': 80}  # No 'response' key
        codex_result = {'score': 75}

        analysis = FastModerator.analyze(claude_result, codex_result)

        # Should still calculate consensus
        assert analysis['consensus_score'] == 77

        # Disagreements and agreements should be empty lists (no text to extract)
        assert isinstance(analysis['disagreements'], list)
        assert isinstance(analysis['agreements'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
