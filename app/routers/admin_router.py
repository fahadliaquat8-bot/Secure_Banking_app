from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from app.cache.redis_client import cache_get, cache_set

from app.core.security import ALGORITHM, SECRET_KEY, oauth2_scheme
from app.models.user import AccountStatusUpdate, OTPVerify, UserCreate, UserLogin, CustomerUpdate, CashDepositRequest
from app.services.admin_service import AdminService
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository

router = APIRouter(prefix="/admin", tags=["Admin Management"])


def verify_admin(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token required")

    try:
        token_str = token.replace("Bearer ", "") if "Bearer " in token else token
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin permission required")

        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ==================== AUTH ====================

@router.post("/login-initiate")
async def login_step_1(details: UserLogin):
    return await AdminService.login_step_1(details.username, details.password)


@router.post("/login-verify")
async def login_step_2(details: OTPVerify):
    return await AdminService.login_step_2(details.username, details.otp)


# ==================== CUSTOMER MANAGEMENT ====================

@router.post("/customers")
async def create_customer(details: UserCreate, admin=Depends(verify_admin)):
    # Admin creates customers (customers cannot self-register)
    return await UserService.register_customer(details.username, details.email, details.password)


@router.get("/customers")
async def get_customers(search: str = Query(None), admin=Depends(verify_admin)):
    if search:
        return await UserRepository.search_customers(search)
    return await UserRepository.get_all_customers()


@router.get("/customers/by-account/{account_number}")
async def get_customer_by_account(account_number: str, admin=Depends(verify_admin)):
    customer = await UserRepository.get_customer_by_account_number(account_number)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found for this account number")
    return customer


@router.post("/customers/add-cash")
async def add_cash_to_customer(payload: CashDepositRequest, admin=Depends(verify_admin)):
    result = await UserService.add_cash(payload.account_number, payload.amount)

    return {
        "status": "success",
        "message": "Cash added successfully",
        "account_number": payload.account_number,
        "amount_added": payload.amount,
        "new_balance": result["new_balance"],
    }


@router.put("/customers/{user_id}")
async def update_customer(user_id: int, details: CustomerUpdate, admin=Depends(verify_admin)):
    password_hash = None
    if details.password:
        UserService.validate_password_strength(details.password)
        from app.core.security import get_password_hash
        password_hash = get_password_hash(details.password)

    updated = await UserRepository.update_customer(
        user_id=user_id,
        username=details.username,
        email=details.email,
        password_hash=password_hash,
    )

    if not updated:
        raise HTTPException(status_code=400, detail="Customer not updated")
    return {"status": "success", "message": "Customer updated"}


@router.patch("/customers/{user_id}/status")
async def update_status(user_id: int, details: AccountStatusUpdate, admin=Depends(verify_admin)):
    updated = await UserRepository.update_account_status(user_id, details.status)
    if not updated:
        raise HTTPException(status_code=400, detail="Status not updated")
    return {"status": "success", "message": f"Account status updated to {details.status}"}


@router.delete("/customers/{user_id}")
async def delete_customer(user_id: int, admin=Depends(verify_admin)):
    deleted = await UserRepository.delete_customer(user_id)
    if not deleted:
        raise HTTPException(status_code=400, detail="Customer not deleted")
    return {"status": "success", "message": "Customer deleted"}


@router.get("/stats")
async def stats(admin=Depends(verify_admin)):
    cache_key = "admin:stats"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    data = await UserRepository.get_statistics()
    await cache_set(cache_key, data, ttl=30)  # 30 seconds cache
    return data
