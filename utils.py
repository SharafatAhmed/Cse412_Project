import os
from werkzeug.utils import secure_filename
from PIL import Image
from config import Config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_photo(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create unique filename
        from datetime import datetime
        import uuid
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
        
        # Save file
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # Optimize image if needed
        optimize_image(filepath)
        
        return unique_filename
    return None

def optimize_image(filepath, max_size=(1200, 1200)):
    try:
        img = Image.open(filepath)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else img)
            img = background
        
        img.save(filepath, 'JPEG', quality=85)
    except Exception as e:
        print(f"Error optimizing image: {e}")

def create_notification(user_id, message):
    from models import Notification, db
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()