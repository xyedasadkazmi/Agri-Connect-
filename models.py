from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# -------------------- USER MODEL --------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # role-based fields
    role = db.Column(db.String(50), default='farmer')   # farmer | expert | admin
    profession = db.Column(db.String(80))
    expertise = db.Column(db.String(80))
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)  # for experts verified by admin

    # Relationships
    blogs = db.relationship('Blog', backref='user', lazy=True)
    products = db.relationship('Product', backref='user', lazy=True)
    posts = db.relationship('ForumPost', backref='user', lazy=True)
    replies = db.relationship('ForumReply', backref='user', lazy=True)
    cart_items = db.relationship('Cart', backref='user', lazy=True)  # ✅ fixed
    orders = db.relationship('Order', backref='user', lazy=True)

    # helpers
    def is_admin(self):
        return self.role == 'admin'

    def is_expert(self):
        return self.role == 'expert'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# -------------------- BLOG MODEL --------------------
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), index=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Blog {self.title}>"


# -------------------- PRODUCT MODEL --------------------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), index=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, default=0.0, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(100), nullable=True)
    stock = db.Column(db.Integer, default=10, nullable=False)  # Quantity available
    image = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def final_price(self):
        """Return the price after discount (if any)."""
        if self.discount and self.discount > 0:
            return round(self.price * (1 - self.discount / 100), 2)
        return self.price

    def in_stock(self):
        """Return True if product is in stock."""
        return self.stock > 0

    def stock_status(self):
        """Return stock status string with emoji for UI."""
        if self.stock > 10:
            return "🟢 In Stock"
        elif 1 <= self.stock <= 10:
            return "🟠 Limited Stock"
        else:
            return "🔴 Out of Stock"

    def __repr__(self):
        return f"<Product {self.name} | Price: {self.price} | Stock: {self.stock}>"


# -------------------- CART MODEL --------------------
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', backref=db.backref('cart_items', lazy=True))
    # user relationship handled by backref from User.cart_items

    # Helper methods
    def total_price(self):
        return self.quantity * self.product.final_price()

    def increase_quantity(self, amount=1):
        self.quantity += amount

    def decrease_quantity(self, amount=1):
        self.quantity = max(self.quantity - amount, 1)

    def __repr__(self):
        return f"<Cart User:{self.user_id} Product:{self.product_id} Qty:{self.quantity}>"


# -------------------- ORDER MODEL --------------------
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending / Paid / Failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def calculate_total(self):
        return sum(item.total() for item in self.order_items)

    def __repr__(self):
        return f"<Order User:{self.user_id} Total:{self.total_amount} Status:{self.status}>"


# -------------------- ORDER ITEM MODEL --------------------
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def total(self):
        return self.quantity * self.price

    def __repr__(self):
        return f"<OrderItem Order:{self.order_id} Product:{self.product_id} Qty:{self.quantity} Total:{self.total()}>"


# -------------------- EXPERT MODEL --------------------
class Expert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    education = db.Column(db.String(200))
    specialization = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    bio = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    consultations = db.relationship('Consultation', backref='expert', lazy=True)

    def __repr__(self):
        return f"<Expert {self.name}>"


# -------------------- FORUM POST MODEL --------------------
class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), index=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    replies = db.relationship('ForumReply', backref='post', cascade='all, delete-orphan', lazy=True)
    likes = db.relationship('Like', primaryjoin="Like.post_id==ForumPost.id", viewonly=True, lazy=True)

    def reply_count(self):
        return len(self.replies)

    def like_count(self):
        return Like.query.filter_by(post_id=self.id).count()

    def __repr__(self):
        return f"<ForumPost {self.title}>"


# -------------------- FORUM REPLY MODEL --------------------
class ForumReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    likes = db.relationship('Like', primaryjoin="Like.reply_id==ForumReply.id", viewonly=True, lazy=True)

    def like_count(self):
        return Like.query.filter_by(reply_id=self.id).count()

    def __repr__(self):
        return f"<ForumReply {self.id}>"


# -------------------- LIKE MODEL --------------------
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey('forum_reply.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Like user={self.user_id} post={self.post_id} reply={self.reply_id}>"


# -------------------- CONSULTATION MODEL --------------------
class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_name = db.Column(db.String(120), nullable=False)
    farmer_email = db.Column(db.String(120), nullable=True)
    problem = db.Column(db.Text, nullable=False)

    response = db.Column(db.Text, nullable=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('expert.id'), nullable=True)

    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Consultation {self.farmer_name} - {self.status}>"


# -------------------- INIT DATABASE --------------------
def init_db(app):
    with app.app_context():
        db.create_all()
        print("✅ Database initialized with all models!")
