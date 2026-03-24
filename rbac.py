"""
rbac.py — Role-Based Access Control logic for the Estimator Platform
"""
import streamlit as st

# Roles and their allowed actions
PERMISSIONS = {
    "admin": {
        "view_all",
        "create_client",
        "delete_client",
        "create_estimate",
        "delete_estimate",
        "manage_users"
    },
    "estimator": {
        "view_all",
        "create_client",
        "create_estimate"
    },
    "viewer": {
        "view_all"
    }
}

def get_current_role():
    """Retrieve the current user's role from session state."""
    if not st.session_state.get("logged_in") or not st.session_state.get("user"):
        return "viewer"
    return st.session_state.user.get("role", "viewer")

def can(action: str) -> bool:
    """Check if the current user has permission to perform an action."""
    role = get_current_role()
    return action in PERMISSIONS.get(role, set())

def require(action: str, message: str = "You do not have permission to access this restricted area."):
    """Stop execution and show an error if the user lacks permission."""
    if not can(action):
        st.error(f"🔒 **Access Denied:** {message}")
        st.stop()

def role_badge():
    """Render a small role badge aligned with the UI theme."""
    role = get_current_role()
    # Matching theme colors: admin=danger/red, estimator=accent/blue, viewer=accent3/green
    colors = {
        "admin": ("var(--error)", "Admin"),
        "estimator": ("var(--accent)", "Estimator"),
        "viewer": ("var(--success)", "Viewer")
    }
    color, label = colors.get(role, ("var(--text3)", "Unknown"))
    
    badge_html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        background: {color}15;
        border: 1px solid {color}30;
        color: {color};
        padding: 3px 10px;
        border-radius: 12px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.65rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    ">
        {label}
    </div>
    """
    return badge_html
