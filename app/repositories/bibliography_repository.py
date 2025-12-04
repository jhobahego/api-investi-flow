from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.bibliography import Bibliography
from app.schemas.bibliography import BibliographyCreate, BibliographyUpdate


class BibliographyRepository:
    def get_by_project(self, db: Session, project_id: int) -> List[Bibliography]:
        return (
            db.query(Bibliography).filter(Bibliography.project_id == project_id).all()
        )

    def get_by_id(self, db: Session, id: int) -> Optional[Bibliography]:
        return db.query(Bibliography).filter(Bibliography.id == id).first()

    def create(
        self, db: Session, project_id: int, obj_in: BibliographyCreate
    ) -> Bibliography:
        db_obj = Bibliography(
            project_id=project_id,
            type=obj_in.type,
            author=obj_in.author,
            year=obj_in.year,
            title=obj_in.title,
            source=obj_in.source,
            doi=obj_in.doi,
            url=obj_in.url,
            volume=obj_in.volume,
            issue=obj_in.issue,
            pages=obj_in.pages,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Bibliography, obj_in: BibliographyUpdate
    ) -> Bibliography:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        obj = db.query(Bibliography).get(id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False

    def update_file(
        self, db: Session, id: int, file_path: str, file_name: str
    ) -> Optional[Bibliography]:
        obj = db.query(Bibliography).get(id)
        if obj:
            obj.file_path = file_path
            obj.file_name = file_name
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj
        return None


bibliography_repository = BibliographyRepository()
