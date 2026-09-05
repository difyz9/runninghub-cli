"""Prompt quality and Opik tracking command registrations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer


def register_quality_commands(
    app: typer.Typer,
    *,
    emit: Callable[[dict[str, Any], bool], None],
    fail: Callable[[Exception], None],
) -> None:
    """Register prompt/opik commands."""

    @app.command("prompt")
    def prompt_cmd(
        scene: str = typer.Option("", "--scene", "-c", help="场景描述（如：古风美女樱花树下）"),
        workflow: str = typer.Option("txt2img", "--workflow", "-w", help="工作流类型: txt2img / txt2vid / img2vid / music"),
        style: str | None = typer.Option(None, "--style", "-s", help="强制指定风格ID（不传则自动匹配）"),
        llm: bool = typer.Option(False, "--llm", "-l", help="使用 LLM 扩写（需配置 DEEPSEEK_API_KEY）"),
        no_check: bool = typer.Option(False, "--no-check", help="跳过质量自检"),
        list_styles: bool = typer.Option(False, "--list-styles", help="列出所有可用风格"),
        list_genres: bool = typer.Option(False, "--list-genres", help="按类别列出风格"),
        detail: bool = typer.Option(False, "--detail", "-d", help="输出详细信息（质量报告等）"),
    ):
        """🎨 高质量提示词生成 — 智能选择调色风格 + 质量自检"""
        try:
            from scripts.prompt_quality import PromptEngine

            engine = PromptEngine()

            if list_styles:
                all_styles = engine.list_styles()
                emit(
                    {
                        "count": len(all_styles),
                        "styles": [
                            {
                                "id": s["id"],
                                "name": s["name"],
                                "genre": s.get("genre", ""),
                                "mood": s.get("mood", ""),
                                "best_for": s.get("best_for", []),
                            }
                            for s in all_styles
                        ],
                    }
                )
                return

            if list_genres:
                genres = engine.list_genres()
                emit({"count": len(genres), "genres": genres})
                return

            result = engine.generate(
                scene,
                workflow_type=workflow,
                force_style=style or "",
                use_llm=llm,
                quality_check=not no_check,
            )

            if detail:
                emit(
                    {
                        "prompt": result["prompt"],
                        "style": result["style"],
                        "quality": result["quality"],
                        "verified": result["verified"],
                        "mode": result["mode"],
                    }
                )
            else:
                emit(
                    {
                        "prompt": result["prompt"],
                        "style": result["style"]["name"],
                        "quality_score": (result["quality"] or {}).get("score"),
                        "verified": result["verified"],
                    }
                )
        except Exception as exc:
            fail(exc)

    @app.command("opik")
    def opik_cmd(
        action: str = typer.Argument("stats", help="stats | search | list"),
        project: str | None = typer.Option(None, "--project", "-p", help="按项目过滤"),
        name: str | None = typer.Option(None, "--name", "-n", help="按名称搜索"),
        limit: int = typer.Option(10, "--limit", "-l", help="返回条数"),
    ):
        """📊 Opik 运行记录跟踪 — 查询提示词生成 / RunningHub 任务的运行历史"""
        try:
            from scripts.opik_tracker import tracker

            if action == "stats":
                stats = tracker.stats()
                emit(stats)
            elif action in ("search", "list"):
                traces = tracker.search(project=project, name=name, limit=limit)
                emit(
                    {
                        "count": len(traces),
                        "traces": [
                            {
                                "trace_id": t["trace_id"],
                                "name": t["name"],
                                "project": t["project"],
                                "duration_ms": t["duration_ms"],
                                "span_count": t.get("span_count", 0),
                                "score": t.get("output", {}).get("score"),
                                "style": t.get("output", {}).get("style_name")
                                or t.get("metadata", {}).get("style_name"),
                                "prompt_preview": t.get("output", {}).get("prompt_preview", ""),
                                "start_time": t["start_time"],
                                "error": t.get("error"),
                            }
                            for t in traces
                        ],
                    }
                )
            else:
                emit({"error": f"未知操作: {action}"}, ok=False)

        except ImportError:
            emit({"error": "Opik tracking not available. Ensure scripts/opik_tracker.py is present"}, ok=False)
        except Exception as exc:
            fail(exc)
