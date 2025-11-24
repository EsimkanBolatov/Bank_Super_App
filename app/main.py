from fastapi import FastAPI
from app.core.config import settings
from app.routers import auth, accounts, transfers, transactions, services, mfa, ai, loans

app = FastAPI(title="Bank Super App")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(transactions.router)
app.include_router(services.router)
app.include_router(mfa.router)
app.include_router(ai.router)
app.include_router(loans.router)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Bank API is running"
    }



if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8080)