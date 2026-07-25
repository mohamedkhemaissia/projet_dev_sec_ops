from dataclasses import dataclass

import requests


@dataclass
class ServiceError(Exception):
    status_code: int
    message: str
    error: str = "service_error"

    def __str__(self):
        return self.message


class TrainingHubAPI:
    def __init__(
        self,
        user_service_url,
        course_service_url,
        certificate_service_url,
        timeout=5,
    ):
        self.base_urls = {
            "users": user_service_url.rstrip("/"),
            "courses": course_service_url.rstrip("/"),
            "certificates": certificate_service_url.rstrip("/"),
        }
        self.timeout = timeout

    def _request(self, service, method, path, token=None, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.request(
                method,
                f"{self.base_urls[service]}{path}",
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ServiceError(
                503,
                "Le service est momentanément indisponible. Réessayez dans un instant.",
                "service_unavailable",
            ) from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            raise ServiceError(
                response.status_code,
                payload.get("message", "Une erreur est survenue."),
                payload.get("error", "service_error"),
            )
        return response

    @staticmethod
    def _json(response):
        if not response.content:
            return None
        return response.json()

    def register(self, payload):
        return self._json(
            self._request("users", "POST", "/api/v1/users/register", json=payload)
        )

    def login(self, email, password):
        return self._json(
            self._request(
                "users",
                "POST",
                "/api/v1/users/login",
                json={"email": email, "password": password},
            )
        )

    def profile(self, token):
        return self._json(
            self._request("users", "GET", "/api/v1/users/me", token=token)
        )

    def update_profile(self, token, payload):
        return self._json(
            self._request(
                "users",
                "PUT",
                "/api/v1/users/me",
                token=token,
                json=payload,
            )
        )

    def users(self, token):
        return self._json(
            self._request("users", "GET", "/api/v1/users/", token=token)
        )

    def update_user(self, token, user_id, payload):
        return self._json(
            self._request(
                "users",
                "PUT",
                f"/api/v1/users/{user_id}",
                token=token,
                json=payload,
            )
        )

    def delete_user(self, token, user_id):
        return self._json(
            self._request(
                "users",
                "DELETE",
                f"/api/v1/users/{user_id}",
                token=token,
            )
        )

    def courses(self, token):
        return self._json(
            self._request("courses", "GET", "/api/v1/courses", token=token)
        )

    def course(self, token, course_id):
        return self._json(
            self._request(
                "courses",
                "GET",
                f"/api/v1/courses/{course_id}",
                token=token,
            )
        )

    def create_course(self, token, payload):
        return self._json(
            self._request(
                "courses",
                "POST",
                "/api/v1/courses",
                token=token,
                json=payload,
            )
        )

    def update_course(self, token, course_id, payload):
        return self._json(
            self._request(
                "courses",
                "PUT",
                f"/api/v1/courses/{course_id}",
                token=token,
                json=payload,
            )
        )

    def delete_course(self, token, course_id):
        return self._json(
            self._request(
                "courses",
                "DELETE",
                f"/api/v1/courses/{course_id}",
                token=token,
            )
        )

    def enroll(self, token, course_id):
        return self._json(
            self._request(
                "courses",
                "POST",
                f"/api/v1/courses/{course_id}/enroll",
                token=token,
            )
        )

    def unenroll(self, token, course_id):
        return self._json(
            self._request(
                "courses",
                "DELETE",
                f"/api/v1/courses/{course_id}/enroll",
                token=token,
            )
        )

    def my_enrollments(self, token):
        return self._json(
            self._request(
                "courses",
                "GET",
                "/api/v1/courses/enrollments/me",
                token=token,
            )
        )

    def course_enrollments(self, token, course_id):
        return self._json(
            self._request(
                "courses",
                "GET",
                f"/api/v1/courses/{course_id}/enrollments",
                token=token,
            )
        )

    def update_enrollment(self, token, enrollment_id, status):
        return self._json(
            self._request(
                "courses",
                "PUT",
                f"/api/v1/courses/enrollments/{enrollment_id}/status",
                token=token,
                json={"status": status},
            )
        )

    def issue_certificate(self, token, course_id):
        return self._json(
            self._request(
                "certificates",
                "POST",
                f"/api/v1/certificates/courses/{course_id}/issue",
                token=token,
            )
        )

    def my_certificates(self, token):
        return self._json(
            self._request(
                "certificates",
                "GET",
                "/api/v1/certificates/me",
                token=token,
            )
        )

    def verify_certificate(self, code):
        return self._json(
            self._request(
                "certificates",
                "GET",
                f"/api/v1/certificates/verify/{code}",
            )
        )

    def download_certificate(self, token, certificate_id):
        return self._request(
            "certificates",
            "GET",
            f"/api/v1/certificates/{certificate_id}/download",
            token=token,
        )
