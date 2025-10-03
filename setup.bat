@echo off
echo 🚀 Setting up Student Scholarship Portal...

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Database setup
echo 🗄️ Setting up database...
echo Please ensure MySQL is running and create the database:
echo CREATE DATABASE scholarship_portal_db;
echo CREATE USER 'portal_user'@'localhost' IDENTIFIED BY 'your_password';
echo GRANT ALL PRIVILEGES ON scholarship_portal_db.* TO 'portal_user'@'localhost';
echo FLUSH PRIVILEGES;
echo.
pause

REM Run migrations
echo 🔄 Running migrations...
python manage.py makemigrations
python manage.py migrate

REM Create superuser
echo 👤 Creating superuser...
python manage.py createsuperuser

REM Collect static files
echo 📂 Collecting static files...
python manage.py collectstatic --noinput

REM Create media directories
echo 📁 Creating media directories...
if not exist "media\profile_pictures" mkdir media\profile_pictures
if not exist "media\student_documents" mkdir media\student_documents
if not exist "media\institute_documents" mkdir media\institute_documents
if not exist "media\grievance_documents" mkdir media\grievance_documents
if not exist "media\financial_reports" mkdir media\financial_reports

REM Create logs directory
if not exist "logs" mkdir logs

echo ✅ Setup complete!
echo 🌐 Run 'python manage.py runserver' to start the development server
echo 📊 Access admin panel at: http://localhost:8000/admin/
echo 📖 API documentation will be available at: http://localhost:8000/api/docs/
pause
