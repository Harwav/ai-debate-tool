"""
Unit tests for PromptOptimizer - Context extraction and prompt optimization.

Tests:
1. Extract relevant context from large file (scoring algorithm)
2. Focused prompt creation
3. Focus area inference from request
4. Section extraction from code
5. Context truncation to max_lines limit
"""

import pytest
import tempfile
from pathlib import Path
from ai_debate_tool.services.prompt_optimizer import PromptOptimizer


class TestPromptOptimizer:
    """Test suite for PromptOptimizer component."""

    @pytest.fixture
    def sample_file(self):
        """Create temporary Python file with various sections."""
        content = '''
"""
Module for order management.

This module handles order creation, validation, and processing.
"""

import django
from django.db import models


class OrderService:
    """Service for order business logic."""

    def create_order(self, data):
        """Create new order with validation."""
        # Validate customer
        if not data.get('customer'):
            raise ValueError("Customer required")

        # Create order
        order = Order.objects.create(**data)
        return order

    def validate_order(self, order):
        """Validate order data."""
        if not order.customer:
            return False
        if not order.material1:
            return False
        return True


class Order(models.Model):
    """Order model."""
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    material1 = models.ForeignKey('Material', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, default='new')


def helper_function():
    """Helper function."""
    pass


# Unrelated code
def unrelated():
    pass
'''

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_extract_relevant_context(self, sample_file):
        """Test extracting relevant context with focus areas."""
        # Focus on 'order' and 'service'
        focus_areas = ['order', 'service']

        context = PromptOptimizer.extract_relevant_context(
            sample_file,
            focus_areas,
            max_lines=20
        )

        # Should extract relevant sections (excerpt format with line ranges)
        assert 'Order' in context or 'OrderService' in context
        assert '[Lines' in context  # Excerpt format marker

        # Should be concise (not full file)
        line_count = len(context.split('\n'))
        assert line_count <= 50  # Much shorter than original file

    def test_focused_prompt_creation(self, sample_file):
        """Test creating focused prompt with extracted context."""
        request = "Review the order creation logic for bugs"
        focus_areas = ['order', 'create', 'validate']

        # First extract context
        context = PromptOptimizer.extract_relevant_context(
            sample_file,
            focus_areas,
            max_lines=15
        )

        # Then create focused prompt
        prompt = PromptOptimizer.create_focused_prompt(
            request,
            context,
            focus_areas
        )

        # Should contain request
        assert request in prompt

        # Should contain focus areas
        assert 'FOCUS ON' in prompt
        assert 'Order' in prompt or 'Create' in prompt

        # Should be concise (not entire file)
        assert len(prompt) < 2000  # Much shorter than full file

    def test_infer_focus_areas(self):
        """Test automatic focus area inference from request."""
        # Test refactoring focus
        request1 = "Refactor the order service to use transactions"
        focus1 = PromptOptimizer.infer_focus_areas(request1)
        assert 'refactoring' in focus1
        assert len(focus1) >= 1

        # Test database focus
        request2 = "Review the database schema migration"
        focus2 = PromptOptimizer.infer_focus_areas(request2)
        assert 'database' in focus2

        # Test UI focus
        request3 = "Check the order creation form validation"
        focus3 = PromptOptimizer.infer_focus_areas(request3)
        assert 'ui' in focus3

        # Test bug focus
        request4 = "Find race conditions in payment processing"
        focus4 = PromptOptimizer.infer_focus_areas(request4)
        assert 'bug' in focus4

        # Test generic (defaults to 'refactoring')
        request5 = "What does this code do?"
        focus5 = PromptOptimizer.infer_focus_areas(request5)
        assert 'refactoring' in focus5  # Default focus area

    def test_section_extraction(self, sample_file):
        """Test extracting code sections (functions/classes)."""
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = PromptOptimizer._extract_sections(content)

        # Should find classes
        class_sections = [s for s in sections if s['type'] == 'class']
        assert len(class_sections) >= 2  # OrderService, Order

        # Should find top-level functions (methods within classes not counted separately)
        function_sections = [s for s in sections if s['type'] == 'function']
        assert len(function_sections) >= 1  # helper_function at minimum

        # Each section should have required fields
        for section in sections:
            assert 'name' in section
            assert 'content' in section
            assert 'type' in section

    def test_context_truncation(self, sample_file):
        """Test that context respects max_lines limit."""
        focus_areas = ['order', 'service', 'model', 'validate']

        # Request very small limit
        context = PromptOptimizer.extract_relevant_context(
            sample_file,
            focus_areas,
            max_lines=10
        )

        line_count = len(context.split('\n'))

        # Should be close to limit (allow header/footer)
        assert line_count <= 15

        # Should still contain most relevant section
        # (OrderService is highest scored)
        assert 'OrderService' in context or 'Order' in context


class TestPromptOptimizerEdgeCases:
    """Test edge cases for PromptOptimizer."""

    def test_empty_file(self):
        """Test handling empty file."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write('')
            temp_path = f.name

        try:
            context = PromptOptimizer.extract_relevant_context(
                temp_path,
                ['test'],
                max_lines=10
            )

            # Should return empty or minimal context
            assert len(context) < 100
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_nonexistent_file(self):
        """Test handling nonexistent file."""
        context = PromptOptimizer.extract_relevant_context(
            'nonexistent_file.py',
            ['test'],
            max_lines=10
        )

        # Should return error message or empty
        assert 'error' in context.lower() or len(context) == 0

    def test_no_focus_areas(self, sample_file='test.py'):
        """Test extraction with no focus areas."""
        # Create sample file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write('def test(): pass')
            temp_path = f.name

        try:
            context = PromptOptimizer.extract_relevant_context(
                temp_path,
                [],  # No focus areas
                max_lines=10
            )

            # Should still extract something (top sections)
            assert len(context) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
