"""Read-only HTML dashboard for human incident review."""

from flask import Blueprint, current_app, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    incidents = current_app.extensions["aiops_store"].list_all()
    return render_template(
        "dashboard.html",
        incidents=incidents,
        refresh_seconds=10,
    )
