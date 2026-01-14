import os
import random
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException

from app.cache.redis_client import redis_del, redis_incr
from app.core.security import create_access_token, verify_password
from app.repositories.user_repo import UserRepository

# Force-load .env from project root (../../.env from this file)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


class AdminService:
    @staticmethod
    def send_otp_email(to_email: str, otp: str) -> None:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_address = os.getenv("SMTP_EMAIL")
        email_password = os.getenv("SMTP_PASSWORD")

        if not email_address or not email_password:
            raise HTTPException(status_code=500, detail="Email service is not configured")

        msg = EmailMessage()
        msg["Subject"] = "Your Admin OTP Code"
        msg["From"] = email_address
        msg["To"] = to_email
        msg.set_content(f"Your OTP code is: {otp}\n\nThis OTP expires in 5 minutes.")

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(email_address, email_password)
                smtp.send_message(msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send OTP email: {e}")

    @staticmethod
    async def login_step_1(username: str, password: str):
        rate_key = f"rl:admin_login:{username}"
        attempts = await redis_incr(rate_key, ttl=600)
        if attempts > 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

        user = await UserRepository.get_user_by_username(username)

        if not user or user.get("role") != "admin" or not verify_password(password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid admin credentials")

        otp = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        await UserRepository.update_user_otp(
            user_id=user["user_id"],
            otp_code=otp,
            otp_expires_at=expires_at,
            reset_attempts=True,
        )

        AdminService.send_otp_email(user["email"], otp)
        await redis_del(rate_key)

        return {
            "status": "success",
            "message": "OTP sent (valid for 5 minutes)",
            "email": user["email"],
        }

    @staticmethod
    async def login_step_2(username: str, otp: str):
        rate_key = f"rl:admin_otp:{username}"
        attempts = await redis_incr(rate_key, ttl=600)
        if attempts > 10:
            raise HTTPException(status_code=429, detail="Too many OTP attempts. Try again later.")

        user = await UserRepository.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid OTP")

        if not user.get("otp_code") or not user.get("otp_expires_at"):
            raise HTTPException(status_code=401, detail="OTP not found or expired. Request a new OTP.")

        attempts = user.get("otp_attempts", 0)
        if attempts >= 5:
            await UserRepository.update_user_otp(user["user_id"], None)
            raise HTTPException(status_code=429, detail="Too many wrong OTP attempts. Request a new OTP.")

        now = datetime.utcnow()
        expires_at = user["otp_expires_at"]

        if isinstance(expires_at, str):
            try:
                expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                await UserRepository.update_user_otp(user["user_id"], None)
                raise HTTPException(status_code=401, detail="OTP expired. Request a new OTP.")

        if now > expires_at:
            await UserRepository.update_user_otp(user["user_id"], None)
            raise HTTPException(status_code=401, detail="OTP expired. Request a new OTP.")

        if user["otp_code"] != otp:
            await UserRepository.increment_otp_attempts(user["user_id"])
            raise HTTPException(status_code=401, detail="Invalid OTP")

        await UserRepository.update_user_otp(user["user_id"], None)

        token = create_access_token(data={"sub": user["username"], "id": user["user_id"], "role": "admin"})
        await redis_del(rate_key)
        return {"status": "success", "access_token": token, "token_type": "bearer"}
