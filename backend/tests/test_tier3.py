"""
Test suite for Tier 3 College functionality
Tests web search, form automation, and orchestration
"""

import asyncio
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.tier3_web_search import get_tier3_web_search_service
from app.services.tier3_college_service import get_tier3_college_service


async def test_college_detail_extraction():
    """Test extraction of college details from user query"""
    service = get_tier3_web_search_service()
    
    # Test case 1: Full query
    details = await service.extract_college_details(
        "What is the NPC for VIT with 95 percentile marks, open category?"
    )
    assert details["college_name"] is not None, "Should extract college name"
    assert details["category"] == "OPEN", "Should extract category"
    print("✓ Full query extraction passed")
    
    # Test case 2: With marks
    details = await service.extract_college_details(
        "BITS Pilani with 450 marks"
    )
    assert details["marks"] == 450, "Should extract marks"
    assert details["college_name"] is not None, "Should extract college"
    print("✓ Marks extraction passed")
    
    # Test case 3: With category
    details = await service.extract_college_details(
        "Manipal CSE SC category"
    )
    assert details["category"] == "SC", "Should extract SC category"
    print("✓ Category extraction passed")


async def test_known_college_search():
    """Test searching for known colleges"""
    service = get_tier3_web_search_service()
    
    result = await service.search_college_npc("BITS Pilani")
    assert result["status"] in ["found", "not_found", "error"], "Should have valid status"
    assert result["college_name"] == "BITS Pilani", "Should preserve college name"
    print("✓ Known college search passed")


async def test_fallback_on_missing_marks():
    """Test fallback behavior when marks are not provided"""
    service = get_tier3_college_service()
    
    result = await service.lookup_npc("Tell me about VIT")
    
    # Should return partial result with calculator link
    assert result["status"] in ["partial", "success"], "Should have valid status"
    assert "message" in result, "Should include message"
    print("✓ Fallback on missing marks passed")


def test_result_formatting_for_llm():
    """Test formatting of Tier 3 results for LLM consumption"""
    service = get_tier3_college_service()
    
    # Test success formatting
    result = {
        "status": "success",
        "college_name": "BITS Pilani",
        "marks": 450,
        "npc": 245.5,
        "eligible": True,
        "message": "NPC calculation completed"
    }
    formatted = service.format_result_for_llm(result)
    assert "BITS Pilani" in formatted, "Should include college name"
    assert "245.5" in formatted, "Should include NPC"
    print("✓ Success result formatting passed")
    
    # Test failure formatting
    result_failed = {
        "status": "failed",
        "message": "No college found"
    }
    formatted_failed = service.format_result_for_llm(result_failed)
    assert "No college found" in formatted_failed, "Should include error message"
    print("✓ Failed result formatting passed")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Tier 3 College Functionality Tests")
    print("=" * 60)
    
    try:
        print("\n[1/4] Testing College Detail Extraction...")
        await test_college_detail_extraction()
        
        print("\n[2/4] Testing Known College Search...")
        await test_known_college_search()
        
        print("\n[3/4] Testing Fallback on Missing Marks...")
        await test_fallback_on_missing_marks()
        
        print("\n[4/4] Testing Result Formatting for LLM...")
        test_result_formatting_for_llm()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
