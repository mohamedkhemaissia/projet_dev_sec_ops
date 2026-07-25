from functools import wraps
from io import BytesIO
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from api_client import ServiceError

web_bp = Blueprint("web", __name__)


def is_safe_local_url(target):
    if not target or "\\" in target:
        return False
    parsed = urlsplit(target)
    return (
        not parsed.scheme
        and not parsed.netloc
        and parsed.path.startswith("/")
        and not parsed.path.startswith("//")
    )


def api():
    return current_app.extensions["traininghub_api"]


def token():
    return session.get("access_token")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not token():
            flash("Connectez-vous pour accéder à cet espace.", "info")
            return redirect(url_for("web.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = session.get("user", {})
            if not token():
                return redirect(url_for("web.login"))
            if user.get("role") != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def handle_service_error(error, redirect_endpoint=None):
    if error.status_code == 401:
        session.clear()
        flash("Votre session a expiré. Veuillez vous reconnecter.", "warning")
        return redirect(url_for("web.login"))
    flash(error.message, "danger")
    if redirect_endpoint:
        return redirect(url_for(redirect_endpoint))
    return None


def safe_list(call):
    try:
        return call() or []
    except ServiceError as error:
        flash(error.message, "warning")
        return []


def parse_course_form():
    return {
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "duration": request.form.get("duration", "").strip(),
        "level": request.form.get("level", "beginner"),
        "category": request.form.get("category", "").strip(),
    }


@web_bp.get("/")
def home():
    if token():
        return redirect(url_for("web.dashboard"))
    return render_template("public/home.html", layout="public")


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if token():
        return redirect(url_for("web.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            result = api().login(email, password)
            session.clear()
            session["access_token"] = result["token"]
            session["user"] = result["user"]
            session.permanent = True
            flash(f"Bienvenue, {result['user']['name']} !", "success")
            next_url = request.args.get("next", "")
            if is_safe_local_url(next_url):
                return redirect(next_url)
            return redirect(url_for("web.dashboard"))
        except ServiceError as error:
            flash(error.message, "danger")
    return render_template("public/login.html", layout="auth")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if token():
        return redirect(url_for("web.dashboard"))
    if request.method == "POST":
        payload = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
            "password": request.form.get("password", ""),
        }
        if payload["password"] != request.form.get("password_confirm", ""):
            flash("Les mots de passe ne correspondent pas.", "danger")
        else:
            try:
                api().register(payload)
                flash("Votre compte est prêt. Vous pouvez vous connecter.", "success")
                return redirect(url_for("web.login"))
            except ServiceError as error:
                flash(error.message, "danger")
    return render_template("public/register.html", layout="auth")


@web_bp.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("web.home"))


@web_bp.route("/verify", methods=["GET", "POST"])
def verify():
    code = request.values.get("code", "").strip().upper()
    result = None
    searched = bool(code)
    if searched:
        try:
            result = api().verify_certificate(code)
        except ServiceError as error:
            if error.status_code != 404:
                flash(error.message, "danger")
    return render_template(
        "public/verify.html",
        layout="public",
        code=code,
        result=result,
        searched=searched,
    )


@web_bp.get("/dashboard")
@login_required
def dashboard():
    role = session.get("user", {}).get("role")
    endpoint = "web.admin_dashboard" if role == "admin" else "web.learner_dashboard"
    return redirect(url_for(endpoint))


@web_bp.get("/learner")
@role_required("learner")
def learner_dashboard():
    courses = safe_list(lambda: api().courses(token()))
    enrollments = safe_list(lambda: api().my_enrollments(token()))
    certificates = safe_list(lambda: api().my_certificates(token()))
    enrolled_ids = {item["course_id"] for item in enrollments}
    recommended = [course for course in courses if course["id"] not in enrolled_ids][:3]
    stats = {
        "courses": len(enrollments),
        "in_progress": sum(item["status"] == "in_progress" for item in enrollments),
        "completed": sum(item["status"] == "completed" for item in enrollments),
        "certificates": len(certificates),
    }
    return render_template(
        "learner/dashboard.html",
        stats=stats,
        enrollments=enrollments[:3],
        recommended=recommended,
    )


@web_bp.get("/courses")
@login_required
def courses():
    all_items = safe_list(lambda: api().courses(token()))
    items = list(all_items)
    query = request.args.get("q", "").strip().lower()
    level = request.args.get("level", "").strip()
    category = request.args.get("category", "").strip()
    if query:
        items = [
            item
            for item in items
            if query in item["title"].lower()
            or query in item["description"].lower()
            or query in item["category"].lower()
        ]
    if level:
        items = [item for item in items if item["level"] == level]
    if category:
        items = [item for item in items if item["category"] == category]

    enrollments = []
    if session["user"]["role"] == "learner":
        enrollments = safe_list(lambda: api().my_enrollments(token()))
    enrollment_map = {item["course_id"]: item for item in enrollments}
    categories = sorted({item["category"] for item in all_items})
    return render_template(
        "shared/courses.html",
        courses=items,
        categories=categories,
        enrollment_map=enrollment_map,
    )


@web_bp.get("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    try:
        course = api().course(token(), course_id)
    except ServiceError as error:
        if error.status_code == 404:
            abort(404)
        return handle_service_error(error, "web.courses")
    enrollment = None
    if session["user"]["role"] == "learner":
        enrollment = next(
            (
                item
                for item in safe_list(lambda: api().my_enrollments(token()))
                if item["course_id"] == course_id
            ),
            None,
        )
    return render_template(
        "shared/course_detail.html",
        course=course,
        enrollment=enrollment,
    )


@web_bp.post("/courses/<int:course_id>/enroll")
@role_required("learner")
def enroll(course_id):
    try:
        api().enroll(token(), course_id)
        flash("Inscription confirmée. Bonne formation !", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.courses")
    return redirect(url_for("web.course_detail", course_id=course_id))


@web_bp.post("/courses/<int:course_id>/unenroll")
@role_required("learner")
def unenroll(course_id):
    try:
        api().unenroll(token(), course_id)
        flash("Votre inscription a été annulée.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.learner_enrollments")
    return redirect(url_for("web.learner_enrollments"))


@web_bp.get("/learner/enrollments")
@role_required("learner")
def learner_enrollments():
    enrollments = safe_list(lambda: api().my_enrollments(token()))
    return render_template("learner/enrollments.html", enrollments=enrollments)


@web_bp.post("/learner/certificates/issue/<int:course_id>")
@role_required("learner")
def issue_certificate(course_id):
    try:
        api().issue_certificate(token(), course_id)
        flash("Votre certificat est disponible.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.learner_enrollments")
    return redirect(url_for("web.learner_certificates"))


@web_bp.get("/learner/certificates")
@role_required("learner")
def learner_certificates():
    certificates = safe_list(lambda: api().my_certificates(token()))
    return render_template(
        "learner/certificates.html",
        certificates=certificates,
    )


@web_bp.get("/certificates/<int:certificate_id>/download")
@login_required
def download_certificate(certificate_id):
    try:
        response = api().download_certificate(token(), certificate_id)
    except ServiceError as error:
        return handle_service_error(error, "web.dashboard")
    return send_file(
        BytesIO(response.content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"traininghub-certificate-{certificate_id}.pdf",
    )


@web_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        payload = {}
        for field in ("name", "email", "password"):
            value = request.form.get(field, "").strip()
            if value:
                payload[field] = value
        try:
            updated = api().update_profile(token(), payload)
            session["user"] = updated
            flash("Votre profil a été mis à jour.", "success")
            return redirect(url_for("web.profile"))
        except ServiceError as error:
            redirect_response = handle_service_error(error)
            if redirect_response:
                return redirect_response
    return render_template("shared/profile.html")


@web_bp.get("/admin")
@role_required("admin")
def admin_dashboard():
    users = safe_list(lambda: api().users(token()))
    courses_list = safe_list(lambda: api().courses(token()))
    enrollment_count = 0
    completed_count = 0
    for course in courses_list:
        items = safe_list(lambda course_id=course["id"]: api().course_enrollments(token(), course_id))
        enrollment_count += len(items)
        completed_count += sum(item["status"] == "completed" for item in items)
    stats = {
        "learners": sum(user["role"] == "learner" for user in users),
        "courses": len(courses_list),
        "enrollments": enrollment_count,
        "completed": completed_count,
    }
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=users[-5:][::-1],
        recent_courses=courses_list[-4:][::-1],
    )


@web_bp.get("/admin/users")
@role_required("admin")
def admin_users():
    users = safe_list(lambda: api().users(token()))
    query = request.args.get("q", "").strip().lower()
    if query:
        users = [
            user
            for user in users
            if query in user["name"].lower() or query in user["email"].lower()
        ]
    return render_template("admin/users.html", users=users)


@web_bp.post("/admin/users/<int:user_id>/role")
@role_required("admin")
def admin_update_user_role(user_id):
    try:
        api().update_user(token(), user_id, {"role": request.form.get("role")})
        flash("Le rôle a été mis à jour.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.admin_users")
    return redirect(url_for("web.admin_users"))


@web_bp.post("/admin/users/<int:user_id>/delete")
@role_required("admin")
def admin_delete_user(user_id):
    try:
        api().delete_user(token(), user_id)
        flash("L’utilisateur a été supprimé.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.admin_users")
    return redirect(url_for("web.admin_users"))


@web_bp.get("/admin/courses")
@role_required("admin")
def admin_courses():
    return render_template(
        "admin/courses.html",
        courses=safe_list(lambda: api().courses(token())),
    )


@web_bp.route("/admin/courses/new", methods=["GET", "POST"])
@role_required("admin")
def admin_create_course():
    course = {}
    if request.method == "POST":
        course = parse_course_form()
        try:
            api().create_course(token(), course)
            flash("La formation a été publiée.", "success")
            return redirect(url_for("web.admin_courses"))
        except ServiceError as error:
            flash(error.message, "danger")
    return render_template(
        "admin/course_form.html",
        course=course,
        form_title="Créer une formation",
        submit_label="Publier la formation",
    )


@web_bp.route("/admin/courses/<int:course_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def admin_edit_course(course_id):
    try:
        course = api().course(token(), course_id)
    except ServiceError as error:
        if error.status_code == 404:
            abort(404)
        return handle_service_error(error, "web.admin_courses")
    if request.method == "POST":
        course = parse_course_form()
        try:
            api().update_course(token(), course_id, course)
            flash("La formation a été mise à jour.", "success")
            return redirect(url_for("web.admin_courses"))
        except ServiceError as error:
            flash(error.message, "danger")
    return render_template(
        "admin/course_form.html",
        course=course,
        form_title="Modifier la formation",
        submit_label="Enregistrer les modifications",
    )


@web_bp.post("/admin/courses/<int:course_id>/delete")
@role_required("admin")
def admin_delete_course(course_id):
    try:
        api().delete_course(token(), course_id)
        flash("La formation a été supprimée.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.admin_courses")
    return redirect(url_for("web.admin_courses"))


@web_bp.get("/admin/courses/<int:course_id>/enrollments")
@role_required("admin")
def admin_enrollments(course_id):
    try:
        course = api().course(token(), course_id)
        enrollments = api().course_enrollments(token(), course_id)
    except ServiceError as error:
        return handle_service_error(error, "web.admin_courses")
    return render_template(
        "admin/enrollments.html",
        course=course,
        enrollments=enrollments,
    )


@web_bp.post("/admin/enrollments/<int:enrollment_id>/status")
@role_required("admin")
def admin_update_enrollment(enrollment_id):
    course_id = request.form.get("course_id", type=int)
    try:
        api().update_enrollment(token(), enrollment_id, request.form.get("status"))
        flash("La progression a été actualisée.", "success")
    except ServiceError as error:
        return handle_service_error(error, "web.admin_courses")
    return redirect(url_for("web.admin_enrollments", course_id=course_id))
