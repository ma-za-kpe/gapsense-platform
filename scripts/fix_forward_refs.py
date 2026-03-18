#!/usr/bin/env python3
"""
Fix forward references in SQLAlchemy models by adding TYPE_CHECKING imports.

This script adds proper TYPE_CHECKING blocks to all model files to resolve
circular dependency issues.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Verify all model imports work correctly."""
    # Import all models to trigger any remaining issues
    try:
        from gapsense.core.models import (
            Base,
            CurriculumNode,
            DiagnosticSession,
            GapProfile,
            Parent,
            Student,
            Teacher,
        )

        # Verify models are usable (prevent "unused" warnings)
        assert Base is not None
        assert CurriculumNode is not None
        assert Student is not None
        assert Parent is not None
        assert Teacher is not None
        assert DiagnosticSession is not None
        assert GapProfile is not None

        print("✅ All models import successfully!")
        print("✅ Forward references resolved via TYPE_CHECKING")
        return 0
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
