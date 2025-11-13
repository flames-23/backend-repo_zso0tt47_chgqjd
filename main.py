import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from database import create_document
from schemas import Contact

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# Email sending via SMTP or service provider is often blocked in ephemeral envs.
# We'll implement a simple stub that stores messages and, if SMTP creds exist,
# attempts to send using Python's smtplib. Fallback to store-only.
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TARGET_EMAIL = os.getenv("TARGET_EMAIL", "shreyash@certiswift.in")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "noreply@portfolio.local")

class ContactIn(BaseModel):
    name: str
    email: EmailStr
    message: str

@app.post("/api/contact")
def submit_contact(payload: ContactIn):
    # Save to DB first
    try:
        create_document("contact", payload.model_dump())
    except Exception as e:
        # Not fatal for user, but log and continue
        print("DB save error:", e)

    # Try sending email if SMTP is configured
    sent = False
    error = None
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            body = f"New collaboration request from {payload.name} <{payload.email}>\n\n" \
                   f"Message:\n{payload.message}\n"
            msg = MIMEText(body)
            msg["Subject"] = f"Portfolio Collaboration: {payload.name}"
            msg["From"] = FROM_EMAIL
            msg["To"] = TARGET_EMAIL

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(FROM_EMAIL, [TARGET_EMAIL], msg.as_string())
                sent = True
        except Exception as e:
            error = str(e)
            print("SMTP send error:", error)

    return {
        "ok": True,
        "email_dispatched": sent,
        "target": TARGET_EMAIL,
        "note": "Stored in DB; email sent if SMTP configured.",
        "error": error,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
