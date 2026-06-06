from __future__ import annotations


INDIA_LOCATIONS = [
    {"name": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    {"name": "Amritsar", "state": "Punjab", "latitude": 31.6340, "longitude": 74.8723},
    {"name": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"name": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    {"name": "Bhubaneswar", "state": "Odisha", "latitude": 20.2961, "longitude": 85.8245},
    {"name": "Chandigarh", "state": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794},
    {"name": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"name": "Coimbatore", "state": "Tamil Nadu", "latitude": 11.0168, "longitude": 76.9558},
    {"name": "Dehradun", "state": "Uttarakhand", "latitude": 30.3165, "longitude": 78.0322},
    {"name": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"name": "Gandhinagar", "state": "Gujarat", "latitude": 23.2156, "longitude": 72.6369},
    {"name": "Guwahati", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362},
    {"name": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"name": "Indore", "state": "Madhya Pradesh", "latitude": 22.7196, "longitude": 75.8577},
    {"name": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"name": "Jammu", "state": "Jammu and Kashmir", "latitude": 32.7266, "longitude": 74.8570},
    {"name": "Jodhpur", "state": "Rajasthan", "latitude": 26.2389, "longitude": 73.0243},
    {"name": "Kanpur", "state": "Uttar Pradesh", "latitude": 26.4499, "longitude": 80.3319},
    {"name": "Kochi", "state": "Kerala", "latitude": 9.9312, "longitude": 76.2673},
    {"name": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    {"name": "Kozhikode", "state": "Kerala", "latitude": 11.2588, "longitude": 75.7804},
    {"name": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    {"name": "Madurai", "state": "Tamil Nadu", "latitude": 9.9252, "longitude": 78.1198},
    {"name": "Mangaluru", "state": "Karnataka", "latitude": 12.9141, "longitude": 74.8560},
    {"name": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"name": "Mysuru", "state": "Karnataka", "latitude": 12.2958, "longitude": 76.6394},
    {"name": "Nagpur", "state": "Maharashtra", "latitude": 21.1458, "longitude": 79.0882},
    {"name": "Nashik", "state": "Maharashtra", "latitude": 19.9975, "longitude": 73.7898},
    {"name": "Noida", "state": "Uttar Pradesh", "latitude": 28.5355, "longitude": 77.3910},
    {"name": "Patna", "state": "Bihar", "latitude": 25.5941, "longitude": 85.1376},
    {"name": "Puducherry", "state": "Puducherry", "latitude": 11.9416, "longitude": 79.8083},
    {"name": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    {"name": "Raipur", "state": "Chhattisgarh", "latitude": 21.2514, "longitude": 81.6296},
    {"name": "Rajkot", "state": "Gujarat", "latitude": 22.3039, "longitude": 70.8022},
    {"name": "Ranchi", "state": "Jharkhand", "latitude": 23.3441, "longitude": 85.3096},
    {"name": "Shillong", "state": "Meghalaya", "latitude": 25.5788, "longitude": 91.8933},
    {"name": "Surat", "state": "Gujarat", "latitude": 21.1702, "longitude": 72.8311},
    {"name": "Thiruvananthapuram", "state": "Kerala", "latitude": 8.5241, "longitude": 76.9366},
    {"name": "Tiruchirappalli", "state": "Tamil Nadu", "latitude": 10.7905, "longitude": 78.7047},
    {"name": "Udaipur", "state": "Rajasthan", "latitude": 24.5854, "longitude": 73.7125},
    {"name": "Vadodara", "state": "Gujarat", "latitude": 22.3072, "longitude": 73.1812},
    {"name": "Varanasi", "state": "Uttar Pradesh", "latitude": 25.3176, "longitude": 82.9739},
    {"name": "Vijayawada", "state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480},
    {"name": "Visakhapatnam", "state": "Andhra Pradesh", "latitude": 17.6868, "longitude": 83.2185},
]


def list_india_locations() -> list[dict]:
    return sorted(INDIA_LOCATIONS, key=lambda item: (item["state"], item["name"]))


def find_india_location(query: str) -> dict | None:
    normalized = _normalize(query)
    for location in INDIA_LOCATIONS:
        if _normalize(location["name"]) == normalized:
            return location
        if _normalize(f"{location['name']}, {location['state']}") == normalized:
            return location
    return None


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())

