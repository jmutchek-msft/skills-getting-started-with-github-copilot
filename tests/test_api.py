"""
Tests for Mergington High School Activities API endpoints

This module contains comprehensive tests for all API endpoints including:
- GET /activities: Retrieve all activities
- POST /activities/{activity_name}/signup: Sign up for an activity
- DELETE /activities/{activity_name}/unregister: Unregister from an activity
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


class TestActivitiesAPI:
    """Test suite for the Activities API endpoints."""

    def test_get_activities(self, client):
        """Test retrieving all activities."""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that we get a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that each activity has required fields
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)

    def test_root_redirect(self, client):
        """Test that root path redirects to static index.html."""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"

    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity."""
        # Choose an activity that exists and has space
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_participants = len(initial_data[activity_name]["participants"])
        
        # Sign up for the activity
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the participant was added
        updated_response = client.get("/activities")
        updated_data = updated_response.json()
        updated_participants = updated_data[activity_name]["participants"]
        
        assert len(updated_participants) == initial_participants + 1
        assert email in updated_participants

    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist."""
        response = client.post("/activities/Nonexistent Activity/signup?email=test@mergington.edu")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity."""
        activity_name = "Programming Class"
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()

    def test_unregister_from_activity_success(self, client):
        """Test successful unregistration from an activity."""
        activity_name = "Gym Class"
        email = "unregister_test@mergington.edu"
        
        # First sign up for the activity
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Get participant count after signup
        after_signup = client.get("/activities")
        after_signup_data = after_signup.json()
        participants_after_signup = len(after_signup_data[activity_name]["participants"])
        
        # Now unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert unregister_response.status_code == 200
        data = unregister_response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the participant was removed
        after_unregister = client.get("/activities")
        after_unregister_data = after_unregister.json()
        participants_after_unregister = after_unregister_data[activity_name]["participants"]
        
        assert len(participants_after_unregister) == participants_after_signup - 1
        assert email not in participants_after_unregister

    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist."""
        response = client.delete("/activities/Nonexistent Activity/unregister?email=test@mergington.edu")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_unregister_non_registered_participant(self, client):
        """Test unregistration of a participant who isn't registered."""
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_activity_data_structure(self, client):
        """Test that activities have the correct data structure."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        
        # Test specific known activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Test Chess Club structure
        chess_club = data["Chess Club"]
        assert chess_club["description"] == "Learn strategies and compete in chess tournaments"
        assert chess_club["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert chess_club["max_participants"] == 12
        assert isinstance(chess_club["participants"], list)

    def test_email_parameter_required(self, client):
        """Test that email parameter is required for signup and unregister."""
        activity_name = "Chess Club"
        
        # Test signup without email
        signup_response = client.post(f"/activities/{activity_name}/signup")
        assert signup_response.status_code == 422  # Validation error
        
        # Test unregister without email
        unregister_response = client.delete(f"/activities/{activity_name}/unregister")
        assert unregister_response.status_code == 422  # Validation error

    def test_url_encoding_in_activity_names(self, client):
        """Test that activity names with spaces are properly URL encoded."""
        activity_name = "Chess Club"  # Has a space
        email = "urltest@mergington.edu"
        
        # Test with properly encoded URL
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Clean up
        client.delete(f"/activities/{activity_name}/unregister?email={email}")


class TestIntegrationScenarios:
    """Integration tests that test multiple operations together."""

    def test_full_lifecycle(self, client):
        """Test a complete signup and unregister lifecycle."""
        activity_name = "Science Club"
        email = "lifecycle@mergington.edu"
        
        # 1. Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # 2. Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # 3. Verify signup
        after_signup = client.get("/activities")
        after_signup_data = after_signup.json()
        assert len(after_signup_data[activity_name]["participants"]) == initial_count + 1
        assert email in after_signup_data[activity_name]["participants"]
        
        # 4. Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # 5. Verify unregistration
        after_unregister = client.get("/activities")
        after_unregister_data = after_unregister.json()
        assert len(after_unregister_data[activity_name]["participants"]) == initial_count
        assert email not in after_unregister_data[activity_name]["participants"]

    def test_multiple_participants_same_activity(self, client):
        """Test multiple participants signing up for the same activity."""
        activity_name = "Art Workshop"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Sign up multiple students
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are signed up
        after_signups = client.get("/activities")
        after_signups_data = after_signups.json()
        participants = after_signups_data[activity_name]["participants"]
        
        assert len(participants) == initial_count + len(emails)
        for email in emails:
            assert email in participants
        
        # Clean up - unregister all test participants
        for email in emails:
            client.delete(f"/activities/{activity_name}/unregister?email={email}")