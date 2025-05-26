from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime, timedelta



app = Flask(__name__)
supabase = create_client(url, key)

from routes.admin_dashboard import admin_dashboard_bp
from routes.admin_modify import admin_modify_bp
from routes.admin_upload import admin_upload_bp
from routes.admin_delete import admin_delete_bp
from routes.admin_login import admin_login_bp
from routes.admin_order import admin_order_bp
from routes.admin_analytics import admin_analytics_bp


app.register_blueprint(admin_login_bp)
app.register_blueprint(admin_dashboard_bp)
app.register_blueprint(admin_modify_bp, url_prefix='/admin_modify')
app.register_blueprint(admin_upload_bp)
app.register_blueprint(admin_delete_bp)
app.register_blueprint(admin_order_bp)
app.register_blueprint(admin_analytics_bp)


# Home Route
@app.route('/')
def home():
    # Pop the error message from the session for display on the sign-in page
    error_message = session.pop('error_message', None)
    return render_template('sign-in.html', error_message=error_message)

# Validate Sign-in
@app.route('/validate-signin', methods=['POST'])
def validate_signin():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        session['error_message'] = "Please enter both email and password."
        return redirect(url_for('home')) # Redirect back to sign-in page

    response = supabase.table('users').select('*').eq('email', email).execute()
    users = response.data

    if not users:
        # User with this email does not exist
        session['error_message'] = "User does not exist. Please sign up."
        return redirect(url_for('home')) # Redirect back to sign-in page

    user = users[0]
    if user['password'] != password:
        # Correct email, but incorrect password
        session['error_message'] = "Wrong password. Please try again."
        return redirect(url_for('home')) # Redirect back to sign-in page

    # If email and password are correct
    session['email'] = email
    # Assuming 'index' is your dashboard or main authenticated page
    return redirect(url_for('index'))

@app.route('/sign-up')
def signup():
    # Pass any error messages from the session to the template
    error_message = session.pop('error_message', None)
    return render_template('sign-up.html', error_message=error_message)

# Validate Sign-Up
@app.route('/validate-signup', methods=['POST'])
def validate_signup():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        session['error_message'] = "All fields are required."
        return redirect(url_for('signup'))

    # Email validation
    if not email.endswith('@gmail.com'):
        session['error_message'] = "Please insert an your gmail account (e.g., your_email@gmail.com)."
        return redirect(url_for('signup'))

    # Password length validation
    if len(password) != 8:
        session['error_message'] = "Password must be exactly 8 characters long."
        return redirect(url_for('signup'))

    response = supabase.table('users').select('*').eq('email', email).execute()
    if response.data:
        session['error_message'] = "User already exists, Please sign in."
        return redirect(url_for('signup')) # Stay on the sign-up page

    insert_response = supabase.table('users').insert({
        "email": email,
        "password": password
    }).execute()

    if insert_response and insert_response.data:
        new_user = insert_response.data[0]
        session['email'] = email
        session['name'] = new_user.get('name', '')
        session['phone'] = new_user.get('phone', '')
        session['address'] = new_user.get('address', '')
        return redirect(url_for('home'))
    else:
        session['error_message'] = "Error during sign-up. Please try again."
        return redirect(url_for('signup'))    

# Index (after sign-in)
@app.route('/index')
def index():
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('index.html')

#  Wishlist Routes (PLACE IT HERE)
@app.route('/wishlist', methods=['GET'])
def wishlist():
    if 'email' not in session:
        return redirect(url_for('home'))

    response = supabase.table('wishlist').select('*').eq('user_email', session['email']).execute()
    wishlist_items = response.data
    updated_wishlist_items = []

    for item in wishlist_items:
        updated_item = item.copy()
        if item.get('source') == 'Price Compare':
            product_name = item.get('product_title')
            if product_name:
                image_results = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute()
                images = [img["image_url"] for img in image_results.data if "image_url" in img]
                updated_item['images'] = images
            else:
                updated_item['images'] = []
        else:
            updated_item['images'] = [item.get('product_photo', '')] # For other sources, just use the stored photo

        updated_wishlist_items.append(updated_item)

    return render_template('wishlist.html', wishlist=updated_wishlist_items)

# ... (your existing imports and code) ...

# app.py

# ... (rest of your imports and code) ...

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        flash("You need to be logged in to add items to your wishlist", "error")
        return redirect(url_for('home'))

    try:
        product_url = request.form['product_url']
        product_name = request.form['product_title']
        product_price = request.form['product_price']
        product_image = request.form['product_photo']
        user_email = session['email']

        # --- THIS IS THE CRITICAL CHANGE ---
        # Change 'source' to 'source_type' to match your HTML forms
        # And provide a more descriptive default if it's missing (though it shouldn't be with correct forms)
        source = request.form.get('source_type', 'Unknown Source')

        # Logic for Admin DB products and product_url consistency in wishlist table
        # This part is important for unique identification in the wishlist, especially for Admin DB products
        if source == 'Price Compare':
            # For Admin DB, product_url in wishlist should be the product's unique name
            # assuming product_name is sufficiently unique for Admin DB products.
            product_url_for_db = product_name
        else:
            # For external sources (Amazon/Myntra), use the actual product URL
            product_url_for_db = product_url


        existing = supabase.table('wishlist').select('*') \
            .eq('user_email', user_email) \
            .eq('product_url', product_url_for_db) \
            .execute()

        if not existing.data:
            supabase.table('wishlist').insert({
                'user_email': user_email,
                'product_url': product_url_for_db, # Use the consistent URL for comparison
                'product_title': product_name,
                'product_price': product_price,
                'product_photo': product_image,
                'source': source # This will now store 'Amazon', 'Myntra', or 'Admin DB'
            }).execute()
            flash("Product added to wishlist!", "success")
        else:
            flash("This product is already in your wishlist", "info")

    except Exception as e:
        flash(f"Error adding to wishlist: {str(e)}", "error")
        # Added a print for server-side debugging
        print(f"ERROR in add_to_wishlist: {e}")

    # Redirect to the wishlist page after adding
    return redirect(url_for('wishlist')) # Use url_for for robustness

# ... (rest of your app.py) ...
    
# In app.py

@app.route('/remove-from-wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        flash("You need to be logged in to remove items from your wishlist", "error")
        return redirect(url_for('home'))

    # Get the wishlist_id which is the unique ID of the row in the 'wishlist' table
    wishlist_id_to_remove = request.form.get('wishlist_id')
    user_email = session['email']

    if wishlist_id_to_remove:
        try:
            # Convert to int, as 'id' in Supabase is usually an integer primary key
            wishlist_id_to_remove = int(wishlist_id_to_remove)

            # Delete based on the unique wishlist item ID and user email for security
            response = supabase.table('wishlist') \
                .delete() \
                .eq('id', wishlist_id_to_remove) \
                .eq('user_email', user_email) \
                .execute()

            if response.data:
                flash("Product removed from wishlist!", "success")
            else:
                # This could mean ID was not found or email didn't match the record
                flash("Product not found in your wishlist or could not be removed. (ID mismatch)", "error")
        except ValueError:
            flash("Invalid wishlist ID provided.", "error")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            print(f"Error removing from wishlist: {e}") # Debugging server-side

    else:
        flash("No wishlist item ID specified for removal.", "error")

    # Redirect back to the wishlist page
    return redirect(url_for('wishlist'))

@app.route("/product/<product_name>")
def product_detail(product_name):
    response = supabase.table("products").select("*").eq("name", product_name).execute()
    product = response.data[0] if response.data else None
    images = []
    reviews_response = supabase.table("product_reviews").select("*").eq("product_name", product_name).execute()
    reviews = reviews_response.data

    # Initialize in_wishlist flag
    in_wishlist = False
    wishlist_item_id = None # To store the specific wishlist item ID if found

    if product:
        # Fetch images from the product_images table
        image_results = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute()
        images = [img["image_url"] for img in image_results.data if "image_url" in img]

        # Check if the product is in the user's wishlist
        if 'email' in session:
            user_email = session['email']
            
            wishlist_check_response = supabase.table('wishlist') \
                                            .select('id', 'product_url') \
                                            .eq('user_email', user_email) \
                                            .eq('product_title', product_name) \
                                            .execute()
            
            if wishlist_check_response.data:
                # If product found, get the wishlist item ID
                in_wishlist = True
                wishlist_item_id = wishlist_check_response.data[0]['id'] # Get the ID of the first match
                
        return render_template(
            "product_detail.html",
            product=product,
            images=images,
            reviews=reviews,
            datetime=datetime,
            in_wishlist=in_wishlist,         # Pass the flag
            wishlist_item_id=wishlist_item_id # Pass the ID for removal
        )
    else:
        return "Product not found", 404

# ... (your existing /add_to_wishlist and /remove-from-wishlist routes) ...

# Ensure your /add_to_wishlist handles 'Admin DB' source product_url consistently    

# ... other imports and configurations ...

@app.route("/submit_review", methods=["POST"])
def submit_review():
    if 'email' not in session:
        flash("You must be logged in to submit a review.", "error")
        return redirect(url_for("home"))

    product_name = request.form.get("product_name")
    rating = int(request.form.get("rating"))
    comment = request.form.get("comment")
    user_email = session['email']

    # Check if the user has already submitted a review for this product
    existing_review_response = supabase.table("product_reviews").select("*").eq("product_name", product_name).eq("user_email", user_email).execute()
    existing_review = existing_review_response.data

    if existing_review:
        flash("You have already submitted a review for this product. You can edit your existing review.", "info")
        return redirect(url_for("product_detail", product_name=product_name))
    else:
        try:
            supabase.table("product_reviews").insert({
                "product_name": product_name,
                "user_email": user_email,
                "rating": rating,
                "comment": comment,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            flash("Your review has been submitted successfully!", "success")
        except Exception as e:
            flash(f"An error occurred while submitting your review: {e}", "error")
        return redirect(url_for("product_detail", product_name=product_name))

# ... rest of your app.py ...

# In app.py

@app.route("/edit_review/<int:review_id>")
def edit_review_page(review_id):
    if 'email' not in session:
        flash("You must be logged in to edit a review.", "error")
        return redirect(url_for("home"))

    review_response = supabase.table("product_reviews").select("*").eq("id", review_id).eq("user_email", session['email']).execute()
    review_to_edit = review_response.data[0] if review_response.data else None

    if review_to_edit:
        product_name = review_to_edit['product_name']
        response = supabase.table("products").select("*").eq("name", product_name).execute()
        product = response.data[0] if response.data else None
        images = []
        reviews_response = supabase.table("product_reviews").select("*").eq("product_name", product_name).execute()
        reviews = reviews_response.data

        if product:
            image_results = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute()
            images = [img["image_url"] for img in image_results.data if "image_url" in img]
            return render_template(
                "product_detail.html",
                product=product,
                images=images,
                reviews=reviews,
                datetime=datetime,
                editing_review=review_to_edit # <-- This is correctly passed
            )
        else:
            return "Product not found", 404
    else:
        flash("You are not authorized to edit this review.", "warning")
        return redirect(url_for("home"))
    
@app.route("/update_review/<int:review_id>", methods=["POST"])
def update_review(review_id):
    if 'email' not in session:
        flash("You must be logged in to update a review.", "error")
        return redirect(url_for("home"))

    rating = int(request.form.get("rating"))
    comment = request.form.get("comment")
    product_name = request.form.get("product_name")

    try:
        supabase.table("product_reviews").update({
            "rating": rating,
            "comment": comment,
            "created_at": datetime.utcnow().isoformat() # Update the timestamp
        }).eq("id", review_id).eq("user_email", session['email']).execute()
        flash("Your review has been updated successfully!", "success")
    except Exception as e:
        flash(f"An error occurred while updating your review: {e}", "error")

    return redirect(url_for("product_detail", product_name=product_name))

@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect('/sign-in')  # Redirect to sign-in if not logged in

    user = {
        'email': session['email'],
        'name': session.get('name', 'Not provided'),
        'phone': session.get('phone', 'N/A'),
        'address': session.get('address', 'Not provided'),
    }

    return render_template('profile.html', user=user)

@app.route('/edit-profile')
def edit_profile():
    if 'email' not in session:
        return redirect('/sign-in')

    user = {
        'email': session['email'],
        'name': session.get('name', ''),
        'phone': session.get('phone', ''),
        'address': session.get('address', ''),
    }
    return render_template('edit_profile.html', user=user)

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'email' not in session:
        return redirect('/sign-in')

    updated_name = request.form.get('name')
    updated_phone = request.form.get('phone')
    updated_address = request.form.get('address')
    email = session['email']

    # Update in Supabase
    supabase.table('users').update({
        'name': updated_name,
        'phone': updated_phone,
        'address': updated_address
    }).eq('email', email).execute()

    # Also update the session
    session['name'] = updated_name
    session['phone'] = updated_phone
    session['address'] = updated_address

    return redirect('/profile')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/order/<product_name>', methods=['GET'])
def order_page(product_name):
    if 'email' not in session:
        return redirect(url_for('signin'))

    email = session['email']

    # Fetch user details
    user_data = supabase.table('users').select('*').eq('email', email).execute().data[0]

    # Fetch product details
    product_data = supabase.table('products').select('*').eq('name', product_name).execute().data[0]

    return render_template('order.html', user=user_data, product=product_data)


@app.route('/submit-order', methods=['POST'])
def submit_order():
    email = session.get('email')
    product_name = request.form.get('product_name')
    quantity = int(request.form.get('quantity'))
    new_address = request.form.get('address')
    payment_method = request.form.get('payment_method')

# Fetch product by name
    product_response = supabase.table('products').select('*').eq('name', product_name).execute()
    if not product_response.data:
        flash("Product not found.", "error")
        return redirect(url_for('index'))

    product = product_response.data[0]
    stock = product['stock']
    unit_price = product['price']

    if quantity > stock:
        flash(f"Not enough stock available for {product_name}. Available: {stock}", "warning")
        return redirect(url_for('product_detail', product_name=product_name))

# Update stock
    new_stock = stock - quantity
    supabase.table('products').update({'stock': new_stock}).eq('name', product_name).execute()

# Update user's address
    supabase.table('users').update({'address': new_address}).eq('email', email).execute()

    total_price = unit_price * quantity
    order_time = datetime.now() # Store as a datetime object
    formatted_order_time = order_time.strftime("%Y-%m-%d %H:%M:%S")
    delivery_date = order_time + timedelta(days=2)
    formatted_delivery_date = delivery_date.strftime("%Y-%m-%d")

    order_data = {
        'email': email,
        'product_name': product_name,
        'quantity': quantity,
        'total_price': int(total_price),
        'address': new_address,
        'payment_method': payment_method,
        'order_time': formatted_order_time,
        'delivery_date': formatted_delivery_date,
        'status': 'Pending' # Set initial status for the order
    }

# Insert into 'Order' table with delivery date and status
    try:
        insert_response = supabase.table('Order').insert(order_data).execute()
        order_id = insert_response.data[0]['id'] # Get the ID of the newly created order
        flash("Order placed successfully!", "success")
    except Exception as e:
        flash(f"Error placing order: {e}", "error")
        return redirect(url_for('index')) # Redirect to a safe page on error

    if payment_method == 'cod':
    # Pass the order_id to the receipt page
        return render_template('receipt.html', **order_data, order_id=order_id)
    else:
    # For other payment methods (if you implement them later), you might redirect elsewhere
        return redirect(url_for('orders_page'))
    
@app.route('/order-history')
def orders_page():
    if 'email' not in session:
        return redirect(url_for('home'))

    email = session['email']
    orders_response = supabase.table('Order').select('*').eq('email', email).order('order_time', desc=True).execute()
    user_orders = orders_response.data

    updated_orders = []
    for order in user_orders:
        product_name = order['product_name']
        image_results = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute()
        images = [img["image_url"] for img in image_results.data if "image_url" in img]
        order['product_image'] = images[0] if images else ''  # Get the first image if available
        updated_orders.append(order)

    return render_template('order_history_page.html', user_orders=updated_orders)


@app.route('/view-receipt/<int:order_id>')
def view_receipt(order_id):
    if 'email' not in session:
        print("Error: Email not in session")
        return redirect(url_for('home'))

    email = session['email']
    print(f"Fetching receipt for order ID: {order_id} and email: {email}")
    order_response = supabase.table('Order').select('*').eq('id', order_id).eq('email', email).execute()
    print("Supabase Response:", order_response)
    order_data = order_response.data[0] if order_response.data else None
    print("Order Data:", order_data)

    if order_data:
        return render_template('receipt.html', **order_data)
    else:
        return "Order not found or you don't have permission to view this receipt.", 404
    
@app.route('/cancel-order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'email' not in session:
        flash("You must be logged in to cancel an order.", "error")
        return redirect(url_for('home'))

    email = session['email']

    # 1. Fetch the order details
    order_response = supabase.table('Order').select('*').eq('id', order_id).eq('email', email).execute()
    order = order_response.data[0] if order_response.data else None

    if not order:
        flash("Order not found or you don't have permission to cancel it.", "error")
        return redirect(url_for('orders_page'))

    # Check if the order can be cancelled (e.g., if status is 'Pending')
    if order['status'] != 'Pending': # Assuming only 'Pending' orders can be cancelled
        flash(f"Order {order_id} cannot be cancelled as its status is '{order['status']}'.", "warning")
        return redirect(url_for('orders_page'))

    try:
        # 2. Update order status to 'Cancelled'
        supabase.table('Order').update({'status': 'Cancelled'}).eq('id', order_id).execute()

        # 3. Return product quantity to stock
        product_name = order['product_name']
        quantity_cancelled = order['quantity']

        product_response = supabase.table('products').select('stock').eq('name', product_name).execute()
        current_stock = product_response.data[0]['stock'] if product_response.data else 0

        new_stock = current_stock + quantity_cancelled
        supabase.table('products').update({'stock': new_stock}).eq('name', product_name).execute()

        flash(f"Order {order_id} has been successfully cancelled and stock updated.", "success")
    except Exception as e:
        flash(f"An error occurred while cancelling order {order_id}: {e}", "error")
    return redirect(url_for('orders_page'))


# ... (your existing imports and code) ...

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return "No search query provided!", 400

    print(f"Searching for: {query}")  # Debug

    amazon_products = fetch_amazon_products(query)
    myntra_products = get_myntra_results(query)
    supabase_results = search_supabase_products(query)

    all_products = []

    # Fetch user's wishlist for comparison
    user_wishlist_product_urls = set()
    if 'email' in session:
        wishlist_response = supabase.table('wishlist').select('product_url').eq('user_email', session['email']).execute()
        user_wishlist_product_urls = {item['product_url'] for item in wishlist_response.data}


    # Format Amazon results
    for p in amazon_products:
        product_url = p.get('product_url', '')
        all_products.append({
            'product_title': p.get('product_title', ''),
            'product_price': p.get('product_price', ''), # Store raw price
            'product_photo': p.get('product_photo', ''),
            'product_url': product_url,
            'source': 'Amazon',
            'images': [],
            'in_wishlist': product_url in user_wishlist_product_urls # Add this flag
        })

    # Format Myntra results
    for p in myntra_products:
        product_url = p['link']
        all_products.append({
            'product_title': p['title'],
            'product_price': p['price'], # Store raw price
            'product_photo': p['image'],
            'product_url': product_url,
            'source': 'Myntra',
            'images': [],
            'in_wishlist': product_url in user_wishlist_product_urls # Add this flag
        })

    # Format Supabase results
    for p in supabase_results:
        product_name = p.get('name', '')
        image_results = supabase.table("product_images").select("image_url").eq("product_name", product_name).execute()
        images = [img["image_url"] for img in image_results.data if "image_url" in img]
        
        # For Admin DB products, use a unique identifier or product_name for wishlist check
        # Assuming 'name' is unique enough for wishlist identification
        product_identifier = product_name 
        
        all_products.append({
            'product_title': product_name,
            'product_price': p.get('price', ''), # Store raw price
            'product_photo': images[0] if images else '',
            'source': 'Price Compare',
            'images': images,
            'in_wishlist': product_identifier in user_wishlist_product_urls # Add this flag
        })

    def unified_price_parser(item):
        price_str = str(item.get('product_price', '')).replace('₹', '').replace('Rs.', '').replace(',', '').strip()
        try:
            return float(price_str)
        except ValueError:
            return float('inf')

    all_products.sort(key=unified_price_parser)

    for product in all_products:
        print(f"{product['source']}: {product['product_title']} - {product['product_price']} - In Wishlist: {product['in_wishlist']}") # Print raw price for debugging
    
    return render_template(
        'result.html',
        products=all_products,
        query=query,
        lowest_amazon=min((p for p in all_products if p['source'] == 'Amazon'), key=unified_price_parser, default=None),
        lowest_myntra=min((p for p in all_products if p['source'] == 'Myntra'), key=unified_price_parser, default=None),
        lowest_supabase=min((p for p in all_products if p['source'] == 'Price Compare'), key=unified_price_parser, default=None)
    )

#  Helper Functions (LAST)
def fetch_amazon_products(query):
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        
    }
    params = {"query": query, "country": "IN"}

    response = requests.get(url, headers=headers, params=params)
    print(response.status_code, response.text)  # Debugging API Response

    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("products", [])
    else:
        return []
    
def get_myntra_results(query):
    options = Options()
    options.add_argument("--headless=new")  # newer headless mode (if supported)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)

    search_url = f"https://www.myntra.com/{query}"
    driver.get(search_url)
    time.sleep(3)

    products = []

    product_elements = driver.find_elements(By.CLASS_NAME, "product-base")
    for product in product_elements[:10]:
        try:
            title = product.find_element(By.CLASS_NAME, 'product-product').text
        except:
            title = "N/A"

        try:
            price = product.find_element(By.CLASS_NAME, 'product-discountedPrice').text
        except:
            try:
                price = product.find_element(By.CLASS_NAME, 'product-price').text
            except:
                price = "N/A"

        try:
            image = product.find_element(By.TAG_NAME, 'img').get_attribute('src')
        except:
            image = ""

        try:
            link = product.find_element(By.TAG_NAME, 'a').get_attribute('href')
            if not link.startswith("http"):
                link = "https://www.myntra.com" + link
        except:
            link = "#"

        products.append({
            'title': title,
            'price': price,
            'image': image,
            'link': link
        })

    driver.quit()
    return products

def search_supabase_products(search_query):
    result = supabase.table("products").select("*").ilike("name", f"%{search_query}%").execute()
    return result.data if result.data else []



# ----------------
# Run Server
# ----------------
if __name__ == '__main__':
    app.run(debug=True)
