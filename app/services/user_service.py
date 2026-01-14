import random
import re
from decimal import Decimal

from fastapi import HTTPException
from app.cache.redis_client import cache_get, cache_set, redis_del, redis_incr

from app.core.security import create_access_token, get_password_hash, verify_password
from app.repositories.user_repo import UserRepository


class UserService:
    @staticmethod
    def _validate_password_strength(password: str) -> None:
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters and include a letter and a number",
            )

    @staticmethod
    def validate_password_strength(password: str) -> None:
        UserService._validate_password_strength(password)

    @staticmethod
    async def _invalidate_customer_profile_cache(user_id: int) -> None:
        await redis_del(f"customer:profile:{user_id}")

    @staticmethod
    async def register_customer(username: str, email: str, password: str):
        if await UserRepository.get_user_by_username(username):
            raise HTTPException(status_code=400, detail="Username already exists")

        if await UserRepository.get_user_by_email(email):
            raise HTTPException(status_code=400, detail="Email already exists")

        UserService._validate_password_strength(password)
        password_hash = get_password_hash(password)
        user_id = await UserRepository.create_user(username, email, password_hash)

        # Create a unique account number (retry a few times to avoid collisions).
        for _ in range(5):
            account_number = str(random.randint(1000000000, 9999999999))
            if not await UserRepository.get_customer_by_account_number(account_number):
                await UserRepository.create_account(user_id, account_number)
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate a unique account number")

        return {"status": "success", "message": "Customer registered successfully", "user_id": user_id}

    @staticmethod
    async def login_customer(username: str, password: str):
        rate_key = f"rl:customer_login:{username}"
        attempts = await redis_incr(rate_key, ttl=600)
        if attempts > 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

        user = await UserRepository.get_user_by_username(username)

        if not user or user.get("role") != "customer" or not verify_password(password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid customer credentials")

        # Check account status
        customer = await UserRepository.get_customer_profile_by_user_id(user["user_id"])
        if customer and customer.get("account_status") == "suspended":
            raise HTTPException(status_code=403, detail="Account is suspended")

        token = create_access_token(
            data={"sub": user["username"], "id": user["user_id"], "role": "customer"}
        )
        await redis_del(rate_key)
        return {"status": "success", "access_token": token, "token_type": "bearer"}

    @staticmethod
    async def get_customer_profile(user_id: int):
        cache_key = f"customer:profile:{user_id}"

        cached = await cache_get(cache_key)
        if cached:
            return cached

        profile = await UserRepository.get_customer_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Customer not found")

        await cache_set(cache_key, profile, ttl=120)  # 2 minutes cache
        return profile

    @staticmethod
    async def add_cash(account_number: str, amount: Decimal):
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        new_balance = await UserRepository.add_cash_by_account(account_number, amount)
        if new_balance is None:
            raise HTTPException(status_code=404, detail="Account not found")
        customer = await UserRepository.get_customer_by_account_number(account_number)
        if customer:
            await UserService._invalidate_customer_profile_cache(customer["user_id"])
        return {"status": "success", "new_balance": new_balance}


    @staticmethod
    async def withdraw_cash(account_number: str, amount: Decimal):
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        result = await UserRepository.withdraw_cash_by_account(account_number, amount)

        if result == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Account not found")

        if result == "INSUFFICIENT":
            raise HTTPException(status_code=400, detail="Insufficient funds")

        customer = await UserRepository.get_customer_by_account_number(account_number)
        if customer:
            await UserService._invalidate_customer_profile_cache(customer["user_id"])
        return {"status": "success", "new_balance": result}

    @staticmethod
    async def withdraw_cash_by_user_id(user_id: int, amount: Decimal):
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        result = await UserRepository.withdraw_cash_by_user_id(user_id, amount)

        if result == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Account not found")

        if result == "SUSPENDED":
            raise HTTPException(status_code=403, detail="Account is suspended")

        if result == "INSUFFICIENT":
            raise HTTPException(status_code=400, detail="Insufficient funds")

        await UserService._invalidate_customer_profile_cache(user_id)
        return {"status": "success", "new_balance": result}

    @staticmethod
    async def transfer_to_account(from_user_id: int, to_account_number: str, amount: Decimal):
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        result = await UserRepository.transfer_between_accounts(from_user_id, to_account_number, amount)

        if result == "NOT_FOUND":
            raise HTTPException(status_code=404, detail="Sender or recipient account not found")

        if result == "SUSPENDED":
            raise HTTPException(status_code=403, detail="Sender or recipient account is suspended")

        if result == "SAME_ACCOUNT":
            raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

        if result == "INSUFFICIENT":
            raise HTTPException(status_code=400, detail="Insufficient funds")

        await UserService._invalidate_customer_profile_cache(from_user_id)
        recipient = await UserRepository.get_customer_by_account_number(to_account_number)
        if recipient:
            await UserService._invalidate_customer_profile_cache(recipient["user_id"])

        return {"status": "success", "new_balance": result}

    @staticmethod
    async def get_transaction_history(user_id: int, limit: int = 50, offset: int = 0):
        if limit <= 0 or limit > 200:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 200")
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be >= 0")
        return await UserRepository.get_transaction_history_by_user_id(user_id, limit=limit, offset=offset)
