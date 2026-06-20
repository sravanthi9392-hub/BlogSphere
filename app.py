import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'blogsphere_ultra_secure_secret_key_1337')

PREDEFINED_CATEGORIES = [
    'Technology', 'Artificial Intelligence', 'Web Development', 
    'Education', 'Health', 'Career Guidance', 'Programming'
]

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    # Enable foreign keys for cascading deletes
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.context_processor
def inject_categories():
    return dict(categories=PREDEFINED_CATEGORIES)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
            
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Choose another one.', 'danger')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))

# --- Main Public Routes ---

@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    conn = get_db_connection()
    
    # Building dynamic search & filter queries
    query = '''
        SELECT posts.*, users.username as author 
        FROM posts 
        JOIN users ON posts.author_id = users.id 
        WHERE 1=1
    '''
    params = []
    
    if search_query:
        query += " AND (posts.title LIKE ? OR posts.content LIKE ? OR users.username LIKE ?)"
        like_str = f"%{search_query}%"
        params.extend([like_str, like_str, like_str])
        
    if category_filter and category_filter in PREDEFINED_CATEGORIES:
        query += " AND posts.category = ?"
        params.append(category_filter)
        
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_posts = conn.execute(count_query, params).fetchone()[0]
    
    # Append sorting and pagination limits
    query += " ORDER BY posts.created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    posts = conn.execute(query, params).fetchall()
    
    # Metrics Sidebars
    popular_posts = conn.execute('SELECT * FROM posts ORDER BY likes DESC LIMIT 3').fetchall()
    recent_posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC LIMIT 3').fetchall()
    
    conn.close()
    
    total_pages = (total_posts + per_page - 1) // per_page
    
    return render_template('index.html', 
                           posts=posts, 
                           popular_posts=popular_posts,
                           recent_posts=recent_posts,
                           page=page, 
                           total_pages=total_pages,
                           search_query=search_query,
                           category_filter=category_filter)

# --- Dashboard & Profiles ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user_id = session['user_id']
    
    post_count = conn.execute('SELECT COUNT(*) FROM posts WHERE author_id = ?', (user_id,)).fetchone()[0]
    comment_count = conn.execute('SELECT COUNT(*) FROM comments WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    my_posts = conn.execute('''
        SELECT * FROM posts 
        WHERE author_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    return render_template('dashboard.html', post_count=post_count, comment_count=comment_count, my_posts=my_posts)

@app.route('/profile/<username>')
def profile(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
        
    stats = conn.execute('''
        SELECT 
            (SELECT COUNT(*) FROM posts WHERE author_id = ?) as posts_count,
            (SELECT COUNT(*) FROM comments WHERE user_id = ?) as comments_count
    ''', (user['id'], user['id'])).fetchone()
    
    user_posts = conn.execute('SELECT * FROM posts WHERE author_id = ? ORDER BY created_at DESC', (user['id'],)).fetchall()
    conn.close()
    
    return render_template('profile.html', profile_user=user, stats=stats, user_posts=user_posts)

# --- Blog Engine CRUD Ops ---

@app.route('/post/new', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('Log in to draft posts.', 'warning')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title'].strip()
        category = request.form['category']
        content = request.form['content'].strip()
        
        if not title or not content or category not in PREDEFINED_CATEGORIES:
            flash('Invalid form payload submission.', 'danger')
            return redirect(url_for('create_post'))
            
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (title, category, content, author_id) VALUES (?, ?, ?, ?)',
                     (title, category, content, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Blog Post launched successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('create_post.html')

@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db_connection()
    post = conn.execute('''
        SELECT posts.*, users.username as author 
        FROM posts 
        JOIN users ON posts.author_id = users.id 
        WHERE posts.id = ?
    ''', (post_id,)).fetchone()
    
    if not post:
        conn.close()
        flash('Post not found.', 'danger')
        return redirect(url_for('index'))
        
    comments = conn.execute('''
        SELECT comments.*, users.username as commenter 
        FROM comments 
        JOIN users ON comments.user_id = users.id 
        WHERE post_id = ? 
        ORDER BY comments.created_at ASC
    ''', (post_id,)).fetchall()
    
    conn.close()
    return render_template('post.html', post=post, comments=comments)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        conn.close()
        flash('Post tracking profile absent.', 'danger')
        return redirect(url_for('index'))
        
    if post['author_id'] != session['user_id']:
        conn.close()
        flash('Action unauthorized.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form['title'].strip()
        category = request.form['category']
        content = request.form['content'].strip()
        
        conn.execute('''
            UPDATE posts SET title = ?, category = ?, content = ?, updated_at = ?
            WHERE id = ?
        ''', (title, category, content, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), post_id))
        conn.commit()
        conn.close()
        
        flash('Post modified and saved.', 'success')
        return redirect(url_for('view_post', post_id=post_id))
        
    conn.close()
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if post and post['author_id'] == session['user_id']:
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
        flash('Post deleted permanently.', 'info')
    else:
        flash('Unauthorized command deletion rejected.', 'danger')
        
    conn.close()
    return redirect(url_for('dashboard'))

# --- AJAX Async Like API Endpoint ---

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Login required to rate configurations'}), 401
        
    conn = get_db_connection()
    post = conn.execute('SELECT likes FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({'error': 'Post absolute reference absent'}), 404
        
    new_likes = post['likes'] + 1
    conn.execute('UPDATE posts SET likes = ? WHERE id = ?', (new_likes, post_id))
    conn.commit()
    conn.close()
    
    return jsonify({'likes': new_likes})

# --- Comment Engine Sub-routes ---

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Login required to leave remarks.', 'warning')
        return redirect(url_for('login'))
        
    comment_text = request.form['comment'].strip()
    if comment_text:
        conn = get_db_connection()
        conn.execute('INSERT INTO comments (post_id, user_id, comment) VALUES (?, ?, ?)',
                     (post_id, session['user_id'], comment_text))
        conn.commit()
        conn.close()
        flash('Comment shared.', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/comment/<int:comment_id>/edit', methods=['POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    new_text = request.form['comment'].strip()
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if comment and comment['user_id'] == session['user_id']:
        conn.execute('UPDATE comments SET comment = ? WHERE id = ?', (new_text, comment_id))
        conn.commit()
        flash('Comment updated.', 'success')
    
    conn.close()
    return redirect(url_for('view_post', post_id=comment['post_id']))

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if comment and comment['user_id'] == session['user_id']:
        conn.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
        flash('Comment removed completely.', 'info')
        
    conn.close()
    return redirect(url_for('view_post', post_id=comment['post_id']))

if __name__ == '__main__':
    app.run(debug=True)