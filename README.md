AgriFarma - Minimal Flask starter project (skeleton)
--------------------------------------------------
How to run (Linux / Windows PowerShell):
1. Create virtual environment (recommended):
   python -m venv venv
   source venv/bin/activate     # (Linux/macOS)
   venv\Scripts\activate      # (Windows PowerShell)
2. Install requirements:
   pip install -r requirements.txt
3. Initialize database (first run):
   flask --app app db-init
4. Run the app:
   flask --app app run --debug
The app will be available at http://127.0.0.1:5000
This starter contains basic authentication, forum, blog, product models and a global search.


# 🌾 AgriFarma — Smart Agriculture & Farmer Support Platform

AgriFarma is a **Flask-based full-stack web application** designed to help farmers connect with experts, share knowledge, buy/sell products, and discuss farming-related issues in an online community.

It serves as a **one-stop digital platform for farmers**, experts, and administrators.

---

## 🚀 Features

### 👨‍🌾 For Farmers
- Create and manage blogs about farming tips.
- Post questions in the discussion forum.
- Buy/sell agricultural products.
- Request consultations from agriculture experts.
- View expert replies directly in the farmer dashboard.

### 🧑‍💼 For Experts
- Manage consultation requests from farmers.
- Reply directly to farmer queries.
- Access expert dashboard showing all assigned consultations.
- Engage in forum discussions.

### 🛠️ For Admins
- Full control over users, blogs, products, and forum content.
- Promote or demote users between `farmer` and `expert` roles.
- Delete inappropriate content (blogs, products, replies, or forum posts).
- Manage system and user permissions.

---

## 🏗️ Project Structure

AgriFarma/
│
├── app.py # Main Flask application
├── models.py # Database models (User, Blog, Product, Forum, Consultation, etc.)
├── requirements.txt # Required Python packages
│
├── static/ # Static assets
│ ├── css/ # Custom CSS files
│ ├── js/ # JavaScript scripts
│ └── uploads/ # Uploaded images (blogs/products)
│
├── templates/ # HTML Templates
│ ├── base.html # Base layout for all pages
│ ├── index.html # Home page
│ ├── login.html / register.html
│ ├── dashboard.html # Farmer dashboard
│ ├── expert_dashboard.html # Expert dashboard
│ ├── admin_dashboard.html # Admin dashboard
│ ├── blog.html / new_blog.html / view_blog.html
│ ├── products.html / view_product.html / new_product.html
│ ├── forum.html / view_thread.html / new_thread.html
│ ├── consult.html / consultation_detail.html / consultation_request.html
│ └── search_results.html
│
├── migrations/ # Flask-Migrate files (auto-generated)
└── instance/
└── agrifarma.db # SQLite database (auto-created)


---

