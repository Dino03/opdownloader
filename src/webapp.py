import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator

from .cdasia import CDAsiaClient
from .downloader import Downloader
from .utils import ensure_dirs, load_config


app = FastAPI(title="CDAsia Opinions Downloader", version="0.1.0")


class RunRequest(BaseModel):
    division: Optional[str] = None
    keywords: Optional[List[str]] = None
    year_from: Optional[int] = Field(None, ge=1900, le=2100)
    year_to: Optional[int] = Field(None, ge=1900, le=2100)
    max_docs: Optional[int] = Field(None, ge=0)
    headless: Optional[bool] = None
    dry_run: bool = False

    @field_validator("keywords", mode="before")
    @classmethod
    def split_keywords(cls, value: Any) -> Optional[List[str]]:
        if isinstance(value, str):
            return [kw.strip() for kw in value.split(",") if kw.strip()]
        return value

    @model_validator(mode="after")
    def validate_year_range(self) -> "RunRequest":
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_to < self.year_from
        ):
            raise ValueError("year_to must be >= year_from")
        return self

TASKS: Dict[str, Dict[str, Any]] = {}


def _apply_overrides(cfg: Dict[str, Any], payload: RunRequest) -> Dict[str, Any]:
    filters = cfg.setdefault("filters", {})
    if payload.division is not None:
        filters["division"] = payload.division
    if payload.keywords is not None:
        filters["keywords"] = payload.keywords
    if payload.year_from is not None:
        filters["year_from"] = payload.year_from
    if payload.year_to is not None:
        filters["year_to"] = payload.year_to
    if payload.max_docs is not None:
        filters["max_docs"] = payload.max_docs

    if payload.headless is not None:
        cfg.setdefault("scrape", {})["headless"] = payload.headless

    return cfg


async def _download_job(task_id: str, payload: RunRequest) -> None:
    info = TASKS[task_id]
    loop = asyncio.get_running_loop()
    info.update({
        "status": "running",
        "started_at": loop.time(),
        "dry_run": payload.dry_run,
    })

    cfg = _apply_overrides(load_config(), payload)
    downloads_dir = Path(cfg["site"]["downloads_subdir"])
    logs_dir = Path(cfg["site"]["log_dir"])
    ensure_dirs([downloads_dir, logs_dir])

    log_path = logs_dir / f"task-{task_id}.log"
    log_sink_id = logger.add(log_path, rotation="2 MB")

    try:
        async with CDAsiaClient(cfg) as client:
            await client.login(human_checkpoint=not cfg["scrape"].get("headless", True))
            results = await client.search()
            info["results_found"] = len(results)

            if payload.dry_run:
                preview = []
                for entry in results[:10]:
                    preview.append({
                        "title": entry.get("title"),
                        "date": entry.get("date"),
                        "href": entry.get("href"),
                    })
                info["preview"] = preview
                info["status"] = "completed"
                return

            downloader = Downloader(cfg, downloads_dir)
            await downloader.fetch_all(client.page, results)
            info["downloaded"] = len(downloader.index_rows)
            info["status"] = "completed"
    except Exception as exc:  # pragma: no cover - defensive logging
        info["status"] = "failed"
        info["error"] = str(exc)
        logger.exception("Task {task_id} failed: {exc}", task_id=task_id, exc=exc)
    finally:
        info["headless"] = cfg.get("scrape", {}).get("headless")
        info["finished_at"] = loop.time()
        info["log_path"] = str(log_path)
        logger.remove(log_sink_id)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    cfg = load_config()
    filters = cfg.get("filters", {})
    scrape = cfg.get("scrape", {})
    keywords_value = ", ".join(filters.get("keywords", []))
    headless_checked = "checked" if scrape.get("headless", True) else ""
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='utf-8'>
        <title>CDAsia Opinions Downloader</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
            form {{ display: grid; gap: 1rem; margin-bottom: 2rem; }}
            label {{ display: flex; flex-direction: column; font-weight: 600; }}
            input[type='text'], input[type='number'] {{ padding: 0.5rem; font-size: 1rem; }}
            .checkbox {{ flex-direction: row; align-items: center; gap: 0.5rem; font-weight: 400; }}
            button {{ padding: 0.75rem 1.5rem; font-size: 1rem; cursor: pointer; }}
            #status {{ background: #f5f5f5; padding: 1rem; min-height: 4rem; white-space: pre-wrap; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
            th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
            th {{ background: #fafafa; }}
        </style>
    </head>
    <body>
        <h1>CDAsia Opinions Downloader</h1>
        <p>Launch downloads with the same automation that powers the CLI. Provide your filters and click <strong>Start run</strong>.</p>
        <form id='run-form'>
            <label>Division
                <input type='text' name='division' value='{filters.get('division', '')}' placeholder='e.g., SEC-OGC'>
            </label>
            <label>Keywords (comma separated)
                <input type='text' name='keywords' value='{keywords_value}'>
            </label>
            <label>Year from
                <input type='number' name='year_from' min='1900' max='2100' value='{filters.get('year_from', '')}'>
            </label>
            <label>Year to
                <input type='number' name='year_to' min='1900' max='2100' value='{filters.get('year_to', '')}'>
            </label>
            <label>Max documents (0 = unlimited)
                <input type='number' name='max_docs' min='0' value='{filters.get('max_docs', 0)}'>
            </label>
            <label class='checkbox'><input type='checkbox' name='headless' {headless_checked}> Run headless</label>
            <label class='checkbox'><input type='checkbox' name='dry_run'> Dry run (list only)</label>
            <button type='submit'>Start run</button>
        </form>
        <section>
            <h2>Task status</h2>
            <div id='status'>Awaiting run…</div>
            <div id='preview'></div>
        </section>
        <script>
            const statusEl = document.getElementById('status');
            const previewEl = document.getElementById('preview');
            const form = document.getElementById('run-form');
            let activeTask = null;
            let pollTimer = null;

            function renderPreview(task) {{
                if (!task.preview || task.preview.length === 0) {{
                    previewEl.innerHTML = '';
                    return;
                }}
                const rows = task.preview.map(item => `
                    <tr>
                        <td>${{item.title || ''}}</td>
                        <td>${{item.date || ''}}</td>
                        <td><a href='${{item.href || '#'}}' target='_blank'>Link</a></td>
                    </tr>
                `).join('');
                previewEl.innerHTML = `
                    <h3>Preview (first ${task.preview.length} results)</h3>
                    <table>
                        <thead><tr><th>Title</th><th>Date</th><th>URL</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                `;
            }}

            function updateStatus(task) {{
                const lines = [
                    `Task ID: ${task.id}`,
                    `Status: ${task.status}`,
                    task.results_found !== undefined ? `Results found: ${task.results_found}` : '',
                    task.downloaded !== undefined ? `Downloaded: ${task.downloaded}` : '',
                    task.error ? `Error: ${task.error}` : '',
                    task.log_path ? `Log file: ${task.log_path}` : ''
                ].filter(Boolean);
                statusEl.textContent = lines.join('\n');
                renderPreview(task);
            }}

            async function pollTask(taskId) {{
                try {{
                    const res = await fetch(`/api/tasks/${{taskId}}`);
                    if (!res.ok) {{
                        throw new Error('Task lookup failed');
                    }}
                    const task = await res.json();
                    updateStatus(task);
                    if (task.status === 'completed' || task.status === 'failed') {{
                        clearInterval(pollTimer);
                        pollTimer = null;
                    }}
                }} catch (err) {{
                    statusEl.textContent = `Error checking task: ${{err}}`;
                }}
            }}

            form.addEventListener('submit', async (event) => {{
                event.preventDefault();
                if (pollTimer) {{
                    clearInterval(pollTimer);
                    pollTimer = null;
                }}
                const data = new FormData(form);
                const payload = {{}};
                for (const [key, value] of data.entries()) {{
                    if (!value && key !== 'headless' && key !== 'dry_run') continue;
                    if (key === 'keywords') {{
                        payload[key] = value.split(',').map(v => v.trim()).filter(Boolean);
                    }} else if (key === 'headless' || key === 'dry_run') {{
                        payload[key] = true;
                    }} else if (key === 'max_docs' || key.startsWith('year')) {{
                        payload[key] = Number(value);
                    }} else {{
                        payload[key] = value;
                    }}
                }}

                if (!data.has('headless')) {{
                    payload.headless = false;
                }}

                try {{
                    const res = await fetch('/api/run', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(payload)
                    }});
                    if (!res.ok) {{
                        const error = await res.json();
                        throw new Error(error.detail || 'Failed to start run');
                    }}
                    const body = await res.json();
                    activeTask = body.task_id;
                    statusEl.textContent = `Task ${{body.task_id}} started…`;
                    previewEl.innerHTML = '';
                    pollTimer = setInterval(() => pollTask(activeTask), 2000);
                }} catch (err) {{
                    statusEl.textContent = `Error starting run: ${{err}}`;
                }}
            }});
        </script>
    </body>
    </html>
    """


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    return load_config()


@app.get("/api/tasks")
async def list_tasks() -> List[Dict[str, Any]]:
    return [dict(id=task_id, **data) for task_id, data in TASKS.items()]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    data = dict(TASKS[task_id])
    data.setdefault("id", task_id)
    return data


@app.post("/api/run")
async def start_run(payload: RunRequest) -> Dict[str, str]:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending"}
    asyncio.create_task(_download_job(task_id, payload))
    return {"task_id": task_id}


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
