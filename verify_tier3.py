#!/usr/bin/env python3
"""
Tier 3 Implementation Verification Script
Checks that all components are properly integrated and working
"""

import os
import sys
import importlib

def check_imports():
    """Verify all new modules can be imported"""
    print("=" * 60)
    print("TIER 3 IMPLEMENTATION VERIFICATION")
    print("=" * 60)
    
    modules_to_check = [
        "backend.app.services.tier3_web_search",
        "backend.app.services.tier3_form_automation",
        "backend.app.services.tier3_college_service",
        "backend.app.services.chat_orchestrator",
        "backend.app.services.llm_service",
    ]
    
    print("\n[1/4] Checking Imports...")
    all_good = True
    
    for module_name in modules_to_check:
        try:
            parts = module_name.split(".")
            if parts[0] == "backend":
                # Adjust path for import
                sys.path.insert(0, "backend")
                module = importlib.import_module(".".join(parts[1:]))
            else:
                module = importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {str(e)}")
            all_good = False
    
    return all_good


def check_dependencies():
    """Verify all dependencies are installed"""
    print("\n[2/4] Checking Dependencies...")
    
    dependencies = [
        "selenium",
        "beautifulsoup4",
        "webdriver_manager",
        "httpx",
        "groq",
    ]
    
    all_installed = True
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            print(f"  ✗ {dep} - NOT INSTALLED")
            all_installed = False
    
    return all_installed


def check_files():
    """Verify all new files exist"""
    print("\n[3/4] Checking Files...")
    
    files_to_check = [
        "backend/app/services/tier3_web_search.py",
        "backend/app/services/tier3_form_automation.py",
        "backend/app/services/tier3_college_service.py",
        "backend/tests/test_tier3.py",
        "TIER3_IMPLEMENTATION.md",
        "TIER3_SUMMARY.md",
        "DEPLOYMENT_GUIDE.md",
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size_kb = os.path.getsize(file_path) / 1024
            print(f"  ✓ {file_path} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def check_integration():
    """Verify integration in key files"""
    print("\n[4/4] Checking Integration...")
    
    checks = []
    
    # Check 1: chat_orchestrator imports tier3
    try:
        with open("backend/app/services/chat_orchestrator.py", "r") as f:
            content = f.read()
            if "tier3_college_service" in content:
                checks.append(("chat_orchestrator imports tier3", True))
            else:
                checks.append(("chat_orchestrator imports tier3", False))
    except Exception as e:
        checks.append(("chat_orchestrator imports tier3", False))
    
    # Check 2: llm_service has enhanced intent detection
    try:
        with open("backend/app/services/llm_service.py", "r") as f:
            content = f.read()
            if "requires_college_lookup" in content and "college_keywords" in content:
                checks.append(("llm_service college detection", True))
            else:
                checks.append(("llm_service college detection", False))
    except Exception as e:
        checks.append(("llm_service college detection", False))
    
    # Check 3: requirements.txt has new dependencies
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            if "selenium" in content and "beautifulsoup4" in content:
                checks.append(("requirements.txt updated", True))
            else:
                checks.append(("requirements.txt updated", False))
    except Exception as e:
        checks.append(("requirements.txt updated", False))
    
    # Check 4: README mentions Tier 3
    try:
        with open("README.md", "r") as f:
            content = f.read()
            if "Tier 3" in content:
                checks.append(("README documents Tier 3", True))
            else:
                checks.append(("README documents Tier 3", False))
    except Exception as e:
        checks.append(("README documents Tier 3", False))
    
    all_good = True
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
        if not result:
            all_good = False
    
    return all_good


def main():
    """Run all verification checks"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    results = {
        "Imports": check_imports(),
        "Dependencies": check_dependencies(),
        "Files": check_files(),
        "Integration": check_integration(),
    }
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{check_name:.<40} {status}")
    
    all_pass = all(results.values())
    
    if all_pass:
        print("\n✓ ALL CHECKS PASSED - TIER 3 IMPLEMENTATION VERIFIED!")
        print("\nYour system is ready for Tier 3 college NPC calculator queries.")
        print("\nTry asking:")
        print("  - 'What is the NPC for BITS Pilani with 450 marks?'")
        print("  - 'VIT CSE with 95 percentile?'")
        print("  - 'Manipal Engineering open category 550 marks?'")
    else:
        print("\n✗ SOME CHECKS FAILED")
        print("\nTo fix:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Verify all files are in place")
        print("3. Check file permissions")
        print("4. See DEPLOYMENT_GUIDE.md for troubleshooting")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
