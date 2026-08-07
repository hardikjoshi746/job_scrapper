from fastapi import APIRouter, Depends, HTTPException 
from sqlalchemy.orm import Session 
from typing import List 
from dependencies import get_db
from models import Application
from schemas import ApplicationCreate, ApplicationResponse, ApplicationUpdate

router = APIRouter()

# Get all the applications 
@router.get("/", response_model=List[ApplicationResponse])
def get_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()

# create application and sotre it in database
@router.post("/", response_model=ApplicationResponse)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    db_app = Application(**data.model_dump())
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


# get application based on id
@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application_by_id(app_id: int, db: Session = Depends(get_db)):
    response = db.query(Application).filter(Application.id == app_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="Application not found")
    else:
        return response

# update an application
@router.patch("/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: int, data: ApplicationUpdate, db: Session = Depends(get_db)):
    db_app = db.query(Application).filter(Application.id == app_id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    updates = data.model_dump(exclude_unset=True)                           
    for key, value in updates.items():           
      setattr(db_app, key, value)   
    db.commit()
    db.refresh(db_app)
    return db_app
        

# delete an application
@router.delete("/{app_id}")
def delete_applications(app_id: int, db: Session = Depends(get_db)):
    db_app = db.query(Application).filter(Application.id == app_id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    else:
        db.delete(db_app)
        db.commit()
        return {"message" : "deleted"}
