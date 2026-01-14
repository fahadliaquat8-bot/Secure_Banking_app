import aiomysql

from app.database.database import db


class UserRepoUsersMixin:
    @staticmethod
    async def create_user(username: str, email: str, password_hash: str):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                sql = "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)"
                await cur.execute(sql, (username, email, password_hash, "customer"))
                user_id = cur.lastrowid
                await conn.commit()
                return user_id

    @staticmethod
    async def get_user_by_username(username: str):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                return await cur.fetchone()

    @staticmethod
    async def get_user_by_email(email: str):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                return await cur.fetchone()

    @staticmethod
    async def get_user_by_id(user_id: int):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                return await cur.fetchone()

    @staticmethod
    async def check_username_exists(username: str, exclude_user_id: int = None):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if exclude_user_id:
                    sql = "SELECT user_id FROM users WHERE username = %s AND user_id != %s"
                    await cur.execute(sql, (username, exclude_user_id))
                else:
                    sql = "SELECT user_id FROM users WHERE username = %s"
                    await cur.execute(sql, (username,))

                return await cur.fetchone() is not None

    @staticmethod
    async def check_email_exists(email: str, exclude_user_id: int = None):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if exclude_user_id:
                    sql = "SELECT user_id FROM users WHERE email = %s AND user_id != %s"
                    await cur.execute(sql, (email, exclude_user_id))
                else:
                    sql = "SELECT user_id FROM users WHERE email = %s"
                    await cur.execute(sql, (email,))

                return await cur.fetchone() is not None
