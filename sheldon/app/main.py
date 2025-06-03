from fastapi import FastAPI, UploadFile, File, HTTPException
import requests
import subprocess
import jwt
from datetime import datetime, timedelta

app = FastAPI()

CA_URL = "http://step-ca:9000/sign"
ROOT_CERT_PATH = "/app/root_ca.crt"
JWT_SECRET = "secure-random-key"

@app.post("/issue-certificate")
async def issue_certificate(csr: UploadFile = File(...)):
    csr_data = await csr.read()

    resp = requests.post(CA_URL, json={"csr": csr_data.decode()})

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="CA issuance failed")

    cert_pem = resp.json()["crt"]
    return {"certificate": cert_pem}

@app.post("/verify-certificate")
async def verify_certificate(cert: UploadFile = File(...)):
    cert_data = await cert.read()

    cert_file = "/tmp/temp_cert.crt"
    with open(cert_file, "wb") as f:
        f.write(cert_data)

    result = subprocess.run(
        ["step", "certificate", "verify", cert_file, "--roots", ROOT_CERT_PATH],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail="Invalid or untrusted certificate")

    token = jwt.encode({
        "verified": True,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, JWT_SECRET, algorithm="HS256")

    return {"verification_token": token}