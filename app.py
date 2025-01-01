from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.model.filters import BaseFilter

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secure this in a config or environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
db = SQLAlchemy(app)
admin = Admin(app, name='Blog Admin', template_mode='bootstrap4')

# Models
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))
    author = db.Column(db.String(50), nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# Admin Panel   
class TagFilter(BaseFilter):
    def apply(self, query, value, alias=None):
        return query.filter(Post.tags.any(Tag.name.ilike(f"%{value}%")))

    def operation(self):
        return "contains"

class PostAdmin(ModelView):
    column_searchable_list = ['title', 'category']
    column_filters = ['category']

admin.add_view(PostAdmin(Post, db.session))

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Routes
@app.route('/')
def home():
    posts = Post.query.all()  # Fetch all posts from the database
    return render_template('index.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for('home'))
        flash("Invalid credentials!")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect(url_for('home'))

@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        tag_names = request.form['tags'].split(',')
        tags = []
        for name in tag_names:
            tag = Tag.query.filter_by(name=name.strip()).first()
            if not tag:
                tag = Tag(name=name.strip())
                db.session.add(tag)
            tags.append(tag)
        new_post = Post(title=title, content=content, category=category, tags=tags, author=current_user.username)
        db.session.add(new_post)
        db.session.commit()
        flash("Post added successfully!")
        return redirect(url_for('home'))
    return render_template('add_post.html')

@app.route('/category/<category>')
def view_category(category):
    posts = Post.query.filter_by(category=category).all()
    return render_template('index.html', posts=posts, filter=f"Category: {category}")
# Define the route for viewing a single post
@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)  # Fetch post by ID
    return render_template('post_detail.html', post=post)  # Replace 'post_detail.html' with your post detail template

@app.route('/tag/<tag>')
def view_tag(tag):
    posts = Post.query.filter(Post.tags.any(Tag.name == tag)).all()
    return render_template('index.html', posts=posts, filter=f"Tag: {tag}")

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    posts = Post.query.filter(
        (Post.title.ilike(f"%{query}%")) | 
        (Post.content.ilike(f"%{query}%"))
    ).all()
    return render_template('index.html', posts=posts, filter=f"Search: {query}")

# Database Initialization
with app.app_context():
    db.create_all()

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
