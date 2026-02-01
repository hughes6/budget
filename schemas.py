from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class Data(BaseModel):
  'bucket is category of item money was spent on'
  'amount is usd amount of money spent'
  Bucket: str
  amount: float 