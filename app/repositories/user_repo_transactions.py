from decimal import Decimal

import aiomysql

from app.database.database import db


async def _insert_transaction(
    cur,
    user_id: int,
    account_number: str,
    transaction_type: str,
    amount: Decimal,
    balance_after: Decimal,
    related_account: str | None = None,
):
    await cur.execute(
        """
        INSERT INTO transactions (
            user_id, account_number, transaction_type, amount, balance_after, related_account
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            account_number,
            transaction_type,
            str(amount),
            str(balance_after),
            related_account,
        ),
    )


class UserRepoTransactionsMixin:
    @staticmethod
    async def get_transaction_history_by_user_id(user_id: int, limit: int = 50, offset: int = 0):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT
                        transaction_id,
                        account_number,
                        transaction_type,
                        amount,
                        balance_after,
                        related_account,
                        created_at
                    FROM transactions
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
                rows = await cur.fetchall()
                for row in rows:
                    row["amount"] = Decimal(str(row["amount"]))
                    row["balance_after"] = Decimal(str(row["balance_after"]))
                return rows
