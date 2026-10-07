import base64
import binascii
from io import BytesIO
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError


def normalize_image(value: str) -> str:
    """Decode and re-encode raster uploads, stripping metadata and bounding storage."""
    try:
        header, encoded = value.split(',', 1)
        if header not in ('data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64'):
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError()
        with Image.open(BytesIO(raw)) as image:
            if image.width * image.height > 16000000 or image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError()
            image.load()
            clean = ImageOps.exif_transpose(image).convert('RGB')
            clean.thumbnail((1600, 1600))
            output = BytesIO()
            clean.save(output, format='JPEG', quality=85)
        return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode('ascii')
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Choose a valid JPEG, PNG or WebP image (maximum 2 MB)')
