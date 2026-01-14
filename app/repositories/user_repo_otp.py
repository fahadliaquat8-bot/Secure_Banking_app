from datetime import datetime

import aiomysql

from app.database.database import db


class UserRepoOtpMixin:
    @staticmethod
    async def update_user_otp(
        user_id: int,
        otp_code: str | None,
        otp_expires_at: datetime | None = None,
        reset_attempts: bool = False,
    ):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                if otp_code is None:
                    await cur.execute(
                        """
                        UPDATE users
                        SET otp_code = NULL,
                            otp_expires_at = NULL,
                            otp_attempts = 0
                        WHERE user_id = %s
                        """,
                        (user_id,),
                    )
                else:
                    if reset_attempts:
                        await cur.execute(
                            """
                            UPDATE users
                            SET otp_code = %s,
                                otp_expires_at = %s,
                                otp_attempts = 0
                            WHERE user_id = %s
                            """,
                            (otp_code, otp_expires_at, user_id),
                        )
                    else:
                        await cur.execute(
                            """
                            UPDATE users
                            SET otp_code = %s,
                                otp_expires_at = %s
                            WHERE user_id = %s
                            """,
                            (otp_code, otp_expires_at, user_id),
                        )

                await conn.commit()

    @staticmethod
    async def increment_otp_attempts(user_id: int):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE users
                    SET otp_attempts = otp_attempts + 1
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                await conn.commit()
