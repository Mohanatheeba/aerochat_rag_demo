"""
Tier 3 Form Automation Service
Automates NPC calculator form filling and result extraction.

Uses Selenium with headless Chrome to navigate college websites
and fill NPC calculator forms.
"""

import asyncio
import time
from typing import Optional, Dict, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class Tier3FormAutomationService:
    """
    Automates college NPC calculator form filling and result extraction.
    """

    def __init__(self):
        self.timeout = 10  # seconds
        self.headless = True  # Run in headless mode for faster execution

    def _get_chrome_driver(self):
        """
        Initialize Selenium WebDriver with Chrome options.
        """
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-resources")
        chrome_options.add_argument("--disable-extensions")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver

    async def calculate_npc(
        self,
        npc_url: str,
        marks: Optional[int] = None,
        category: str = "OPEN",
        college_name: str = ""
    ) -> Dict:
        """
        Fill NPC calculator form and extract result.
        
        Args:
            npc_url: URL of the NPC calculator
            marks: Student's marks/score
            category: Category (OPEN, OBC, SC, ST, EWS, PWD)
            college_name: College name for context
        
        Returns:
            {
                "success": bool,
                "npc": float | None,
                "remarks": str | None,
                "eligible": bool | None,
                "error": str | None
            }
        """
        driver = None
        try:
            driver = self._get_chrome_driver()
            driver.set_page_load_timeout(self.timeout)
            
            # Navigate to NPC calculator
            driver.get(npc_url)
            wait = WebDriverWait(driver, self.timeout)
            
            # Try to fill form with different field detection strategies
            result = await self._fill_and_extract(driver, wait, marks, category)
            
            return result
        
        except Exception as e:
            return {
                "success": False,
                "npc": None,
                "remarks": None,
                "eligible": None,
                "error": f"Form automation failed: {str(e)}"
            }
        
        finally:
            if driver:
                driver.quit()

    async def _fill_and_extract(
        self,
        driver,
        wait,
        marks: Optional[int],
        category: str
    ) -> Dict:
        """
        Attempt to fill form fields and extract NPC result.
        Tries multiple strategies to handle different form structures.
        """
        
        # Strategy 1: Find by common input field patterns
        form_fields = self._find_form_fields(driver)
        
        if form_fields:
            # Fill marks/score field
            if marks and "marks_field" in form_fields:
                try:
                    field = driver.find_element(*form_fields["marks_field"])
                    field.clear()
                    field.send_keys(str(marks))
                except Exception:
                    pass
            
            # Fill category field
            if "category_field" in form_fields:
                try:
                    select_elem = Select(driver.find_element(*form_fields["category_field"]))
                    select_elem.select_by_visible_text(category)
                except Exception:
                    pass
            
            # Try to click submit button
            if "submit_button" in form_fields:
                try:
                    submit_btn = driver.find_element(*form_fields["submit_button"])
                    submit_btn.click()
                    # Wait for result to load
                    await asyncio.sleep(2)
                except Exception:
                    pass
        
        # Extract result from page
        result_text = driver.page_source
        soup = BeautifulSoup(result_text, "html.parser")
        
        npc, remarks = self._extract_npc_result(soup)
        
        return {
            "success": npc is not None,
            "npc": npc,
            "remarks": remarks,
            "eligible": npc is not None,
            "error": None if npc else "Could not extract NPC result from page"
        }

    def _find_form_fields(self, driver) -> Dict:
        """
        Detect common form field patterns for NPC calculators.
        """
        fields = {}
        
        # Look for input fields (marks/score)
        for input_elem in driver.find_elements(By.TAG_NAME, "input"):
            input_id = input_elem.get_attribute("id") or ""
            input_name = input_elem.get_attribute("name") or ""
            input_type = input_elem.get_attribute("type") or ""
            
            if any(kw in input_id.lower() + input_name.lower() for kw in ["marks", "score", "rank", "percentile"]):
                fields["marks_field"] = (By.ID, input_id) if input_id else (By.NAME, input_name)
                break
        
        # Look for select fields (category)
        for select_elem in driver.find_elements(By.TAG_NAME, "select"):
            select_id = select_elem.get_attribute("id") or ""
            select_name = select_elem.get_attribute("name") or ""
            
            if any(kw in select_id.lower() + select_name.lower() for kw in ["category", "quota", "stream"]):
                fields["category_field"] = (By.ID, select_id) if select_id else (By.NAME, select_name)
                break
        
        # Look for submit button
        for button in driver.find_elements(By.TAG_NAME, "button"):
            button_text = button.text.lower()
            if any(kw in button_text for kw in ["submit", "calculate", "check", "result"]):
                fields["submit_button"] = (By.XPATH, f"//button[contains(text(), '{button.text}')]")
                break
        
        # Also try form submission
        forms = driver.find_elements(By.TAG_NAME, "form")
        if forms and "submit_button" not in fields:
            fields["submit_button"] = (By.TAG_NAME, "form")
        
        return fields

    def _extract_npc_result(self, soup: BeautifulSoup) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract NPC value and remarks from page HTML.
        Looks for common patterns in college NPC calculator results.
        """
        
        # Common result patterns to search for
        result_patterns = ["npc", "normalised", "score", "result", "merit"]
        remarks_patterns = ["eligible", "merit", "rank", "remark", "status", "admit"]
        
        npc_value = None
        remarks = None
        
        # Search for text containing NPC value
        text = soup.get_text()
        
        import re
        
        # Try to find NPC value (usually a number with decimal)
        npc_match = re.search(r'NPC\s*[:\-]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if npc_match:
            npc_value = float(npc_match.group(1))
        
        # Also try to find any number pattern near result-like text
        if not npc_value:
            for pattern in result_patterns:
                match = re.search(rf'{pattern}\s*[:\-]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
                if match:
                    npc_value = float(match.group(1))
                    break
        
        # Extract remarks/status
        for pattern in remarks_patterns:
            match = re.search(rf'{pattern}\s*[:\-]?\s*([^.\n]+)', text, re.IGNORECASE)
            if match:
                remarks = match.group(1).strip()
                if remarks:
                    break
        
        return npc_value, remarks


_form_automation_service: Optional[Tier3FormAutomationService] = None

def get_tier3_form_automation_service() -> Tier3FormAutomationService:
    global _form_automation_service
    if _form_automation_service is None:
        _form_automation_service = Tier3FormAutomationService()
    return _form_automation_service
