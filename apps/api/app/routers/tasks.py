# apps/api/app/routers/tasks.py
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List
from sqlalchemy import text, bindparam
import sqlalchemy as sa

from ..db import get_db
from ..middleware.purpose_of_use import require_pou

router = APIRouter(prefix="/v1", tags=["tasks"])

class TaskCreate(BaseModel):
    type: Literal["care_escalation", "pro_reminder", "rpm_alert"]
    payload: Dict[str, Any]
    assignee: Optional[str] = None
    status: Optional[Literal["open","in_progress","done","canceled"]] = "open"

@router.post("/tasks", dependencies=[Depends(require_pou({"OPERATIONS"}))])
def create_task(body: TaskCreate, db=Depends(get_db)):
    row = db.execute(
        text("""
            INSERT INTO tasks(type, status, payload_json, assignee)
            VALUES (:t, :s, :p, :a)
            RETURNING id
        """).bindparams(bindparam("p", type_=sa.JSON)),
        {"t": body.type, "s": body.status or "open", "p": body.payload, "a": body.assignee},
    ).first()
    db.commit()
    return {"id": int(row[0])}

@router.get("/tasks")
def list_tasks(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    me: Optional[bool] = Query(False),                 # tolerated flag from UI
    limit: int = Query(50, ge=1, le=200),
    before_id: Optional[int] = Query(None, description="Keyset pagination: return rows with id < before_id"),
    db=Depends(get_db),
    pou=Depends(require_pou({"OPERATIONS"})),
):
    where = []
    params: Dict[str, Any] = {"limit": limit}
    if type:
        where.append("type = :type"); params["type"] = type
    if status:
        where.append("status = :status"); params["status"] = status
    if assignee:
        where.append("assignee = :assignee"); params["assignee"] = assignee
    if before_id:
        where.append("id < :before_id"); params["before_id"] = before_id

    sql = "SELECT id, type, status, payload_json, assignee, created_at FROM tasks"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT :limit"

    rows = db.execute(text(sql), params).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.post("/tasks/{task_id}/complete", dependencies=[Depends(require_pou({"OPERATIONS"}))])
def complete_task(task_id: int = Path(...), db=Depends(get_db)):
    res = db.execute(text("UPDATE tasks SET status='done' WHERE id=:id RETURNING id"), {"id": task_id}).first()
    if not res:
        raise HTTPException(404, "Task not found")
    db.commit()
    return {"ok": True, "id": int(res[0])}
