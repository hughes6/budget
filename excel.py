import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BudgetExcelParser:
    """Simple Excel parser for budget spreadsheet"""
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.df = None
    
    def load_sheet(self) -> bool:
        """Load the Budget sheet from Excel"""
        try:
            self.df = pd.read_excel(self.excel_path, sheet_name='Sheet2', header=None)
            logger.info(f"Loaded Excel with shape: {self.df.shape}")
            return True
        except Exception as e:
            logger.error(f"Failed to load Excel: {e}")
            return False
    
    def _get_cell_value(self, row: int, col: int, default=None):
        """Safely get cell value"""
        try:
            if row < len(self.df) and col < len(self.df.columns):
                value = self.df.iloc[row, col]
                if pd.isna(value):
                    return default
                return value
        except:
            pass
        return default
    
    def get_main_buckets(self) -> List[Dict]:
        """Get main buckets from A2:B10"""
        buckets = []
        for i in range(1, 10):  # Rows 2-10
            name = self._get_cell_value(i, 0)  # Column A
            amount = self._get_cell_value(i, 1)  # Column B
            
            if name and amount is not None:
                buckets.append({
                    'bucket': str(name).strip(),
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(buckets)} main buckets")
        return buckets
    
    def get_envelopes(self) -> List[Dict]:
        """Get envelope savings from D3:E4"""
        envelopes = []
        for i in range(2, 3):  # Rows 3-6
            name = self._get_cell_value(i, 3)  # Column D
            amount = self._get_cell_value(i, 4)  # Column E
            
            if name and amount is not None:
                envelopes.append({
                    'bucket': f"Envelope - {str(name).strip()}",
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(envelopes)} envelopes")
        return envelopes
    
    def get_subscriptions(self) -> List[Dict]:
        """Get subscriptions from J2:K15"""
        subs = []
        for i in range(1, 15):  # Rows 2-15
            name = self._get_cell_value(i, 9)  # Column J
            amount = self._get_cell_value(i, 10)  # Column K
            
            if name and amount is not None:
                subs.append({
                    'bucket': f"Subscription - {str(name).strip()}",
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(subs)} subscriptions")
        return subs
    
    def get_insurance(self) -> List[Dict]:
        """Get insurance from M2:N6"""
        insurance = []
        for i in range(1, 6):  # Rows 2-6
            name = self._get_cell_value(i, 12)  # Column M
            amount = self._get_cell_value(i, 13)  # Column N
            
            if name and amount is not None:
                insurance.append({
                    'bucket': f"Insurance - {str(name).strip()}",
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(insurance)} insurance items")
        return insurance
    
    def get_investments(self) -> List[Dict]:
        """Get investments from P2:Q4"""
        investments = []
        for i in range(1, 4):  # Rows 2-3
            name = self._get_cell_value(i, 15)  # Column P
            amount = self._get_cell_value(i, 16)  # Column Q
            
            if name and amount is not None:
                investments.append({
                    'bucket': f"Investment - {str(name).strip()}",
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(investments)} investments")
        return investments
    
    def get_education(self) -> List[Dict]:
        """Get education from S2:T3"""
        education = []
        for i in range(1, 3):  # Rows 2-3
            name = self._get_cell_value(i, 18)  # Column S
            amount = self._get_cell_value(i, 19)  # Column T
            
            if name and amount is not None:
                education.append({
                    'bucket': f"Education - {str(name).strip()}",
                    'amount': float(amount)
                })
        
        logger.info(f"Parsed {len(education)} education items")
        return education
    
    def get_all_budget_items(self) -> List[Dict]:
        """Get all budget items combined"""
        all_items = []
        all_items.extend(self.get_main_buckets())
        all_items.extend(self.get_envelopes())
        all_items.extend(self.get_subscriptions())
        all_items.extend(self.get_insurance())
        all_items.extend(self.get_investments())
        all_items.extend(self.get_education())
        
        logger.info(f"Total {len(all_items)} budget items parsed")
        return all_items