from fastapi import FastAPI
from x402.fastapi.middleware import require_payment

app = FastAPI()
app.middleware("http")(
    require_payment(price="0.01", pay_to_address="0x2654bb8B272f117c514aAc3d4032B1795366BA5d")
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
