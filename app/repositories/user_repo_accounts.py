from decimal import Decimal

import aiomysql

from app.database.database import db
from app.repositories.user_repo_transactions import _insert_transaction


class UserRepoAccountsMixin:
    @staticmethod
    async def create_account(user_id: int, account_number: str):
        async with await db.get_conn() as conn:
            async with conn.cursor() as cur:
                sql = "INSERT INTO accounts (user_id, account_number, balance) VALUES (%s, %s, %s)"
                await cur.execute(sql, (user_id, account_number, "0.00"))
                await conn.commit()

    @staticmethod
    async def get_customer_profile_by_user_id(user_id: int):
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                    SELECT 
                        u.user_id,
                        u.username,
                        u.email,
                        u.role,
                        u.created_at as account_created_at,
                        a.account_number,
                        a.balance as current_balance,
                        a.status as account_status
                    FROM users u
                    LEFT JOIN accounts a ON u.user_id = a.user_id
                    WHERE u.user_id = %s AND u.role = 'customer'
                """
                await cur.execute(sql, (user_id,))
                return await cur.fetchone()

    @staticmethod
    async def get_customer_by_account_number(account_number: str):
        """Fetch a customer by account number with account details."""
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
                    INNER JOIN accounts a ON u.user_id = a.user_id
                    WHERE a.account_number = %s AND u.role = 'customer'
                    LIMIT 1
                """
                await cur.execute(sql, (account_number,))
                return await cur.fetchone()

    @staticmethod
    async def add_cash_by_account(account_number: str, amount: Decimal):
        """Add cash to an account by account number (atomic). Returns new balance or None."""
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "UPDATE accounts SET balance = balance + %s WHERE account_number = %s",
                    (str(amount), account_number),
                )

                if cur.rowcount == 0:
                    await conn.rollback()
                    return None

                await cur.execute(
                    "SELECT user_id, balance FROM accounts WHERE account_number = %s",
                    (account_number,),
                )
                row = await cur.fetchone()
                if not row:
                    await conn.rollback()
                    return None

                balance_after = Decimal(str(row["balance"]))
                await _insert_transaction(
                    cur,
                    user_id=int(row["user_id"]),
                    account_number=account_number,
                    transaction_type="deposit",
                    amount=amount,
                    balance_after=balance_after,
                )
                await conn.commit()

                return balance_after

    @staticmethod
    async def withdraw_cash_by_account(account_number: str, amount: Decimal):
        """
        Withdraw cash atomically.
        Returns:
          - new_balance (Decimal) on success
          - "NOT_FOUND" if account doesn't exist
          - "INSUFFICIENT" if balance < amount
        """
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT user_id, balance FROM accounts WHERE account_number = %s FOR UPDATE",
                    (account_number,),
                )
                row = await cur.fetchone()
                if not row:
                    await conn.rollback()
                    return "NOT_FOUND"

                current_balance = Decimal(str(row["balance"]))
                if current_balance < amount:
                    await conn.rollback()
                    return "INSUFFICIENT"

                await cur.execute(
                    "UPDATE accounts SET balance = balance - %s WHERE account_number = %s",
                    (str(amount), account_number),
                )

                await cur.execute(
                    "SELECT balance FROM accounts WHERE account_number = %s",
                    (account_number,),
                )
                row2 = await cur.fetchone()
                if not row2:
                    await conn.rollback()
                    return "NOT_FOUND"

                balance_after = Decimal(str(row2["balance"]))
                await _insert_transaction(
                    cur,
                    user_id=int(row["user_id"]),
                    account_number=account_number,
                    transaction_type="withdraw",
                    amount=amount,
                    balance_after=balance_after,
                )
                await conn.commit()

                return balance_after

    @staticmethod
    async def withdraw_cash_by_user_id(user_id: int, amount: Decimal):
        """
        Atomic withdraw for a customer's own account.
        Returns:
          - Decimal(new_balance) on success
          - "NOT_FOUND" if no account for user
          - "SUSPENDED" if account is not active
          - "INSUFFICIENT" if balance < amount
        """
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT account_number, status FROM accounts WHERE user_id = %s LIMIT 1 FOR UPDATE",
                    (user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    await conn.rollback()
                    return "NOT_FOUND"

                if row.get("status") != "active":
                    await conn.rollback()
                    return "SUSPENDED"

                await cur.execute(
                    """
                    UPDATE accounts
                    SET balance = balance - %s
                    WHERE user_id = %s
                      AND status = 'active'
                      AND balance >= %s
                    """,
                    (str(amount), user_id, str(amount)),
                )

                if cur.rowcount == 0:
                    await conn.rollback()
                    return "INSUFFICIENT"

                await cur.execute(
                    "SELECT balance FROM accounts WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                row2 = await cur.fetchone()
                if not row2:
                    await conn.rollback()
                    return "NOT_FOUND"

                balance_after = Decimal(str(row2["balance"]))
                await _insert_transaction(
                    cur,
                    user_id=user_id,
                    account_number=row["account_number"],
                    transaction_type="withdraw",
                    amount=amount,
                    balance_after=balance_after,
                )
                await conn.commit()

                return balance_after

    @staticmethod
    async def transfer_between_accounts(from_user_id: int, to_account_number: str, amount: Decimal):
        """
        Transfer funds from a customer's account to another account number.
        Returns:
          - Decimal(new_balance) on success
          - "NOT_FOUND" if sender or receiver account is missing
          - "SUSPENDED" if either account is not active
          - "INSUFFICIENT" if sender balance < amount
          - "SAME_ACCOUNT" if sender and receiver are the same account
        """
        async with await db.get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT account_number, balance, status FROM accounts WHERE user_id = %s LIMIT 1 FOR UPDATE",
                    (from_user_id,),
                )
                sender = await cur.fetchone()
                if not sender:
                    await conn.rollback()
                    return "NOT_FOUND"
                if sender.get("status") != "active":
                    await conn.rollback()
                    return "SUSPENDED"

                await cur.execute(
                    "SELECT user_id, account_number, status FROM accounts WHERE account_number = %s LIMIT 1 FOR UPDATE",
                    (to_account_number,),
                )
                receiver = await cur.fetchone()
                if not receiver:
                    await conn.rollback()
                    return "NOT_FOUND"
                if receiver.get("status") != "active":
                    await conn.rollback()
                    return "SUSPENDED"

                if sender.get("account_number") == receiver.get("account_number"):
                    await conn.rollback()
                    return "SAME_ACCOUNT"

                current_balance = Decimal(str(sender["balance"]))
                if current_balance < amount:
                    await conn.rollback()
                    return "INSUFFICIENT"

                await cur.execute(
                    "UPDATE accounts SET balance = balance - %s WHERE account_number = %s",
                    (str(amount), sender["account_number"]),
                )
                await cur.execute(
                    "UPDATE accounts SET balance = balance + %s WHERE account_number = %s",
                    (str(amount), receiver["account_number"]),
                )

                await cur.execute(
                    "SELECT balance FROM accounts WHERE account_number = %s",
                    (sender["account_number"],),
                )
                sender_row = await cur.fetchone()

                await cur.execute(
                    "SELECT balance FROM accounts WHERE account_number = %s",
                    (receiver["account_number"],),
                )
                receiver_row = await cur.fetchone()

                if not sender_row or not receiver_row:
                    await conn.rollback()
                    return "NOT_FOUND"

                sender_balance = Decimal(str(sender_row["balance"]))
                receiver_balance = Decimal(str(receiver_row["balance"]))

                await _insert_transaction(
                    cur,
                    user_id=from_user_id,
                    account_number=sender["account_number"],
                    transaction_type="transfer_out",
                    amount=amount,
                    balance_after=sender_balance,
                    related_account=receiver["account_number"],
                )
                await _insert_transaction(
                    cur,
                    user_id=int(receiver["user_id"]),
                    account_number=receiver["account_number"],
                    transaction_type="transfer_in",
                    amount=amount,
                    balance_after=receiver_balance,
                    related_account=sender["account_number"],
                )
                await conn.commit()
                return sender_balance
