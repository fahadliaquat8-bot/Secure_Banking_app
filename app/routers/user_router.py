from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt

from app.core.security import ALGORITHM, SECRET_KEY, oauth2_scheme
from app.models.user import CashWithdrawAmountRequest, TransferRequest, UserLogin
from app.services.user_service import UserService

router = APIRouter(prefix="/customers", tags=["Customer"])


def verify_customer(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token required")

    try:
        token_str = token.replace("Bearer ", "") if "Bearer " in token else token
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("role") != "customer":
            raise HTTPException(status_code=403, detail="Customer permission required")

        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/login")
async def login(details: UserLogin):
    return await UserService.login_customer(details.username, details.password)


@router.get("/profile")
async def profile(customer=Depends(verify_customer)):
    user_id = customer.get("id")
    return await UserService.get_customer_profile(user_id)


@router.post("/withdraw")
async def withdraw(payload: CashWithdrawAmountRequest, customer=Depends(verify_customer)):
    user_id = customer.get("id")
    return await UserService.withdraw_cash_by_user_id(user_id, payload.amount)


@router.post("/transfer")
async def transfer(payload: TransferRequest, customer=Depends(verify_customer)):
    user_id = customer.get("id")
    return await UserService.transfer_to_account(user_id, payload.to_account_number, payload.amount)


@router.get("/transactions")
async def transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    customer=Depends(verify_customer),
):
    user_id = customer.get("id")
    return await UserService.get_transaction_history(user_id, limit=limit, offset=offset)
