from app.main import create_app


def test_hr_read_endpoints_are_registered_without_mutation_endpoints() -> None:
    paths = {route.path: tuple(route.methods or ()) for route in create_app().routes}
    expected = {
        "/api/v1/leave-balances/me", "/api/v1/leave-requests/me",
        "/api/v1/leave-requests/{request_id}", "/api/v1/onboarding-requests/{request_id}",
        "/api/v1/job-descriptions/{job_description_id}",
    }
    assert expected.issubset(paths)
    assert all("GET" in paths[path] for path in expected)
