import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, User, Blog, Product, ForumPost, ForumReply, Like, Expert, Consultation, init_db, Cart, Order, OrderItem
from google import genai


app = Flask(__name__)
genai_client = genai.Client(api_key="add api key here")

@app.route("/api/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_input
    )
    return jsonify({"reply": response.text})







# -------------------- APP CONFIG --------------------
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecretkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agrifarma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------- CLI DB INIT --------------------
@app.cli.command('db-init')
def db_init():
    with app.app_context():
        db.create_all()
        print('✅ Database initialized.')

# -------------------- DB MIGRATION COMMANDS --------------------
@app.cli.command('db-migrate')
def db_migrate():
    """Generate migration scripts."""
    from flask_migrate import upgrade, migrate as migrate_cmd, init
    with app.app_context():
        migrations_dir = os.path.join(os.getcwd(), 'migrations')
        if not os.path.exists(migrations_dir):
            init()
        migrate_cmd(message="auto migration")
        print("✅ Migration scripts generated.")

@app.cli.command('db-upgrade')
def db_upgrade():
    """Apply migrations to the database."""
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
        print("✅ Database upgraded successfully.")


# -------------------- HOME --------------------
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'expert':
        return redirect(url_for('expert_view'))
    else:
        return redirect(url_for('farmer_dashboard'))


@app.route('/home')
def home():
    latest_blogs = Blog.query.order_by(Blog.created_at.desc()).limit(5).all()
    latest_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    latest_forum = ForumPost.query.order_by(ForumPost.created_at.desc()).limit(5).all()
    return render_template('index.html', blogs=latest_blogs, products=latest_products, forum=latest_forum)


# -------------------- AUTH --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('⚠️ Email already registered', 'warning')
            return redirect(url_for('register'))

        user = User(name=name, email=email, password_hash=generate_password_hash(password), role='farmer')
        db.session.add(user)
        db.session.commit()
        flash('✅ Account created. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'expert':
                return redirect(url_for('expert_view'))
            else:
                return redirect(url_for('farmer_dashboard'))

        flash('❌ Invalid credentials', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Logged out', 'info')
    return redirect(url_for('login'))


# -------------------- PROFILE REDIRECT --------------------
@app.route('/profile')
@login_required
def profile():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'expert':
        return redirect(url_for('expert_view'))
    else:
        return redirect(url_for('farmer_dashboard'))

# -------------------- DASHBOARDS --------------------
@app.route('/dashboard')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    blogs = Blog.query.filter_by(user_id=current_user.id).all()
    products = Product.query.filter_by(user_id=current_user.id).all()
    posts = ForumPost.query.filter_by(user_id=current_user.id).all()
    
    # 🟢 Get all consultations for this farmer (by their email)
    consultations = Consultation.query.filter_by(farmer_email=current_user.email).order_by(
        Consultation.created_at.desc()
    ).all()

    return render_template(
        'dashboard.html',
        user=current_user,
        blogs=blogs,
        products=products,
        posts=posts,
        consultations=consultations
    )



@app.route('/expert/<int:expert_id>')
@app.route('/expert/dashboard')
@login_required
def expert_view(expert_id=None):
    if expert_id is None:
        if current_user.role != 'expert':
            flash('Access denied', 'danger')
            return redirect(url_for('index'))

        expert = Expert.query.filter_by(email=current_user.email).first()
        if not expert:
            flash("Expert profile not found. Contact admin.", "danger")
            return redirect(url_for('index'))

        consults = Consultation.query.filter_by(expert_id=expert.id).order_by(Consultation.created_at.desc()).all()
        forum_posts = ForumPost.query.order_by(ForumPost.created_at.desc()).limit(10).all()
        return render_template('expert_dashboard.html', expert=expert, consults=consults, posts=forum_posts)

    expert = Expert.query.get_or_404(expert_id)
    return render_template('expert_profile.html', expert=expert)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    users = User.query.all()
    experts = Expert.query.all()
    consults = Consultation.query.order_by(Consultation.created_at.desc()).all()
    blogs = Blog.query.all()
    products = Product.query.all()
    forums = ForumPost.query.all()

    return render_template(
        'admin_dashboard.html',
        users=users,
        experts=experts,
        consults=consults,
        blogs=blogs,
        products=products,
        forums=forums
    )


# -------------------- ADMIN FUNCTIONS --------------------
@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@login_required
def promote_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.role = 'expert'

    if not Expert.query.filter_by(email=user.email).first():
        new_expert = Expert(name=user.name, email=user.email, specialization='', is_verified=True)
        db.session.add(new_expert)

    db.session.commit()
    flash(f'✅ {user.name} promoted to Expert.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/demote/<int:user_id>', methods=['POST'])
@login_required
def demote_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.role = 'farmer'

    exp = Expert.query.filter_by(email=user.email).first()
    if exp:
        db.session.delete(exp)

    db.session.commit()
    flash(f'⚠️ {user.name} demoted to Farmer.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/blog/<int:blog_id>', methods=['POST'])
@login_required
def admin_delete_blog(blog_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    blog = Blog.query.get_or_404(blog_id)
    db.session.delete(blog)
    db.session.commit()
    flash('🗑️ Blog deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/delete/product/<int:product_id>', methods=['POST'])
@login_required
def admin_delete_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('🗑️ Product deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/delete/forum/<int:post_id>', methods=['POST'])
@login_required
def admin_delete_forum(post_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    post = ForumPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('🗑️ Forum post deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/delete/reply/<int:reply_id>', methods=['POST'])
@login_required
def admin_delete_reply(reply_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    reply = ForumReply.query.get_or_404(reply_id)
    db.session.delete(reply)
    db.session.commit()
    flash('🗑️ Reply deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


# -------------------- BLOG --------------------

@app.route('/blog')
def blog():
    """Display all blogs with Add New Blog button if user is logged in."""
    blogs = Blog.query.order_by(Blog.created_at.desc()).all()
    return render_template('blog.html', blogs=blogs)


@app.route('/blog/new', methods=['GET', 'POST'])
@login_required
def new_blog():
    """Create a new blog post."""
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image')
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        blog = Blog(
            title=title,
            content=content,
            image=filename,
            user_id=current_user.id
        )
        db.session.add(blog)
        db.session.commit()
        flash('📝 Blog posted successfully!', 'success')
        return redirect(url_for('blog'))  # redirect to all blogs

    return render_template('new_blog.html')


@app.route('/blog/<int:blog_id>')
def view_blog(blog_id):
    """View a single blog in full detail."""
    b = Blog.query.get_or_404(blog_id)
    return render_template('view_blog.html', blog=b)

## -------------------- PRODUCTS --------------------
@app.route('/products')
def products():
    """Display all products with search and category filter."""
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    # 🟢 Query with filters
    query = Product.query
    if q:
        query = query.filter(
            (Product.name.ilike(f"%{q}%")) | (Product.description.ilike(f"%{q}%"))
        )
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    items = query.order_by(Product.created_at.desc()).all()
    categories = sorted({p.category for p in Product.query.all() if p.category})

    return render_template(
        'products.html',
        products=items,
        q=q,
        selected_category=category,
        categories=categories
    )


@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Allow authenticated users to add new products."""
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            description = request.form['description'].strip()
            price = float(request.form['price'] or 0)      # Original price
            discount = float(request.form.get('discount', 0))
            stock = int(request.form.get('stock', 0))      # Quantity
            category = request.form.get('category', '').strip()

            image = request.files.get('image')
            filename = None
            if image and image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # ⚠️ Save original price in DB, calculate discounted price dynamically in model
            product = Product(
                name=name,
                description=description,
                price=price,         # Original price
                discount=discount,   # Discount %
                stock=stock,         # Quantity available
                category=category,
                image=filename,
                user_id=current_user.id,
                created_at=datetime.utcnow()
            )
            db.session.add(product)
            db.session.commit()

            flash(f'🛒 Product "{name}" added successfully!', 'success')
            return redirect(url_for('products'))

        except Exception as e:
            flash(f'❌ Error adding product: {str(e)}', 'danger')
            return redirect(url_for('new_product'))

    return render_template('new_product.html')


@app.route('/product/<int:product_id>')
def view_product(product_id):
    """View a single product with full details."""
    p = Product.query.get_or_404(product_id)

    # 💰 Calculate discounted price dynamically using model method
    discounted_price = p.final_price() if hasattr(p, 'final_price') else p.price
    stock_status = (
        "🟢 In Stock" if p.stock > 10 else
        "🟠 Limited Stock" if 1 <= p.stock <= 10 else
        "🔴 Out of Stock"
    )

    return render_template(
        'view_product.html',
        p=p,
        discounted_price=discounted_price,
        stock_status=stock_status
    )


# -------------------- FORUM --------------------
@app.route('/forum')
def forum():
    q = request.args.get('q', '')
    if q:
        posts = ForumPost.query.filter(
            ForumPost.title.ilike(f"%{q}%") | ForumPost.content.ilike(f"%{q}%")
        ).all()
    else:
        posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    return render_template('forum.html', posts=posts, q=q)


@app.route('/forum/new', methods=['GET', 'POST'])
@login_required
def new_thread():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image')
        filename = None
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        post = ForumPost(title=title, content=content, image_filename=filename, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('💬 New discussion created!', 'success')
        return redirect(url_for('forum'))

    return render_template('new_thread.html')


@app.route('/forum/<int:post_id>', methods=['GET', 'POST'])
def view_thread(post_id):
    post = ForumPost.query.get_or_404(post_id)
    replies = ForumReply.query.filter_by(post_id=post.id).order_by(ForumReply.created_at.asc()).all()

    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Please login to reply.', 'warning')
            return redirect(url_for('login'))
        content = request.form['content']
        reply = ForumReply(content=content, user_id=current_user.id, post_id=post.id)
        db.session.add(reply)
        db.session.commit()
        flash('💬 Reply posted successfully!', 'success')
        return redirect(url_for('view_thread', post_id=post.id))
    return render_template('view_thread.html', post=post, replies=replies)


# -------------------- LIKE SYSTEM --------------------
@app.route('/like/post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = ForumPost.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post_id))
    db.session.commit()
    return jsonify({'count': post.reply_count()})


@app.route('/like/reply/<int:reply_id>', methods=['POST'])
@login_required
def like_reply(reply_id):
    reply = ForumReply.query.get_or_404(reply_id)
    like = Like.query.filter_by(user_id=current_user.id, reply_id=reply_id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(user_id=current_user.id, reply_id=reply_id))
    db.session.commit()
    return jsonify({'count': reply.like_count()})


# -------------------- EXPERT DIRECTORY --------------------
@app.route('/experts')
def experts():
    all_experts = Expert.query.order_by(Expert.is_verified.desc()).all()
    return render_template('experts.html', experts=all_experts)


# -------------------- CONSULTATION --------------------
@app.route('/consult', methods=['GET', 'POST'])
@login_required
def consult():
    if request.method == 'POST':
        farmer_name = request.form['farmer_name']
        farmer_email = request.form['farmer_email']
        problem = request.form['problem']
        consult = Consultation(farmer_name=farmer_name, farmer_email=farmer_email, problem=problem)
        db.session.add(consult)
        db.session.commit()
        flash('✅ Your query has been sent to our experts!', 'success')
        return redirect(url_for('consult'))
    all_consults = Consultation.query.order_by(Consultation.created_at.desc()).all()
    return render_template('consult.html', consultations=all_consults)
# -------------------- CONSULTATION REQUEST --------------------
@app.route('/consult/request/<int:expert_id>', methods=['GET', 'POST'])
@login_required
def consultation_request(expert_id):
    expert = Expert.query.get_or_404(expert_id)

    if request.method == 'POST':
        farmer_name = request.form['farmer_name']
        farmer_email = request.form['farmer_email']
        problem = request.form['problem']

        consult = Consultation(
            farmer_name=farmer_name,
            farmer_email=farmer_email,
            expert_id=expert.id,
            problem=problem
        )
        db.session.add(consult)
        db.session.commit()

        flash(f'✅ Your request has been sent to {expert.name}.', 'success')
        return redirect(url_for('experts'))

    return render_template('consultation_request.html', expert=expert)
# -------------------- CONSULTATION DETAIL (VIEW + REPLY) --------------------
@app.route('/consultation/<int:cid>', methods=['GET', 'POST'])
@login_required
def consultation_detail(cid):
    """
    Show and handle expert reply for a consultation.
    """
    consult = Consultation.query.get_or_404(cid)
    expert = Expert.query.filter_by(email=current_user.email).first()

    # Permission check: only assigned expert or admin can reply
    if not (current_user.role == 'admin' or current_user.role == 'expert'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # ✅ use the correct name from HTML form
        response_text = request.form.get('response', '').strip()
        if not response_text:
            flash('⚠️ Response cannot be empty.', 'warning')
            return redirect(url_for('consultation_detail', cid=cid))

        # ✅ save the response properly
        consult.response = response_text
        consult.status = 'Resolved'
        consult.expert_id = expert.id if expert else None

        from datetime import datetime
        consult.updated_at = datetime.utcnow()
        db.session.commit()

        flash('✅ Response sent successfully to the farmer.', 'success')
        return redirect(url_for('consultation_detail', cid=cid))

    return render_template('consultation_detail.html', consult=consult, expert=expert)




# -------------------- EXPERT DASHBOARD (public profile + expert view) --------------------
@app.route('/expert/<int:expert_id>/dashboard')
@login_required
def expert_dashboard(expert_id):
    """
    Expert dashboard showing all consultation requests assigned to this expert.
    Admins can view any expert dashboard. Experts can view only their own dashboard.
    """
    expert = Expert.query.get_or_404(expert_id)

    # Permission: admin OR the expert themself
    if not (current_user.role == 'admin' or (current_user.role == 'expert' and expert.email == current_user.email)):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    consults = Consultation.query.filter_by(expert_id=expert.id).order_by(Consultation.created_at.desc()).all()
    return render_template('expert_dashboard.html', expert=expert, consults=consults)

# -------------------- UPDATE CONSULTATION RESPONSE --------------------
@app.route('/consultation/update/<int:cid>', methods=['POST'])
@login_required
def update_consultation(cid):
    """
    Allow experts or admins to respond to a consultation request.
    """
    consult = Consultation.query.get_or_404(cid)

    # Get the expert assigned (if any)
    expert = Expert.query.get(consult.expert_id) if consult.expert_id else None

    # Permission check — only assigned expert or admin can update
    if not (current_user.role == 'admin' or
            (current_user.role == 'expert' and expert and expert.email == current_user.email)):
        flash('🚫 Access denied — you are not authorized to respond.', 'danger')
        return redirect(url_for('index'))

    # Get response text
    response_text = request.form.get('response')

    if not response_text or response_text.strip() == "":
        flash('⚠️ Response cannot be empty.', 'warning')
        return redirect(url_for('consultation_detail', cid=cid))

    # Update consultation record
    consult.response = response_text
    consult.status = 'Resolved'
    from datetime import datetime
    consult.updated_at = datetime.utcnow()

    db.session.commit()
    flash('✅ Response submitted successfully.', 'success')

    return redirect(url_for('consultation_detail', cid=cid))


# -------------------- GLOBAL SEARCH --------------------
@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = {'blogs': [], 'products': [], 'forums': []}
    if q:
        results['blogs'] = Blog.query.filter(Blog.title.ilike(f"%{q}%") | Blog.content.ilike(f"%{q}%")).all()
        results['products'] = Product.query.filter(Product.name.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%")).all()
        results['forums'] = ForumPost.query.filter(ForumPost.title.ilike(f"%{q}%") | ForumPost.content.ilike(f"%{q}%")).all()
    return render_template('search_results.html', q=q, results=results)


# -------------------- ADMIN SETUP --------------------
@app.route('/setup-admin')
def setup_admin():
    existing_admin = User.query.filter_by(email='syedasadkazmi41@gmail.com').first()
    if existing_admin:
        return "<h3>✅ Admin already exists: syedasadkazmi41@gmail.com</h3>"

    admin = User(
        name='Site Admin',
        email='syedasadkazmi41@gmail.com',
        password_hash=generate_password_hash('asad123'),
        role='admin',
        profession='Administrator',
        expertise='System Management'
    )
    db.session.add(admin)
    db.session.commit()
    return "<h3>🎉 Admin created successfully!<br>Email: syedasadkazmi41@gmail.com<br>Password: asad123</h3>"


# -------------------- STATIC FILES --------------------
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# -------------------- CART SYSTEM --------------------


@app.route('/cart')
@login_required
def cart():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.total_price() for item in items)
    return render_template('cart.html', items=items, total=total)


# -------------------- ADD TO CART --------------------
@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        quantity = int(request.form.get('quantity', 1))
        quantity = max(quantity, 1)

        if quantity > product.stock:
            flash(f"⚠️ Only {product.stock} items available.", "warning")
            return redirect(url_for('view_product', product_id=product.id))

        cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if cart_item:
            new_qty = cart_item.quantity + quantity
            if new_qty > product.stock:
                flash(f"⚠️ Cannot add more than {product.stock} items.", "warning")
                return redirect(url_for('view_product', product_id=product.id))
            cart_item.quantity = new_qty
        else:
            cart_item = Cart(user_id=current_user.id, product_id=product.id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()
        flash(f"✅ {product.name} added to cart.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error adding to cart: {str(e)}", "danger")

    return redirect(url_for('checkout'))


# -------------------- UPDATE CART --------------------
@app.route('/cart/update/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    item = Cart.query.get_or_404(cart_id)
    if item.user_id != current_user.id:
        flash("🚫 Unauthorized action!", "danger")
        return redirect(url_for('cart'))

    try:
        quantity = int(request.form.get('quantity', 1))
        quantity = max(quantity, 1)

        if quantity > item.product.stock:
            flash(f"⚠️ Only {item.product.stock} items available.", "warning")
            return redirect(url_for('cart'))

        item.quantity = quantity
        db.session.commit()
        flash(f"✅ {item.product.name} quantity updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error updating cart: {str(e)}", "danger")

    return redirect(url_for('cart'))


# -------------------- REMOVE ITEM --------------------
@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    item = Cart.query.get_or_404(cart_id)
    if item.user_id != current_user.id:
        flash("🚫 Unauthorized action!", "danger")
        return redirect(url_for('cart'))

    try:
        db.session.delete(item)
        db.session.commit()
        flash(f"🗑️ {item.product.name} removed from cart.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error removing from cart: {str(e)}", "danger")

    return redirect(url_for('cart'))


# -------------------- CHECKOUT PAGE --------------------
@app.route('/checkout')
@login_required
def checkout():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty!", "info")
        return redirect(url_for('cart'))

    total = sum(item.total_price() for item in items)
    return render_template('checkout.html', items=items, total=total)


# -------------------- PLACE ORDER --------------------
@app.route('/order/place', methods=['POST'])
@login_required
def place_order():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty!", "info")
        return redirect(url_for('cart'))

    try:
        total_amount = sum(item.total_price() for item in items)

        # Create Order
        order = Order(user_id=current_user.id, total_amount=total_amount, status='Pending')
        db.session.add(order)
        db.session.flush()  # Get order.id before commit

        # Create OrderItems & Update Stock
        for item in items:
            if item.quantity > item.product.stock:
                flash(f"⚠️ Not enough stock for {item.product.name}.", "warning")
                db.session.rollback()
                return redirect(url_for('cart'))

            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product.id,
                quantity=item.quantity,
                price=item.product.final_price()
            )
            db.session.add(order_item)

            # Reduce product stock
            item.product.stock -= item.quantity

        # Clear cart
        for item in items:
            db.session.delete(item)

        db.session.commit()
        flash("✅ Order placed successfully!", "success")
        return redirect(url_for('order_details', order_id=order.id))
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error placing order: {str(e)}", "danger")
        return redirect(url_for('cart'))


# -------------------- ORDER DETAILS --------------------
@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("🚫 Unauthorized access!", "danger")
        return redirect(url_for('cart'))

    return render_template('order_details.html', order=order)

# -------------------- APP ENTRY --------------------
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
