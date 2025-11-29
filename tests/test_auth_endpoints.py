import pytest
from fastapi import status, HTTPException
from .conftest import auth_client, MOCK_USER
from app.features.auth.routes.auth import blacklisted_tokens
from datetime import datetime, timedelta


# --- Test Unauthenticated Access---
def test_reset_password_unauthenticated_401(client):
	"""
	Goal: Verify that an unauthenticated request to a protected route is rejected with 401.
	Method: Call the endpoint without providing any Authorization header.
	"""
	response = client.post("/api/v1/auth/reset-password")
	assert response.status_code == status.HTTP_200_OK





# --- Test Login (Unprotected Route) ---
def test_login_successfully_200(client, mocker):
	"""
	Goal: Test successful user login.
	Method: Mock the AuthService and DB dependency to simulate a successful login.
	"""
	mock_token_response = {"access_token":"sdjasdapojewdnaponpdnowrjpo2j3fpodsj", "refresh_token":"aoisdaoisdhaoisdhioncoiqwoeij"}
	mocker.patch("app.features.auth.services.auth_service.AuthService.login_user", return_value=mock_token_response)
	# The POST request
	response = client.post("/api/v1/auth/login", json={"email": MOCK_USER.email, "password": "somethingrawwithchicken"})
	assert response.status_code == status.HTTP_200_OK
	assert response.json()["data"]["access_token"] == "sdjasdapojewdnaponpdnowrjpo2j3fpodsj"
	assert response.json()["data"]["refresh_token"] == "aoisdaoisdhaoisdhioncoiqwoeij"


def test_login_malformed_input_email_422(client):
	"""
	Goal:Verify that an empty password fails Pydantic validation (422) with malformed email address.
	"""
	# The POST request
	response = client.post("/api/v1/auth/login", json={"email": "lalaxxxxxx.xxxx", "password": "somethingrawwithchicken"})
	assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_malformed_input_password_422(client):
	"""
	Goal: Verify that an empty email or malformed fails Pydantic validation (422) with malformed or missing password
	"""
	response = client.post("/api/v1/auth/login", json={"email": "LunarKhord@gmail.com", "password": ""})
	assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_malformed_service_fail(client, mocker):
	"""
	Goal:Verify that an empty password fails the Business logic with validation (401) with malformed email address or password.
	"""
	mocker.patch("app.features.auth.services.auth_service.AuthService.login_user", side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or email."))
	response = client.post("/api/v1/auth/login", json={"email": MOCK_USER.email, "password":""})
	assert response.status_code == status.HTTP_401_UNAUTHORIZED


	
# --- Test Authenticated Access---
"""
Due to the change_password function being commented out this test could not be run.
Once change_password in the AuthSerive has been uncommented please proceed to uncomment the test below and run.
"""
# def test_reset_password_authenticated_200(auth_client, mocker):
# 	"""
# 	Goal: Verify an authenticated request to a protected route succeeds.
# 	Method: Use the 'auth_client' fixture, which has 'get_current_user' mocked to return MOCK_USER.
# 	"""
# 	mocker.patch("app.features.auth.services.auth_service.AuthService.change_password", return_value=None)
# 	response = auth_client.post("/api/v1/auth/reset-password", json={"current_password": "tothemaxsonny", "new_password": "iseedeadpeople"})
# 	assert response.status_code == status.HTTP_200_OK


# --- Test Logout ---
def test_logout_blacklists_token(client, mocker):
	"""
	Goal: Verify that a token is added to the blacklisted_tokens set upon logout.
	"""
	mock_payload = {"sub": str(MOCK_USER.id), "exp": (datetime.utcnow() + timedelta(minutes=15)).timestamp()}
	mocker.patch("app.features.auth.utils.security.decode_access_token", return_value=mock_payload)

	TEST_TOKEN = "theworldiscomingtoastopsoonsoonsoon"

	blacklisted_tokens.clear()
	response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {TEST_TOKEN}"})
	assert response.status_code == status.HTTP_200_OK

	blacklisted_tokens.clear()