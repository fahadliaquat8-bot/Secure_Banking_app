# SecureBankingApp

SecureBankingApp is a Python backend for a secure online banking experience with OTP-based admin access, customer management, account operations, transfers, and transaction history.

## Features
- User registration and authentication
- Admin OTP flow
- Account creation and status management
- Cash deposit/withdrawal
- Transfers between accounts
- Transaction history

## Tech
- FastAPI
- MySQL (aiomysql)
- Redis (cache)

## Setup
1) Create and activate a virtual environment
2) Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3) Configure environment variables in `.env`
4) Initialize the database using `database/database_file.sql`

## Run
```bash
uvicorn main:app --reload
```

## Notes
- `.env` in this repo contains dummy values only.
