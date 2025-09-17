from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from uuid import uuid4
from supabase import create_client, Client
import os
from config import Config
from datetime import datetime, timedelta, timezone

supabase_url = Config.SUPABASE_URL
supabase_key = Config.SUPABASE_KEY

supabase: Client = create_client(supabase_url, supabase_key)


def save_sb_session(auth_session):
    if not auth_session:
        return
    session['sb_access'] = auth_session.access_token
    session['sb_refresh'] = auth_session.refresh_token
    # Supabase returns expires_in (seconds)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=auth_session.expires_in)
    session['sb_expires_at'] = expires_at.timestamp()


def ensure_sb_session():
    # If no tokens, not logged in
    if not session.get('sb_access') or not session.get('sb_refresh'):
        return False
    # Refresh if expiring in < 2 minutes
    now_ts = datetime.now(timezone.utc).timestamp()
    if session.get('sb_expires_at', 0) - now_ts < 120:
        try:
            # Set current session on client and refresh
            supabase.auth.set_session(session['sb_access'], session['sb_refresh'])
            refreshed = supabase.auth.refresh_session()
            save_sb_session(refreshed.session)
        except Exception as e:
            print(f"Supabase refresh failed: {e}")
            return False
    return True


def set_client_session_from_flask():
    """Ensure the supabase client carries the user's auth for Storage/DB policies."""
    access = session.get('sb_access')
    refresh = session.get('sb_refresh')
    if access and refresh:
        try:
            supabase.auth.set_session(access, refresh)
        except Exception as e:
            print(f"set_session failed: {e}")


def fetch_posts():
    try:
        # Fetch tweets (treating them as resources)
        tweets_response = supabase.table('tweets').select("*").order('created_at', desc=True).execute()
        tweets = tweets_response.data

        importance_order = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }

        formatted_posts = []
        for tweet in tweets:
            # Get upvotes count (using resource_id to match your schema)
            try:
                upvotes_response = supabase.table('likes').select('id', count='exact').eq('resource_id', tweet['id']).execute()
                upvotes_count = upvotes_response.count if hasattr(upvotes_response, 'count') else len(upvotes_response.data)
            except Exception as e:
                print(f"Error fetching upvotes: {e}")
                upvotes_count = 0

            # Get comments count from tweet_replies
            try:
                comments_response = supabase.table('tweet_replies').select('id', count='exact').eq('resource_id', tweet['id']).execute()
                comments_count = comments_response.count if hasattr(comments_response, 'count') else len(comments_response.data)
            except Exception as e:
                print(f"Error fetching comments: {e}")
                comments_count = 0

            # Get latest status update (using resource_id to match your schema)
            try:
                status_response = supabase.table('tweet_replies').select('*').eq('resource_id', tweet['id']).order('created_at', desc=True).limit(1).execute()
                latest_status = status_response.data[0] if status_response.data else None
            except Exception as e:
                print(f"Error fetching status: {e}")
                latest_status = None

            # Resolve author name from user_profiles when possible
            author_name = 'Campus Member'
            try:
                author_id = tweet.get('author_id')
                if author_id:
                    author_resp = supabase.table('user_profiles').select('full_name').eq('user_id', author_id).limit(1).execute()
                    if author_resp.data:
                        author_name = author_resp.data[0].get('full_name') or 'Campus Member'
            except Exception as e:
                print(f"Error fetching author name: {e}")

            importance_value = ''
            importance_rank = 0
            if latest_status and latest_status.get('chips_available'):
                importance_value = latest_status['chips_available']
                importance_rank = importance_order.get(str(importance_value).lower(), 0)

            formatted_post = {
                'id': tweet['id'],
                'name': tweet.get('name', tweet.get('content', 'Untitled Resource')),
                'content': tweet.get('content', ''),
                'image_url': tweet.get('image_url'),
                'upvotes_count': upvotes_count,
                'comments_count': comments_count,
                'created_at': tweet['created_at'],
                'latest_status': latest_status,
                'author_name': author_name,
                'can_edit': session.get('user_id') == (tweet.get('author_id') or ''),
                'can_delete': session.get('user_id') == (tweet.get('author_id') or '') or session.get('user_role') == 'faculty',
                'importance': importance_value,
                'importance_rank': importance_rank
            }
            formatted_posts.append(formatted_post)
        
        # Sort: importance desc, upvotes desc, created_at desc
        formatted_posts.sort(key=lambda p: (p.get('importance_rank', 0), p.get('upvotes_count', 0), str(p.get('created_at') or '')), reverse=True)

        return formatted_posts
        
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']
app.permanent_session_lifetime = timedelta(days=7)

# Custom decorator to check if user is logged in
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        # keep Supabase session alive
        if not ensure_sb_session():
            # if refresh failed, force re-login
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Custom decorator to check if user is admin
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('index'))
        decorated_function.__name__ = f.__name__
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    posts = fetch_posts()
    return render_template('index.html', posts=posts)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']  # This is actually email
        password = request.form['password']
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if response.user:
                # Persist Supabase tokens
                save_sb_session(response.session)
                
                # Get user profile from our custom table
                profile_response = supabase.table('user_profiles').select('*').eq('user_id', response.user.id).execute()
                
                if profile_response.data:
                    profile = profile_response.data[0]
                    session['username'] = email
                    session['user_id'] = response.user.id
                    session['user_role'] = profile['role']
                    session['full_name'] = profile['full_name']
                    session['student_id'] = profile.get('student_id') or ''
                    session['faculty_id'] = profile.get('faculty_id') or ''
                    session['department'] = profile.get('department') or ''
                    session['is_admin'] = (profile['role'] == 'admin')
                else:
                    # Fallback for users without profiles
                    session['username'] = email
                    session['user_id'] = response.user.id
                    session['user_role'] = 'student'  # Default role
                    session['is_admin'] = False
                
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            print(f"Login error: {e}")
            return render_template('login.html', error=f"Login failed: {str(e)}")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        student_id = request.form.get('student_id', '')
        faculty_id = request.form.get('faculty_id', '')
        department = request.form.get('department', '')
        
        try:
            # Create user in Supabase Auth
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                user_id = response.user.id
                
                # Create user profile in our custom table
                profile_data = {
                    'user_id': user_id,
                    'email': email,
                    'role': role,
                    'full_name': full_name
                }
                
                # Add role-specific fields
                if role == 'student' and student_id:
                    profile_data['student_id'] = student_id
                elif role == 'faculty':
                    if faculty_id:
                        profile_data['faculty_id'] = faculty_id
                    if department:
                        profile_data['department'] = department
                
                # Insert user profile
                profile_response = supabase.table('user_profiles').insert(profile_data).execute()
                
                if profile_response.data:
                    session['username'] = email
                    session['user_id'] = user_id
                    session['user_role'] = role
                    session['full_name'] = full_name
                    session['is_admin'] = (role == 'admin')
                    
                    return redirect(url_for('profile'))
                else:
                    return render_template('register.html', error="Failed to create user profile")
            else:
                return render_template('register.html', error="Registration failed")
                
        except Exception as e:
            print(f"Registration error: {e}")
            return render_template('register.html', error=f"Registration failed: {str(e)}")
    
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    # Fetch posts created by this user
    my_posts = []
    try:
        user_id = session.get('user_id')
        if user_id:
            resp = supabase.table('tweets').select('*').eq('author_id', user_id).order('created_at', desc=True).execute()
            my_posts = resp.data or []
    except Exception as e:
        print(f"Error fetching my posts: {e}")
        my_posts = []
    return render_template('profile.html', username=session['username'], my_posts=my_posts)

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/logout')
@login_required
def logout():
    try:
        supabase.auth.set_session(session.get('sb_access'), session.get('sb_refresh'))
        supabase.auth.sign_out()
    except Exception as e:
        print(f"Supabase sign_out error: {e}")
    session.clear()
    return redirect(url_for('index'))

# Upvote/Unupvote resource (using existing likes table)
@app.route('/upvote_resource', methods=['POST'])
@login_required
def upvote_resource():
    resource_id = request.json.get('resource_id')
    user_id = session['user_id']
    
    try:
        # Check if user already upvoted this resource
        existing_upvote = supabase.table('likes').select('id').eq('resource_id', resource_id).eq('user_id', user_id).execute()
        
        if existing_upvote.data:
            # Remove upvote
            supabase.table('likes').delete().eq('resource_id', resource_id).eq('user_id', user_id).execute()
            action = 'unupvoted'
        else:
            # Add upvote
            upvote_data = {
                'id': str(uuid4()),
                'resource_id': resource_id,
                'user_id': user_id,
                'like_type': 'upvote'
            }
            supabase.table('likes').insert(upvote_data).execute()
            action = 'upvoted'
        
        # Get updated upvotes count
        upvotes_response = supabase.table('likes').select('id', count='exact').eq('resource_id', resource_id).execute()
        upvotes_count = upvotes_response.count if hasattr(upvotes_response, 'count') else len(upvotes_response.data)
        
        return jsonify({
            'success': True,
            'action': action,
            'upvotes_count': upvotes_count
        })
        
    except Exception as e:
        print(f"Upvote error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Create new resource (only faculty can create) - using tweets table
@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        # Support both old and new field names
        name = request.form.get('name') or request.form.get('title', '')
        content = request.form.get('content') or request.form.get('description', '')
        image_url = request.form.get('image_url', '')
        image_file = request.files.get('image_file')
        crowd_level = request.form.get('crowd', '')  # legacy field name
        importance = request.form.get('importance', '')  # new field name
        chips_available = importance or request.form.get('chips', '')  # map to existing column
        queue_length = request.form.get('queue', '')  # legacy field name
        
        if not name or not name.strip():
            return render_template('create_post.html', error="Resource name/title cannot be empty")
        
        # If an image file is provided, upload to Supabase Storage and get public URL
        if image_file and image_file.filename:
            try:
                # ensure client has user session (for RLS/policies on storage)
                set_client_session_from_flask()
                ext = os.path.splitext(image_file.filename)[1].lower() or '.jpg'
                file_key = f"posts/{uuid4()}{ext}"
                image_bytes = image_file.read()
                # Upload file bytes with correct contentType and upsert
                upload_resp = supabase.storage.from_('images').upload(
                    file_key,
                    image_bytes,
                    {"contentType": image_file.mimetype or "image/jpeg", "upsert": True}
                )
                print("upload_resp:", upload_resp)
                # If SDK returns dict with error, don't set URL
                if isinstance(upload_resp, dict) and upload_resp.get('error'):
                    print("Storage upload error:", upload_resp['error'])
                else:
                    public = supabase.storage.from_('images').get_public_url(file_key)
                    print("public_url_resp:", public)
                    if isinstance(public, dict):
                        image_url = (public.get('data') or {}).get('publicUrl') or image_url
                    elif isinstance(public, str):
                        image_url = public or image_url
            except Exception as e:
                print(f"Image upload failed: {e}")
                # proceed without image
        
        try:
            new_id = str(uuid4())
            resource_data = {
                'id': new_id,
                'name': name.strip(),
                'content': content.strip() if content else '',
                'image_url': image_url.strip() if image_url else '',
                'author_id': session.get('user_id')
            }
            supabase.table('tweets').insert(resource_data).execute()

            # Create an initial status update if provided
            if crowd_level or chips_available or queue_length:
                status_data = {
                    'id': str(uuid4()),
                    'resource_id': new_id,
                    'status_message': content.strip() if content else '',
                    'crowd_level': crowd_level,
                    'chips_available': chips_available,
                    'queue_length': queue_length,
                    'user_id': session.get('user_id')
                }
                try:
                    supabase.table('tweet_replies').insert(status_data).execute()
                except Exception as e:
                    print(f"Warning: initial status insert failed: {e}")

            return redirect(url_for('index'))
        except Exception as e:
            print(f"Resource creation error: {e}")
            return render_template('create_post.html', error="Failed to create resource")
    
    return render_template('create_post.html')

# Update resource status (only faculty can update) - using tweet_replies table
@app.route('/update_status/<resource_id>', methods=['POST'])
@login_required
def update_status(resource_id):
    status_message = request.form.get('status_message', '')
    crowd_level = request.form.get('crowd_level', '')
    importance = request.form.get('importance', '')
    chips_available = importance or request.form.get('chips_available', '')
    queue_length = request.form.get('queue_length', '')
    
    try:
        status_data = {
            'id': str(uuid4()),
            'resource_id': resource_id,
            'status_message': status_message,
            'crowd_level': crowd_level,
            'chips_available': chips_available,
            'queue_length': queue_length,
            'user_id': session['user_id']
        }
        supabase.table('tweet_replies').insert(status_data).execute()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Status update error: {e}")
        return redirect(url_for('index'))

# Delete resource (owner or faculty can delete) - using tweets table
@app.route('/delete_resource/<resource_id>', methods=['POST'])
@login_required
def delete_resource(resource_id):
    try:
        # Fetch the tweet to verify ownership
        tweet_resp = supabase.table('tweets').select('author_id').eq('id', resource_id).limit(1).execute()
        if not tweet_resp.data:
            return jsonify({'success': False, 'error': 'Not found'})
        author_id = tweet_resp.data[0].get('author_id')
        is_owner = session.get('user_id') == author_id
        is_faculty = session.get('user_role') == 'faculty'
        if not (is_owner or is_faculty):
            return jsonify({'success': False, 'error': 'Not authorized'})

        # Delete related data first
        supabase.table('likes').delete().eq('resource_id', resource_id).execute()
        supabase.table('replies').delete().eq('resource_id', resource_id).execute()
        supabase.table('tweet_replies').delete().eq('resource_id', resource_id).execute()
        
        # Delete the resource (tweet)
        supabase.table('tweets').delete().eq('id', resource_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Edit resource (owner or faculty can edit) - using tweets table
@app.route('/edit_post/<resource_id>', methods=['GET', 'POST'])
@login_required
def edit_post(resource_id):
    # Ownership check
    try:
        tw_resp = supabase.table('tweets').select('author_id').eq('id', resource_id).limit(1).execute()
        if not tw_resp.data:
            return redirect(url_for('index'))
        author_id = tw_resp.data[0].get('author_id')
        is_owner = session.get('user_id') == author_id
        is_faculty = session.get('user_role') == 'faculty'
        if not (is_owner or is_faculty):
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Ownership check failed: {e}")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        content = request.form.get('content', '')
        image_url = request.form.get('image_url', '')
        
        if not name.strip():
            return render_template('edit_post.html', post={'id': resource_id, 'name': name, 'content': content, 'image_url': image_url}, error="Resource name cannot be empty")
        
        try:
            update_data = {
                'name': name,
                'content': content,
                'image_url': image_url
            }
            supabase.table('tweets').update(update_data).eq('id', resource_id).execute()
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Resource update error: {e}")
            return render_template('edit_post.html', post={'id': resource_id, 'name': name, 'content': content, 'image_url': image_url}, error="Failed to update resource")
    
    # GET request - fetch the resource
    try:
        resource_response = supabase.table('tweets').select('*').eq('id', resource_id).execute()
        if resource_response.data:
            post = resource_response.data[0]
            return render_template('edit_post.html', post=post)
        else:
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Error fetching resource: {e}")
        return redirect(url_for('index'))

@app.route('/comments/<resource_id>', methods=['GET', 'POST'])
@login_required
def comments(resource_id):
    if request.method == 'POST':
        comment_text = request.form.get('comment', '').strip()
        if comment_text:
            try:
                supabase.table('tweet_replies').insert({
                    'id': str(uuid4()),
                    'resource_id': resource_id,
                    'status_message': comment_text,
                    'user_id': session.get('user_id')
                }).execute()
            except Exception as e:
                print(f"Insert comment failed: {e}")
        return redirect(url_for('comments', resource_id=resource_id))

    # GET -> list existing comments
    comments_list = []
    try:
        resp = supabase.table('tweet_replies').select('*').eq('resource_id', resource_id).order('created_at', desc=True).execute()
        comments_list = resp.data or []
    except Exception as e:
        print(f"Fetch comments failed: {e}")
    # Also fetch the post header
    post = None
    try:
        pr = supabase.table('tweets').select('*').eq('id', resource_id).limit(1).execute()
        if pr.data:
            post = pr.data[0]
    except Exception as e:
        print(f"Fetch post for comments failed: {e}")
    return render_template('comments.html', post=post, comments=comments_list)

if __name__ == '__main__':
    app.run(debug=True)
