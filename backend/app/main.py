from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .database import init_db
from .routers import invoices, chat

app = FastAPI(title="Invoice Intelligence Portal")

templates = Jinja2Templates(directory="backend/app/templates")
app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
