from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Blueprint
from supabase_config import supabase  # Uses shared supabase config
from routes.utils import admin_login_required

app = Flask(__name__)

# Define the blueprint once
admin_dashboard_bp = Blueprint("admin_dashboard", __name__)

@app.route("/admin_upload")
@admin_login_required
def upload_page():
    return render_template("admin_upload.html")

@app.route("/admin_modify")
@admin_login_required
def modify_page():
    return render_template("admin_modify.html")

@app.route("/admin_delete")
@admin_login_required
def delete_page():
    return render_template("admin_delete.html")

@admin_dashboard_bp.route("/admin_dashboard")
@admin_login_required
def admin_dashboard():
    query = request.args.get('query', '').strip().lower()
    
    # Fetch products (filtered or all)
    if query:
        products_response = supabase.table("products").select("*").ilike('name', f'%{query}%').execute()
    else:
        products_response = supabase.table("products").select("*").execute()

    products_data = products_response.data or []

    # Fetch all images
    images_response = supabase.table("product_images").select("*").execute()
    images_data = images_response.data or []

    # Map product_name (lowercase) to list of image dicts
    image_map = {}
    for img in images_data:
        name = img.get("product_name", "").strip().lower()
        url = img.get("image_url")
        if name and url:
            image_map.setdefault(name, []).append({"image_url": url})

    # Attach images to each product
    for product in products_data:
        product_name = product.get("name", "").strip().lower()
        product["images"] = image_map.get(product_name, [])

    return render_template("admin_dashboard.html", products=products_data, query=query)


# Autocomplete endpoint
@admin_dashboard_bp.route('/get_product_names')
@admin_login_required

def get_product_names():
    query = request.args.get('query', '').lower()
    names = supabase.table('products').select('name').execute().data
    filtered_names = [n['name'] for n in names if query in n['name'].lower()]
    return jsonify({'names': filtered_names})

@admin_dashboard_bp.route("/delete_product_direct", methods=["POST"])
@admin_login_required
def delete_product_direct():
    product_name = request.form.get("product_name")

    # Delete image(s)
    supabase.table("product_images").delete().eq("product_name", product_name).execute()

    # Delete product
    response = supabase.table("products").delete().eq("name", product_name).execute()

    # Check if deletion was successful based on `response.data`
    if response.data is not None:
        return redirect(url_for('admin_dashboard.admin_dashboard', query=''))
    else:
        return "Failed to delete product", 500

# Register the blueprint
app.register_blueprint(admin_dashboard_bp)

if __name__ == '__main__':
    app.run(debug=True)
