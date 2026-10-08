import base64
from fastapi import UploadFile, HTTPException
from imagekitio import ImageKit
from config import settings
import asyncio

imagekit = ImageKit(
    private_key=settings.IMAGEKIT_PRIVATE_KEY,
    public_key=settings.IMAGEKIT_PUBLIC_KEY,
    url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
)


async def upload_resume_to_imagekit(file: UploadFile) -> str:
    """
    Uploads a PDF or any file to ImageKit asynchronously and returns the public URL.
    """
    try:
        file_bytes = await file.read()
        file_base64 = base64.b64encode(file_bytes).decode('utf-8')

        def sync_upload():
            return imagekit.upload_file(
                file=file_base64,
                file_name=file.filename
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, sync_upload)

        # Return URL
        return result.url if hasattr(result, 'url') else result['url']

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
