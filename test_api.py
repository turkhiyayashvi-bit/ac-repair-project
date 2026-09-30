import requests

# 1. Test GET All Bookings
url = "http://127.0.0.1:5000/api/admin/bookings"
response = requests.get(url)

print("GET Bookings Status Code:", response.status_code)
print("GET Bookings Response:", response.json())

# 2. Test PATCH Update Booking Status (તમારે જે બુકિંગ આઈડી બદલવું હોય તે અહીં નાખવું)
# booking_id = 1
# patch_url = f"http://127.0.0.1:5000/api/admin/bookings/{booking_id}/status"
# payload = {"status": "Confirmed"}
# response = requests.patch(patch_url, json=payload)
# print("PATCH Booking Response:", response.json())