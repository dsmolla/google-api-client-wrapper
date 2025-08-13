
MAX_RESULTS_LIMIT = 1000
DEFAULT_MAX_RESULTS = 30
MAX_FILE_SIZE = 5368709120  # 5GB Drive API limit for resumable uploads
DEFAULT_CHUNK_SIZE = 1048576  # 1MB default chunk size for uploads

# Special folder IDs
SHARED_DRIVE_ROOT = "root"
TRASH_FOLDER = "trash"
SHARED_WITH_ME_FOLDER = "sharedWithMe"

# Common MIME types
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DOCS_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_SHEETS_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"

MICROSOFT_WORD_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MICROSOFT_EXCEL_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MICROSOFT_POWERPOINT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

# File field selections for API calls
DEFAULT_FILE_FIELDS = "id,name,size,mimeType,createdTime,modifiedTime,parents,webViewLink,webContentLink,owners,permissions"
MINIMAL_FILE_FIELDS = "id,name,mimeType"
FULL_FILE_FIELDS = "*"

# Permission roles
PERMISSION_ROLE_READER = "reader"
PERMISSION_ROLE_WRITER = "writer"
PERMISSION_ROLE_COMMENTER = "commenter"
PERMISSION_ROLE_OWNER = "owner"

# Permission types
PERMISSION_TYPE_USER = "user"
PERMISSION_TYPE_GROUP = "group"
PERMISSION_TYPE_DOMAIN = "domain"
PERMISSION_TYPE_ANYONE = "anyone"