"""
Agent System – FastAPI Backend
"""
from __future__ import annotations

import sys
import os

# Ensure local packages resolve correctly when run from /backend
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.controller import AgentController
from storage.db import init_db, save_task, get_all_tasks, get_task_by_id, delete_task


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent System API",
    description="Lightweight agentic task-runner with tool selection and execution trace",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AgentController()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TaskRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000, description="The task to execute")


class TaskResponse(BaseModel):
    id: int
    task: str
    output: object
    tools_used: list[str]
    steps: list[str]
    timestamp: str
    error: str | None = None


class TaskSummary(BaseModel):
    id: int
    task: str
    tools_used: list[str]
    timestamp: str
    success: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/tools")
def list_tools():
    """List all available tools and their metadata."""
    return {"tools": agent.list_tools()}


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def run_task(body: TaskRequest):
    """
    Submit a task for the agent to process.
    Returns the result along with a full execution trace.
    """
    task_text = body.task.strip()
    if not task_text:
        raise HTTPException(status_code=422, detail="Task must not be empty.")

    response = agent.run(task_text)

    task_id = save_task(
        task=response.task,
        output=response.output,
        error=response.error,
        tools_used=response.tools_used,
        steps=response.steps,
        timestamp=response.timestamp,
    )

    return TaskResponse(
        id=task_id,
        task=response.task,
        output=response.output,
        tools_used=response.tools_used,
        steps=response.steps,
        timestamp=response.timestamp,
        error=response.error,
    )


@app.get("/tasks", response_model=list[TaskSummary])
def list_tasks(limit: int = Query(default=50, ge=1, le=200)):
    """Return a list of past task summaries (most recent first)."""
    rows = get_all_tasks(limit=limit)
    return [
        TaskSummary(
            id=r["id"],
            task=r["task"],
            tools_used=r["tools_used"],
            timestamp=r["timestamp"],
            success=r["error"] is None,
        )
        for r in rows
    ]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    """Retrieve full details of a single task by ID."""
    row = get_task_by_id(task_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return TaskResponse(**row)


@app.delete("/tasks/{task_id}", status_code=204)
def remove_task(task_id: int):
    """Delete a task record."""
    deleted = delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")


@app.get("/tasks/{task_id}/steps")
def get_task_steps(task_id: int):
    """Return only the execution trace for a task."""
    row = get_task_by_id(task_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return {"id": task_id, "steps": row["steps"]}
