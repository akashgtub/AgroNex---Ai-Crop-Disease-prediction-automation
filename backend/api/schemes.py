from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_schemes():
    return [
        {
            "id": 1,
            "name": "PM-KISAN",
            "who_can_apply": "Small and marginal farmers",
            "benefits": "₹6000 per year",
            "eligibility": "Landholding up to 2 hectares",
            "source": "https://pmkisan.gov.in/"
        }
    ]
