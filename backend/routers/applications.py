from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from dependencies import get_db, get_current_user
from models import Application, User
from schemas import ApplicationCreate, ApplicationResponse, ApplicationUpdate

router = APIRouter()


@router.get("", response_model=List[ApplicationResponse])
def get_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Application).filter(Application.user_id == current_user.id).all()


@router.post("", response_model=ApplicationResponse)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_app = Application(**data.model_dump(), user_id=current_user.id)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application_by_id(app_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch("/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: str, data: ApplicationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_app, key, value)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.delete("/{app_id}")
def delete_application(app_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_app = db.query(Application).filter(Application.id == app_id, Application.user_id == current_user.id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(db_app)
    db.commit()
    return {"message": "deleted"}