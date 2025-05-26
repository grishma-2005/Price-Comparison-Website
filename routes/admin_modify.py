from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from supabase_config import supabase
import os
import uuid

admin_modify_bp = Blueprint('admin_modify', __name__)

from supabase_config import SUPABASE_URL

base_url = SUPABASE_URL.rstrip('/')
# # This must come before using `storage_path`
# storage_path = f"{product_name}/{new_filename}"

# new_url = f"{base_url}/storage/v1/object/public/product_images/{storage_path}"

@admin_modify_bp.route('/')
def modify_form():
    product_name = request.args.get('product_name')
    return render_template('admin_modify.html', product_name=product_name)

@admin_modify_bp.route('/get_product_names')
def get_product_names():
    query = request.args.get('query', '').lower()
    names = supabase.table('products').select('name').execute().data
    filtered_names = [n['name'] for n in names if query in n['name'].lower()]
    return jsonify(filtered_names)

@admin_modify_bp.route('/get_images/<product_name>')
def get_images(product_name):
    if not product_name:
        return jsonify([])
    images = supabase.table('product_images').select('*').eq('product_name', product_name).execute().data
    return jsonify(images)

@admin_modify_bp.route('/update_product', methods=['POST'])
def update_product():
    old_name = request.form['product_name']
    column = request.form['column']
    result_msg = ""

    if column == 'image':
        return redirect(url_for('admin_modify.modify_form', product=old_name))

    if column == 'category':
        new_value = request.form.get('new_category')
    else:
        new_value = request.form.get('new_value')

    if not new_value:
        return render_template('admin_modify.html', result="New value required.")

    update_result = supabase.table('products').update({column: new_value}).eq('name', old_name).execute()

    if update_result.data:
        if column == 'name':
            supabase.table('product_images').update({'product_name': new_value}).eq('product_name', old_name).execute()

        # Verify update
        check_name = new_value if column == 'name' else old_name
        verify = supabase.table('products').select(column).eq('name', check_name).execute().data
        if verify and verify[0].get(column) == new_value:
            result_msg = f"Successfully updated {column}."
        else:
            result_msg = f"Update attempted but {column} not updated."
    else:
        result_msg = f"Failed to update {column}."

    return render_template('admin_modify.html', result=result_msg)

@admin_modify_bp.route('/delete_image', methods=['POST'])
def delete_image():
    product_name = request.form['product_name']
    image_url = request.form['image_url']
    image_path = image_url.split("/storage/v1/object/public/")[-1]

    try:
        supabase.storage.from_("product_images").remove([image_path])
        supabase.table('product_images').delete().eq('product_name', product_name).eq('image', image_url).execute()
        return jsonify({"success": True, "message": "Image deleted."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Image deletion failed: {str(e)}"})

@admin_modify_bp.route('/replace_image', methods=['POST'])
def replace_image():
    product_name = request.form['product_name']
    old_url = request.form['old_image_url']
    new_file = request.files['new_image_file']

    if not new_file:
        return jsonify({"success": False, "message": "No new image uploaded."})

    new_filename = str(uuid.uuid4()) + os.path.splitext(new_file.filename)[-1]
    storage_path = f"{product_name}/{new_filename}"

    supabase.storage.from_("product_images").upload(storage_path, new_file)
    new_url = f"https://YOUR_SUPABASE_PROJECT.supabase.co/storage/v1/object/public/product_images/{storage_path}"

    supabase.table('product_images').update({"image": new_url}).eq("product_name", product_name).eq("image", old_url).execute()

    return jsonify({"success": True, "message": "Image replaced.", "new_url": new_url})

@admin_modify_bp.route('/upload_new_image', methods=['POST'])
def upload_new_image():
    product_name = request.form['product_name']
    image_file = request.files['new_image']

    if not image_file:
        return jsonify({"success": False, "message": "No image uploaded."})

    filename = str(uuid.uuid4()) + os.path.splitext(image_file.filename)[-1]
    path = f"{product_name}/{filename}"
    supabase.storage.from_("product_images").upload(path, image_file)

    image_url = f"https://YOUR_SUPABASE_PROJECT.supabase.co/storage/v1/object/public/product_images/{path}"

    supabase.table('product_images').insert({"product_name": product_name, "image": image_url}).execute()

    return jsonify({"success": True, "message": "Image uploaded.", "new_url": image_url})
