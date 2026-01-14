from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class OTPVerify(BaseModel):
    username: str
    otp: str = Field(..., min_length=6, max_length=6)


class CustomerUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class AccountStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class CustomerProfileResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    role: str
    account_created_at: Optional[datetime] = None
    account_number: Optional[str] = None
    current_balance: Optional[Decimal] = None
    account_status: Optional[str] = None


class CashDepositRequest(BaseModel):
    account_number: str = Field(..., min_length=6, max_length=30)
    amount: Decimal = Field(..., gt=0)


class CashWithdrawRequest(BaseModel):
    account_number: str = Field(..., min_length=6, max_length=30)
    amount: Decimal = Field(..., gt=0)


class CashWithdrawAmountRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


class TransferRequest(BaseModel):
    to_account_number: str = Field(..., min_length=6, max_length=30)
    amount: Decimal = Field(..., gt=0)


class TransactionHistoryItem(BaseModel):
    transaction_id: int
    account_number: str
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    related_account: Optional[str] = None
    created_at: datetime

