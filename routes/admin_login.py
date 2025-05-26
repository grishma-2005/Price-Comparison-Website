from flask import Blueprint, render_template, request, redirect, session
from supabase_config import supabase

admin_login_bp = Blueprint('admin_login_bp', __name__)

@admin_login_bp.route('/admin_login_page', methods=['GET'])
def admin_login_page():
    return render_template("admin_login.html")

@admin_login_bp.route('/admin_login', methods=['POST'])
def admin_login():
    email = request.form.get("email")
    password = request.form.get("password")

    result = supabase.table("admin").select("*").eq("admin", email).eq("password", password).execute()

    if result.data and len(result.data) > 0:
        session["admin_logged_in"] = True
        return redirect("/admin_dashboard")
    else:
        return render_template("error.html", message="✗ Invalid login credentials.")
