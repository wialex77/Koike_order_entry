"""
Step 1: File Upload Handler
Handles uploading and processing of PDF, Word, and other document files.
"""

import os
import time
import tempfile
from typing import Optional, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

class FileUploadHandler:
    """Handles file uploads and validation for purchase order documents."""
    
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'
    }
    
    def __init__(self, upload_folder: str = 'uploads', max_file_size: int = 16 * 1024 * 1024):
        """
        Initialize the file upload handler.
        
        Args:
            upload_folder: Directory to store uploaded files
            max_file_size: Maximum file size in bytes (default 16MB)
        """
        self.upload_folder = upload_folder
        self.max_file_size = max_file_size
        
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """Check if the file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def validate_file(self, file: FileStorage) -> Tuple[bool, str]:
        """
        Validate uploaded file.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file:
            return False, "No file provided"
        
        if file.filename == '':
            return False, "No file selected"
        
        if not self.allowed_file(file.filename):
            return False, f"File type not allowed. Supported types: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # Check file size (approximate)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size:
            return False, f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"
        
        return True, ""
    
    def save_file(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """
        Save uploaded file to disk.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (success, message, file_path)
        """
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            return False, error_msg, None
        
        try:
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Create unique filename to avoid conflicts
            name, ext = os.path.splitext(filename)
            timestamp = str(int(time.time()))
            unique_filename = f"{name}_{timestamp}{ext}"
            
            file_path = os.path.join(self.upload_folder, unique_filename)
            file.save(file_path)
            
            return True, f"File uploaded successfully as {unique_filename}", file_path
            
        except Exception as e:
            return False, f"Error saving file: {str(e)}", None
    
    def create_temp_file(self, file: FileStorage) -> Tuple[bool, str, Optional[str]]:
        """
        Create a temporary file from uploaded file for processing.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (success, message, temp_file_path)
        """
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            return False, error_msg, None
        
        try:
            # Get file extension
            ext = os.path.splitext(file.filename)[1].lower()
            
            # Create temporary file with proper extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                file.seek(0)  # Reset file pointer
                temp_file.write(file.read())
                temp_path = temp_file.name
            
            return True, "Temporary file created", temp_path
            
        except Exception as e:
            return False, f"Error creating temporary file: {str(e)}", None
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        stat = os.stat(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        return {
            "filename": filename,
            "name": name,
            "extension": ext.lower(),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024*1024), 2),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "full_path": file_path
        }
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up/delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

# Example usage
if __name__ == "__main__":
    # Test the upload handler
    handler = FileUploadHandler()
    print("File Upload Handler initialized")
    print(f"Allowed extensions: {handler.ALLOWED_EXTENSIONS}")
    print(f"Upload folder: {handler.upload_folder}")
    print(f"Max file size: {handler.max_file_size / (1024*1024):.1f}MB")
