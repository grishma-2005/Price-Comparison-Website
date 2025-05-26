from flask import Blueprint, request, jsonify
from supabase_config import supabase
from flask import Blueprint, render_template

admin_delete_bp = Blueprint("admin_delete", __name__)

@admin_delete_bp.route("/get_product_details")
def get_product_details():
    product_name = request.args.get("product_name")

    if not product_name:
        return jsonify({"error": "Product name required."}), 400

    product_data = supabase.table("products").select("*").eq("name", product_name).single().execute().data
    if not product_data:
        return jsonify({"error": "Product not found."}), 404

    images_data = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute().data
    image_urls = [img["image_url"] for img in images_data] if images_data else []

    return jsonify({
        "category": product_data.get("category"),
        "price": product_data.get("price"),
        "description": product_data.get("description"),
        "stock": product_data.get("stock"),
        "images": image_urls
    })


@admin_delete_bp.route("/delete_product", methods=["POST"])
def delete_product():
    data = request.get_json()
    product_name = data.get("product_name")

    if not product_name:
        return jsonify({'message': 'No product name provided.'}), 400

    # Delete related images
    supabase.table("product_images").delete().eq("product_name", product_name).execute()

    # Delete the product itself
    response = supabase.table("products").delete().eq("name", product_name).execute()

    # ✅ Check if any row was deleted
    if response.data and len(response.data) > 0:
        return jsonify({'message': 'Product deleted successfully.'})
    else:
        return jsonify({'message': 'Product not found or already deleted.'}), 404

@admin_delete_bp.route("/admin_delete/")
def delete_page():
    return render_template("admin_delete.html")