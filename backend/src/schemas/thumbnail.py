from pydantic import BaseModel, Field


class ThumbnailSpec(BaseModel):
    """
    Specification for a thumbnail to be generated.
    """

    name: str = Field(
        ...,
        description="Name/identifier of the thumbnail tier, e.g. 'small', 'medium', 'large'",
    )
    width: int = Field(..., gt=0, description="Target width in pixels")
    height: int = Field(..., gt=0, description="Target height in pixels")
    shape: str = Field(
        default="fit",
        description="Transformation mode: 'fit' (aspect ratio preserved), 'crop'/'square' (center cropped), or 'fill'/'exact' (stretched)",
    )
