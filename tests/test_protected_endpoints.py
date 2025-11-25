"""
This module or test file, serves the purpose of testing out the authentication endpoints
"""




# --- Test Unauthenticated Access---


# User Management Tests

def test_unauthenticated_access_is_rejected_get(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.get("/api/v1/users/me")
	assert response.status_code == 403


def test_unauthenticated_access_is_rejected_patch(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.patch("/api/v1/users/me")
	assert response.status_code == 403



def test_unauthenticated_access_is_rejected_post(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.post("/api/v1/users/me/profile-picture")
	assert response.status_code == 403


def test_unauthenticated_access_is_rejected_delete(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.delete("/api/v1/users/me/profile-picture")
	assert response.status_code == 403


# Email Support Tests



# Sites Tests
def test_unauthenticated_access_is_rejected_get(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.get("/api/v1/sites")
	assert response.status_code == 403

	response_ = client.get("/api/v1/sites/23")
	assert response_.status_code == 403



def test_unauthenticated_access_is_rejected_patch(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.patch("/api/v1/sites/12")
	assert response.status_code == 403



def test_unauthenticated_access_is_rejected_post(client):
	"""
    Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
    Method: Call the endpoint without providing any Authorization header.
    """
	response = client.post("/api/v1/sites")
	assert response.status_code == 403
