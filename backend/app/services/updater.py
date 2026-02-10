import subprocess
import os
from app.config import get_settings

settings = get_settings()


class UpdateService:
    def get_current_version(self) -> str:
        return settings.APP_VERSION

    def check_for_updates(self) -> dict:
        try:
            result = subprocess.run(
                ["git", "fetch", "origin", "--dry-run"],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            result2 = subprocess.run(
                ["git", "log", "HEAD..origin/main", "--oneline"],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            commits = result2.stdout.strip().split("\n") if result2.stdout.strip() else []
            return {
                "current_version": settings.APP_VERSION,
                "updates_available": len(commits) > 0,
                "pending_commits": len(commits),
                "commit_messages": commits[:10],
            }
        except Exception as e:
            return {
                "current_version": settings.APP_VERSION,
                "updates_available": False,
                "error": str(e),
            }

    def apply_update(self) -> dict:
        try:
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "scripts", "update.sh"
            )
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True, timeout=300
            )
            return {"success": result.returncode == 0, "output": result.stdout, "errors": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_update_service() -> UpdateService:
    return UpdateService()
