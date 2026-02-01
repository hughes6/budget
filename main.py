from fastapi import FastAPI
from pydantic import BaseModel
from utils import sendEmail, background_email_checker, populate_db, logger, send_catalog, archive_database, schedule_monthly_archive, send_expense
from database import engine, get_db, SessionLocal
from schemas import Data
import threading
from contextlib import asynccontextmanager
import models
from models import BudgetItem


models.Base.metadata.create_all(bind=engine)


# Start background thread on app startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("App starting up...")
    
    print("Populating db")
    db = SessionLocal()
    try: 
      logger.info("Attempting to populate databast from excel")
      result = populate_db(db)
      if "error" in result:
        logger.warning(f"Database population skipped {result['error']}")
      else:
        logger.info(f"Database populated: {result}")
    except Exception as e:
      logger.error(f"Error during startup: {e}")
    finally:
      db.close()

    # Start background thread

    global email_thread
    global archive_thread
    email_thread = threading.Thread(target=background_email_checker, daemon=True)
    email_thread.start()
    print("Background thread started")
    archive_thread = threading.Thread(target=schedule_monthly_archive, daemon=True)
    archive_thread.start()
    print("Archive thread started")
    
    yield  # App runs here
    
    # Shutdown code
    print("App shutting down...")
    # You can add cleanup code here

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
  'this is just for a test'
  db = SessionLocal()
  send_expense('hconner158@gmail.com',db)
  # send_catalog('hconner158@gmail.com',db)
  # archive_database(db)
  # run_scheduled_archive_dbug()
  return {"Successful"}


