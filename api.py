
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

@app.get("/swap-in")
async def swap_in(amount: int):
    ...


@app.get("/swap-out")
async def swap_out(amount: int, address: str):
    ...
