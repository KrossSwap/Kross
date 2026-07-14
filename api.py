
from fastapi import FastAPI


app = FastAPI()

@app.get("/swap-in")
async def swap_in(amount: int):
    ...


@app.get("/swap-out")
async def swap_out(amount: int, address: str):
    ...
