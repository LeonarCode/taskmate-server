def detect_image_type(content: bytes) -> str | None:
    """Ang uri ng larawan ayon sa unang bytes ng mismong file ("jpeg", "png", "gif" o "webp"), o None kung hindi ito isa sa apat.

    Hindi pinagkakatiwalaan ang pangalan o content type na sinasabi ng client. Walang svg: puwedeng may script kapag binuksan sa browser."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None
