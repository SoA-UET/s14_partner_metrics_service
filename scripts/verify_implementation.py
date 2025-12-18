"""
Quick verification script to check if all imports work correctly.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        print("  Importing MessageQueueService...")
        from app.services.MessageQueueService import MessageQueueService
        print("  ✓ MessageQueueService imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import MessageQueueService: {e}")
        return False
    
    try:
        print("  Importing PartnerMetricsService...")
        from app.services.PartnerMetricsService import PartnerMetricsService
        print("  ✓ PartnerMetricsService imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import PartnerMetricsService: {e}")
        return False
    
    try:
        print("  Importing auth utilities...")
        from app.utils.auth import verify_jwt, require_auth, get_jwks_manager
        print("  ✓ Auth utilities imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import auth utilities: {e}")
        return False
    
    try:
        print("  Importing partner_metrics controller...")
        from app.controllers.v1.partner_metrics import partner_metrics_bp
        print("  ✓ Partner metrics controller imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import partner_metrics controller: {e}")
        return False
    
    try:
        print("  Importing v1 blueprint...")
        from app.controllers.v1 import v1
        print("  ✓ V1 blueprint imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import v1 blueprint: {e}")
        return False
    
    try:
        print("  Importing controllers...")
        from app.controllers import register_api_controllers
        print("  ✓ Controllers imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import controllers: {e}")
        return False
    
    print("\n✓ All imports successful!")
    return True


def test_structure():
    """Test that the service structure is correct."""
    print("\nTesting service structure...")
    
    # Check required files exist
    required_files = [
        'app/__main__.py',
        'app/services/PartnerMetricsService.py',
        'app/services/MessageQueueService.py',
        'app/controllers/v1/partner_metrics.py',
        'app/utils/auth.py',
        '.env.example',
        'pyproject.toml',
        'README.md'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ Missing: {file}")
            all_exist = False
    
    if all_exist:
        print("\n✓ All required files present!")
        return True
    else:
        print("\n✗ Some files are missing")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("S14 Partner Metrics Service - Verification Script")
    print("=" * 60)
    
    # Test structure
    structure_ok = test_structure()
    
    # Test imports
    imports_ok = test_imports()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Structure check: {'✓ PASS' if structure_ok else '✗ FAIL'}")
    print(f"Import check:    {'✓ PASS' if imports_ok else '✗ FAIL'}")
    
    if structure_ok and imports_ok:
        print("\n✓ All verification checks passed!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your settings")
        print("2. Install dependencies: uv pip install -e .")
        print("3. Run the service: python -m app")
        return 0
    else:
        print("\n✗ Some verification checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
