import aiomysql

from app.database.database import db


class UserRepoAdminMixin:
    @staticmethod
    async def get_all_customers():
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                    SELECT 
                        u.user_id,
                        u.username,
                        u.email,
                        u.role,
                        u.created_at,
                        a.account_number,
                        a.balance,
                        a.status as account_status
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id
                    WHERE u.role = 'customer'
                    ORDER BY u.created_at DESC
                """
                await cur.execute(sql)
                return await cur.fetchall()

    @staticmethod
    async def get_customer_by_id(user_id: int):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                    SELECT 
                        u.user_id,
                        u.username,
                        u.email,
                        u.role,
                        u.created_at,
                        a.account_number,
                        a.balance,
                        a.status as account_status
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id
                    WHERE u.user_id = %s AND u.role = 'customer'
                """
                await cur.execute(sql, (user_id,))
                return await cur.fetchone()

    @staticmethod
    async def search_customers(search_term: str):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                    SELECT 
                        u.user_id,
                        u.username,
                        u.email,
                        u.role,
                        u.created_at,
                        a.account_number,
                        a.balance,
                        a.status as account_status
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id
                    WHERE u.role = 'customer' 
                    AND (
                        u.username LIKE %s 
                        OR u.email LIKE %s 
                        OR a.account_number LIKE %s
                    )
                    ORDER BY u.created_at DESC
                """
                search_pattern = f"%{search_term}%"
                await cur.execute(sql, (search_pattern, search_pattern, search_pattern))
                return await cur.fetchall()

    @staticmethod
    async def get_statistics():
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT COUNT(*) as total FROM users WHERE role='customer'")
                total_customers = (await cur.fetchone())["total"]

                await cur.execute("SELECT SUM(balance) as total_balance FROM accounts")
                result = await cur.fetchone()
                total_balance = float(result["total_balance"]) if result["total_balance"] else 0.0

                await cur.execute("SELECT COUNT(*) as active FROM accounts WHERE status='active'")
                active_accounts = (await cur.fetchone())["active"]

                return {
                    "total_customers": total_customers,
                    "total_balance": total_balance,
                    "active_accounts": active_accounts,
                }

    @staticmethod
    async def update_customer(user_id: int, username: str = None, email: str = None, password_hash: str = None):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                update_fields = []
                params = []

                if username:
                    update_fields.append("username = %s")
                    params.append(username)

                if email:
                    update_fields.append("email = %s")
                    params.append(email)

                if password_hash:
                    update_fields.append("password_hash = %s")
                    params.append(password_hash)

                if not update_fields:
                    return False

                params.append(user_id)
                sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s AND role = 'customer'"

                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount > 0

    @staticmethod
    async def update_account_status(user_id: int, status: str):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                sql = "UPDATE accounts SET status = %s WHERE user_id = %s"
                await cur.execute(sql, (status, user_id))
                await conn.commit()
                return cur.rowcount > 0

    @staticmethod
    async def delete_customer(user_id: int):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
                result = await cur.fetchone()

                if not result or result[0] != "customer":
                    return False

                sql = "DELETE FROM users WHERE user_id = %s AND role = 'customer'"
                await cur.execute(sql, (user_id,))
                await conn.commit()
                return cur.rowcount > 0
