from flask import Blueprint, render_template, request, redirect
from supabase_config import supabase

admin_order_bp = Blueprint("admin_order", __name__)

@admin_order_bp.route("/admin_order", methods=["GET", "POST"])
def admin_order():
    if request.method == "POST":
        packed_id = request.form.get("packed_id")
        if packed_id:
            supabase.table("Order").update({"packed_done": True}).eq("id", packed_id).execute()
        return redirect("/admin_order")

    # Determine if we are showing packed or unpacked orders
    status = request.args.get("status", "unpacked")
    show_packed = status == "packed"

    response = (
        supabase.table("Order")
        .select("id, email, product_name, quantity")
        .eq("packed_done", show_packed)
        .execute()
    )
    orders = response.data or []
    for order in orders:
        order["user_email"] = order.pop("email", "")

    return render_template("admin_order.html", orders=orders, show_packed=show_packed)