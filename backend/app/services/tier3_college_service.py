"""
Tier 3 College Service Orchestrator
Main service that coordinates web search + form automation for Tier 3 colleges.
"""

import asyncio
from typing import Optional, Dict
from app.services.tier3_web_search import get_tier3_web_search_service
from app.services.tier3_form_automation import get_tier3_form_automation_service


class Tier3CollegeService:
    """
    Orchestrates Tier 3 college lookup:
    1. Extract college details from user query
    2. Search web for NPC calculator link
    3. Fill form and extract NPC result
    """

    def __init__(self):
        self.web_search = get_tier3_web_search_service()
        self.form_automation = get_tier3_form_automation_service()

    async def lookup_npc(self, user_query: str) -> Dict:
        """
        Complete Tier 3 NPC lookup workflow.
        
        Args:
            user_query: User's question about college NPC
        
        Returns:
            {
                "college_name": str,
                "marks": int | None,
                "category": str,
                "npc": float | None,
                "eligible": bool | None,
                "remarks": str | None,
                "status": "success" | "partial" | "failed",
                "message": str
            }
        """
        try:
            # Step 1: Extract college details from query
            details = await self.web_search.extract_college_details(user_query)
            
            if not details["college_name"]:
                return {
                    "status": "failed",
                    "message": "Could not identify college name from your query. Please mention the college name clearly."
                }
            
            # Step 2: Search for NPC calculator link
            search_result = await self.web_search.search_college_npc(
                details["college_name"],
                state=None
            )
            
            if search_result["status"] == "error" or not search_result["npc_url"]:
                return {
                    "college_name": details["college_name"],
                    "status": "partial",
                    "message": f"Could not find NPC calculator for {details['college_name']}. Please visit their official website directly."
                }
            
            # If no marks provided, return calculator link
            if not details["marks"]:
                return {
                    "college_name": details["college_name"],
                    "marks": None,
                    "npc": None,
                    "status": "partial",
                    "message": f"Found {details['college_name']} NPC Calculator: {search_result['npc_url']}\n\nPlease provide your marks to calculate NPC."
                }
            
            # Step 3: Fill form and extract NPC
            npc_result = await self.form_automation.calculate_npc(
                search_result["npc_url"],
                marks=details["marks"],
                category=details["category"],
                college_name=details["college_name"]
            )
            
            return {
                "college_name": details["college_name"],
                "marks": details["marks"],
                "category": details["category"],
                "npc": npc_result.get("npc"),
                "eligible": npc_result.get("eligible"),
                "remarks": npc_result.get("remarks"),
                "status": "success" if npc_result["success"] else "partial",
                "message": npc_result.get("error") or f"NPC calculation completed for {details['college_name']}"
            }
        
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Tier 3 lookup error: {str(e)}"
            }

    def format_result_for_llm(self, tier3_result: Dict) -> str:
        """
        Format Tier 3 result as context string for LLM.
        """
        if tier3_result["status"] == "failed":
            return f"NOTE: Could not complete Tier 3 college lookup. {tier3_result.get('message', '')}"
        
        if tier3_result["status"] == "partial":
            return f"TIER 3 COLLEGE DATA: {tier3_result.get('message', 'Lookup in progress...')}"
        
        # Success case
        result_text = f"""TIER 3 COLLEGE CALCULATION RESULT:
College: {tier3_result.get('college_name', 'N/A')}
Marks: {tier3_result.get('marks', 'N/A')}
Category: {tier3_result.get('category', 'OPEN')}
NPC Score: {tier3_result.get('npc', 'Not calculated')}
Eligible: {tier3_result.get('eligible', 'Unknown')}
Remarks: {tier3_result.get('remarks', 'N/A')}"""
        
        return result_text


_tier3_service: Optional[Tier3CollegeService] = None

def get_tier3_college_service() -> Tier3CollegeService:
    global _tier3_service
    if _tier3_service is None:
        _tier3_service = Tier3CollegeService()
    return _tier3_service
