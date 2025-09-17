# Morphx2.0
A repo for Morphx Challenge, Live Campus Update

---
## Campus Live Dashboard

A modern online voting and live status dashboard built with **Flask**, **HTML/CSS**, **JavaScript**, and **Supabase** (Postgres) for the backend database. 🚀

---
### **Prerequisites**

- Python 3.11.x or higher installed

---

## **Project Folder Structure**
```
campus-live-dashboard/
│
├── static/
│   ├── css/
│   │   └── style.css        # Main stylesheet
│   ├── js/
│   │   └── script.js        # Client-side JavaScript
│
├── templates/
│   ├── base.html            # Main base template (nav, structure)
│   ├── index.html           # Homepage (post feed, update forms)
│   ├── about.html           # About section
│   ├── login.html           # Login form
│   ├── register.html        # Signup page
│   ├── profile.html         # User profile/info
│   ├── admin.html           # Admin dashboard (future extension)
│   └── create_post.html     # Posting new resources
│
├── app.py                   # Main Flask application (routes, logic)
├── config.py                # Configuration for secrets and Supabase keys
├── requirements.txt         # Python package requirements
```

---

## **Configuring Supabase**

To use your own Supabase project, edit **config.py** with your project **SUPABASE_URL** and **SUPABASE_KEY**:

```python
# config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'
    SUPABASE_URL = os.environ.get('SUPABASE_URL') or '<your_supabase_url>'
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY') or '<your_supabase_key>'
```

---

## **Supabase Database Structure (Collections)**

### `resources`  
Stores main posts/resources (e.g., canteens, events, facilities)
- `id` (UUID): Primary key
- `name` (String): Name/title
- `image_url` (String): Image for the resource
- `created_at` (Timestamp)

### `status_updates`  
Tracks real-time/dynamic updates on resources
- `id` (UUID): Primary key
- `resource_id` (UUID): Foreign key to resources
- `status_message` (String): Free-text update
- `crowd_level` (Text): Status (e.g. Low/Medium/High)
- `chips_available` (Text)
- `queue_length` (Text)
- `user_id` (UUID): (user posting the status)
- `created_at` (Timestamp)

### `upvotes`  
Handles resource upvotes & prevents duplicates per user
- `id` (UUID): Primary key
- `resource_id` (UUID): Foreign key to resources
- `user_id` (UUID): Who upvoted
- `created_at` (Timestamp)

### `comments`  
(If implemented) User comments for resources (linked to both)
- `id` (UUID): Primary key
- `resource_id` (UUID): Foreign key to resources
- `user_id` (UUID): Who commented
- `comment_text` (Text)
- `created_at` (Timestamp)

**Schema SQL:** [Link](https://sntry.cc/morphx_schema)

---

## **Running the Application Locally**

### 1. **Clone and move to working directory**
```bash
cd campus-live-dashboard
```
### 2. **Install virtualenv if needed**
```bash
pip install virtualenv
```
### 3. **Create & activate your virtual environment**
```bash
virtualenv env
# For Windows
.\env\Scripts\activate
# For Mac/Linux
source env/bin/activate
```
### 4. **Install all dependencies**
```bash
pip install -r requirements.txt
```
### 5. **Start Flask**
```bash
python app.py
```

---

## **Included Functionality**

- **User Auth:** Login & Register (via Supabase Auth)
- **Resource Feed:** List all available resources, up-to-date status
- **Voting:** Logged-in users can upvote a resource (1 vote/user/resource)
- **Real-time Updates:** Add or update crowd, chips, queue, and description for every resource
- **Image Uploads:** Images are uploaded to Supabase Storage (for posts)
- **Admin UI:** Basic admin page scaffolding

---

## **Extra Notes**

- You can always link your app to your own Supabase project by updating the config.
- This project uses secure password storage via Supabase—not in plaintext!
- All upvote logic prevents duplicate votes per user/resource.
- The frontend uses Jinja templating for rendering and dynamic display.
- All user sessions, authentication, and upvotes are securely managed.

---
**Challenge Guideline:** [Link](https://sntry.cc/morphx_chall)

---
Looking for more info?  
- **Supabase Docs:** [https://supabase.com/docs](https://supabase.com/docs)
- **Flask Docs:** [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

---
Happy hacking! 😄💡

---
