"""
Tier 3 College Web Search Service
Searches the web for Tier 3 college NPC calculator links.

This service handles colleges not found in the knowledge base (Tier 1/2).
It performs web search to find the college's NPC calculator link.
"""

import asyncio
import httpx
from typing import Optional, Dict, List
from bs4 import BeautifulSoup


class Tier3WebSearchService:
    """
    Searches web for Tier 3 college NPC calculator URLs.
    """

    def __init__(self):
        # Popular college NPC calculator patterns
        self.npc_patterns = [
            "npc calculator",
            "normalised marks calculator",
            "merit score calculator",
            "admission calculator"
        ]
        
        # Popular college websites (hardcoded for faster lookup)
        self.known_colleges = {
            "bits pilani": "https://www.bitsat.ac.in/",
            "vit": "https://www.vit.ac.in/",
            "manipal": "https://www.manipal.edu/",
            "srm": "https://www.srmist.edu.in/",
            "amrita": "https://www.amrita.edu/",
            "jain": "https://www.jainedu.ac.in/",
            "lovely professional": "https://www.lpu.in/",
            "chandigarh": "https://www.cuchd.in/",
            "christ": "https://christuniversity.in/",
            "symbiosis": "https://www.admissions.symbiosis.ac.in/"
        }

    async def search_college_npc(
        self,
        college_name: str,
        state: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Search for a college's NPC calculator link.
        
        Args:
            college_name: Name of the college to search
            state: Optional state name for more specific results
        
        Returns:
            {
                "college_name": str,
                "npc_url": str | None,
                "website": str | None,
                "status": "found" | "not_found" | "error"
            }
        """
        try:
            college_clean = college_name.lower().strip()
            
            # Check known colleges first
            for known_name, website in self.known_colleges.items():
                if known_name in college_clean:
                    npc_url = await self._find_npc_url(website, college_name)
                    return {
                        "college_name": college_name,
                        "npc_url": npc_url,
                        "website": website,
                        "status": "found" if npc_url else "not_found"
                    }
            
            # Fallback to web search
            search_query = f"{college_name} npc calculator"
            if state:
                search_query += f" {state}"
            
            result_url, npc_url = await self._google_search(search_query)
            
            return {
                "college_name": college_name,
                "npc_url": npc_url,
                "website": result_url,
                "status": "found" if npc_url else "not_found"
            }
        
        except Exception as e:
            return {
                "college_name": college_name,
                "npc_url": None,
                "website": None,
                "status": "error",
                "error": str(e)
            }

    async def _find_npc_url(self, website: str, college_name: str) -> Optional[str]:
        """
        Crawl website to find NPC calculator link.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(website)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for links containing NPC keywords
            for link in soup.find_all("a", href=True):
                link_text = link.get_text().lower()
                link_href = link["href"]
                
                # Check if link matches NPC calculator patterns
                for pattern in self.npc_patterns:
                    if pattern in link_text:
                        # Convert relative URLs to absolute
                        if link_href.startswith("/"):
                            if website.endswith("/"):
                                return website + link_href[1:]
                            return website + link_href
                        elif link_href.startswith("http"):
                            return link_href
            
            return None
        
        except Exception:
            return None

    async def _google_search(self, query: str) -> tuple[Optional[str], Optional[str]]:
        """
        Perform a Google search for the query.
        Returns (first_result_url, npc_calculator_url_if_found)
        
        Note: This uses a simple approach. For production, consider using
        a dedicated search API like SerpAPI or custom search engine.
        """
        try:
            # Using DuckDuckGo as fallback (doesn't require API key)
            search_url = f"https://duckduckgo.com/search?q={query}&ia=web"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract first result
            first_result = None
            npc_result = None
            
            for link in soup.find_all("a", {"class": "result__url"}):
                href = link.get("href")
                if href:
                    # Clean up DuckDuckGo URL encoding
                    if href.startswith("/url?q="):
                        href = href.replace("/url?q=", "").split("&")[0]
                    
                    if not first_result:
                        first_result = href
                    
                    # Prioritize NPC calculator links
                    if "npc" in link.get_text().lower():
                        npc_result = href
                        break
            
            return (first_result, npc_result or first_result)
        
        except Exception:
            return (None, None)

    async def extract_college_details(self, user_query: str) -> Dict:
        """
        Extract college name, marks, category from user query.
        
        Example queries:
        - "What's the NPC for BITS Pilani with 450 marks?"
        - "VIT Engineering with 95%ile rank?"
        - "Manipal CSE with 600 marks, open category"
        """
        query_lower = user_query.lower()
        
        college_name = None
        marks = None
        category = None
        
        # Extract college name (very basic - improve with NLP in future)
        colleges = list(self.known_colleges.keys())
        for college in colleges:
            if college in query_lower:
                college_name = college.title()
                break
        
        # Extract marks (look for numbers followed by marks/score keywords)
        import re
        marks_match = re.search(r'(\d{2,3})\s*(marks|score|out of)', query_lower)
        if marks_match:
            marks = int(marks_match.group(1))
        
        # Extract category
        categories = ["open", "obc", "sc", "st", "ews", "pwd"]
        for cat in categories:
            if cat in query_lower:
                category = cat.upper()
                break
        
        return {
            "college_name": college_name,
            "marks": marks,
            "category": category or "OPEN",
            "raw_query": user_query
        }


_tier3_search_service: Optional[Tier3WebSearchService] = None

def get_tier3_web_search_service() -> Tier3WebSearchService:
    global _tier3_search_service
    if _tier3_search_service is None:
        _tier3_search_service = Tier3WebSearchService()
    return _tier3_search_service
