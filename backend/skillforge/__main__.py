"""
SkillForge CLI Entry Point.

Usage:
    python -m skillforge                  # Start API server (default)
    python -m skillforge serve            # Start API server
    python -m skillforge serve --port 8080
    python -m skillforge info             # Show system info
    python -m skillforge skills           # List all skills
    python -m skillforge validate <file>  # Validate a skill YAML
    python -m skillforge run "<message>"  # Run a single query through the agentic loop
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("skillforge")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI server."""
    import uvicorn
    from skillforge.api.server import api

    logger.info("Starting SkillForge API server on %s:%d", args.host, args.port)
    uvicorn.run(
        api,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


def cmd_info(args: argparse.Namespace) -> None:
    """Print system information."""
    from skillforge.app import create_app

    app = create_app()
    info = app.get_system_info()
    print(json.dumps(info, indent=2, default=str, ensure_ascii=False))
    app.shutdown()


def cmd_skills(args: argparse.Namespace) -> None:
    """List all registered skills."""
    from skillforge.app import create_app

    app = create_app()
    skills = app.registry.list_all()

    print(f"\n{'='*60}")
    print(f" SkillForge - {len(skills)} Skills Registered")
    print(f"{'='*60}\n")

    # Group by category
    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for s in skills:
        by_cat[s.category.value].append(s)

    for cat, cat_skills in sorted(by_cat.items()):
        print(f"  [{cat.upper()}]")
        for s in cat_skills:
            stars = "★" * int(s.rating) + "☆" * (5 - int(s.rating))
            print(f"    {s.id:<25} {s.name:<20} v{s.version}  {stars}  ({s.downloads} downloads)")
        print()

    app.shutdown()


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a skill YAML file."""
    from skillforge.engine.loader import SkillLoader
    from skillforge.engine.validator import SkillValidator

    try:
        skill = SkillLoader.from_yaml_file(args.file)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    except Exception as exc:
        print(f"Error: Failed to parse YAML: {exc}")
        sys.exit(1)

    result = SkillValidator.validate(skill)

    print(f"\nValidation: {args.file}")
    print(f"{'='*50}")
    print(f"  Skill ID:   {skill.id}")
    print(f"  Name:       {skill.name}")
    print(f"  Version:    {skill.version}")
    print(f"  Category:   {skill.category.value}")
    print(f"  Result:     {'PASS' if result.valid else 'FAIL'}")
    print(f"  Checks:     {result.checks_passed}/{result.checks_total}")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for err in result.errors:
            print(f"    ✗ {err}")

    if result.warnings:
        print(f"\n  Warnings ({len(result.warnings)}):")
        for warn in result.warnings:
            print(f"    ⚠ {warn}")

    if result.valid:
        print("\n  ✓ Skill is valid and ready to publish!")
    else:
        print(f"\n  ✗ Skill has {len(result.errors)} error(s). Fix before publishing.")

    sys.exit(0 if result.valid else 1)


def cmd_run(args: argparse.Namespace) -> None:
    """Run a single query through the agentic loop."""
    from skillforge.app import create_app

    app = create_app()

    async def _run():
        result = await app.loop.run(
            user_input=args.message,
            user_id=args.user_id,
        )
        return result

    result = asyncio.run(_run())

    print(f"\n{'='*60}")
    print(f" SkillForge - Agentic Loop Result")
    print(f"{'='*60}")
    print(f"  Request:    {result.user_request[:80]}")
    print(f"  Session:    {result.session_id}")
    print(f"  Success:    {result.success}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Tokens:     {result.total_tokens}")
    print(f"  Time:       {result.total_time_ms}ms")

    if result.plan:
        print(f"\n  Plan ({len(result.plan.tasks)} tasks):")
        for task in result.plan.tasks:
            skill_tag = f"[{task.skill_id}]" if task.skill_id else ""
            print(f"    → {task.agent_role.value}: {task.description[:50]} {skill_tag}")

    if result.quality_review:
        print(f"\n  Quality: {result.quality_review.overall_score:.2f}")
        print(f"  Passed:  {result.quality_review.passed}")

    if result.error:
        print(f"\n  Error: {result.error}")

    print(f"\n  Output:")
    print(f"  {'─'*56}")
    for line in result.final_output.split("\n"):
        print(f"  {line}")

    app.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skillforge",
        description="SkillForge - Multi-Agent System with Agentic Loop & Skill Store",
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # info
    subparsers.add_parser("info", help="Show system information")

    # skills
    subparsers.add_parser("skills", help="List all registered skills")

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate a skill YAML file")
    val_parser.add_argument("file", help="Path to YAML file")

    # run
    run_parser = subparsers.add_parser("run", help="Run a query through the agentic loop")
    run_parser.add_argument("message", help="User message to process")
    run_parser.add_argument("--user-id", default="cli-user", help="User ID")

    args = parser.parse_args()

    if args.command is None or args.command == "serve":
        # Default command: start server
        if args.command is None:
            args.host = "0.0.0.0"
            args.port = 8000
            args.reload = False
        cmd_serve(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "skills":
        cmd_skills(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
