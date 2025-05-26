from flask import Blueprint, render_template, request, redirect, flash
from supabase_config import supabase
from datetime import datetime
import uuid
import mimetypes


admin_upload_bp = Blueprint('admin_upload_bp', __name__)

@admin_upload_bp.route('/admin_upload/', methods=['GET', 'POST'])
def upload_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        price = request.form['price']
        description = request.form['description']
        category = request.form['category']
        stock = request.form['stock']
        images = request.files.getlist('images')
        bucket = 'product-images'

        # Check if product already exists
        existing = supabase.table('products').select('*').eq('name', product_name).execute()
        if existing.data:
            flash(f'❌ Product "{product_name}" already exists.', 'error')
            return redirect('/admin_upload/')

        # Upload product to "products" table
        try:
            supabase.table('products').insert({
                'name': product_name,
                'price': float(price),
                'description': description,
                'category': category,
                'stock': int(stock),
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            flash(f'❌ Failed to insert product: {e}', 'error')
            return redirect('/admin_upload/')

        # Upload images to Supabase Storage and metadata to "product_images"
        for img in images:
            original_filename = img.filename
            content = img.read()

            unique_filename = f"{uuid.uuid4()}-{original_filename}"

            # Detect content type
            content_type, _ = mimetypes.guess_type(original_filename)
            if not content_type:
                content_type = 'application/octet-stream'  # fallback

            try:
                supabase.storage.from_(bucket).upload(
                    unique_filename,
                    content,
                    {"content-type": content_type}  # 👈 Add this
                )
                public_url = supabase.storage.from_(bucket).get_public_url(unique_filename)

                supabase.table('product_images').insert({
                    'image_name': unique_filename,
                    'image_url': public_url,
                    'product_name': product_name
                }).execute()
            except Exception as e:
                flash(f'❌ Failed to upload image {original_filename}: {e}', 'error')
                continue


        flash('✅ Product and images uploaded successfully!', 'success')
        return redirect('/admin_upload/')

    return render_template('admin_upload.html')
