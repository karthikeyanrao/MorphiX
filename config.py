import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '66ec717edda40621a65ee68db64710664674031ef0179fde6a70929d80431e07'
    SUPABASE_URL = os.environ.get('SUPABASE_URL') or 'https://vfqekzvhzprbnqgfijep.supabase.co'
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZmcWVrenZoenByYm5xZ2ZpamVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgwNzk4NjksImV4cCI6MjA3MzY1NTg2OX0.PjCxNrRwFta0zQDlPnQ1qNWWBg4lSkzKun-j7P2kvgA'

    ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'admin@example.com').split(',')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

