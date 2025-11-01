from fastapi import FastAPI
from pydantic import BaseModel, EmailStr


app=FastAPI(title='Signature Adapter Mock')

class R(BaseModel): signer_name:str; doc_url:str

@app.post('/requests')
def create(r:R): return {'request_id':'sig-req-1','redirect_url':'https://example.com/sign/sig-req-1'}

class CreateReq(BaseModel):
    email: EmailStr
    template_title: str = "Consent"
    payload: dict = {}

@app.post("/requests")
def create_request(body: CreateReq):
    # in real life: return hosted signing URL
    return {
        "request_id":"mock-req-1",
        "signing_url":"http://localhost:5173/consent/mock-req-1"
    }
