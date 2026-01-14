import os

import aiomysql
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if self.pool:
            return

        try:
            self.pool = await aiomysql.create_pool(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                db=os.getenv("DB_NAME", "secure_bank"),
                minsize=1,
                maxsize=10,
                autocommit=False,
            )
            await self._ensure_schema()
            print("--- Connection to MySQL established ---")
        except Exception as e:
            print(f"--- Error connecting to Database: {e} ---")
            raise

    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def get_conn(self):
        if not self.pool:
            await self.connect()
        # NOTE: your code uses: async with await db.get_conn() as conn:
        # This returns pool.acquire() which is awaitable; you already use it correctly in your repo.
        return self.pool.acquire()

    async def _ensure_schema(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        account_number VARCHAR(30) NOT NULL,
                        transaction_type VARCHAR(20) NOT NULL,
                        amount DECIMAL(18, 2) NOT NULL,
                        balance_after DECIMAL(18, 2) NOT NULL,
                        related_account VARCHAR(30) NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_transactions_user_created (user_id, created_at),
                        INDEX idx_transactions_account_created (account_number, created_at)
                    )
                    """
                )
                await conn.commit()


db = Database()
