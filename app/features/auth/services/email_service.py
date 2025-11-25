from app.platform.services.email import env, send_email


def send_verification_otp(to_email: str, first_name: str, otp: str):
    """Used for: Account Deletion Verification"""
    template = env.get_template("verification_code.html")
    html_content = template.render(first_name=first_name, otp_code=otp, expiration_minutes="10")
    send_email(to_email, "Verify Your Identity - Sitelytics", html_content)


def send_signup_verification(to_email: str, first_name: str, otp: str):
    """Used for: New User Signup Verification"""
    template = env.get_template("verify_signup.html")
    html_content = template.render(first_name=first_name, otp_code=otp, expiration_minutes="10")
    send_email(to_email, "Verify Your Email - Sitelytics", html_content)


def send_password_reset(to_email: str, first_name: str, otp: str):
    """Used for: Forgot Password"""
    template = env.get_template("reset_password.html")
    html_content = template.render(first_name=first_name, otp_code=otp, expiration_minutes="10")
    send_email(to_email, "Reset Your Password - Sitelytics", html_content)


def send_welcome_email(to_email: str, name: str):
    """Used for: Waitlist Confirmation"""
    template = env.get_template("welcome_email.html")
    html_content = template.render(name=name, dashboard_url="https://sitelytics.com/dashboard")
    send_email(to_email, "You're on the list! - Sitelytics", html_content)


def send_account_activation(to_email: str, first_name: str):
    """Used for: Welcome Dashboard (After Signup Verification)"""
    template = env.get_template("welcome_activation.html")
    html_content = template.render(
        first_name=first_name, action_url="https://sitelytics.com/get-review"
    )
    send_email(to_email, "Welcome to Sitelytics", html_content)


def review_request_email(to_email: str, first_name: str, site_name: str, review_link: str):
    """Used for: Audit/Review Requests"""
    template = env.get_template("review_request_confirmation.html")
    html_content = template.render(
        first_name=first_name,
        site_name=site_name,
        review_link=review_link,
        dashboard_url="https://sitelytics.com/dashboard",
    )
    send_email(to_email, f"Review Request for {site_name}", html_content)


def send_account_deleted(to_email: str, first_name: str):
    """Used for: Successful Deletion Notification"""
    template = env.get_template("account_deleted.html")
    html_content = template.render(first_name=first_name)
    send_email(to_email, "Your Account Has Been Deleted", html_content)
