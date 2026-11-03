from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login


def role_required(allowed_roles):
    """
    Decorator for views that checks if the logged in user has one of the allowed roles.
    - If user is not authenticated: Redirect to login.
    - If user is authenticated but not authorized: Raise PermissionDenied (HTTP 403 Forbidden).
    - If 'ADMIN' is in allowed_roles: Requires user.is_staff or user.is_superuser or role == 'ADMIN'.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url='accounts:login')

            profile = getattr(request.user, 'profile', None)
            user_role = profile.role if profile else None

            # Special case for ADMIN role checks
            if 'ADMIN' in allowed_roles:
                if request.user.is_staff or request.user.is_superuser or user_role == 'ADMIN':
                    return view_func(request, *args, **kwargs)
                raise PermissionDenied("Access Denied: Administrative privileges required.")

            # Standard role verification
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied(f"Access Denied: You do not have permission to access this dashboard.")
        return _wrapped_view
    return decorator


def vehicle_owner_required(view_func):
    return role_required(['VEHICLE_OWNER'])(view_func)


def mechanic_required(view_func):
    return role_required(['MECHANIC'])(view_func)


def workshop_required(view_func):
    return role_required(['WORKSHOP'])(view_func)


def supplier_required(view_func):
    return role_required(['SUPPLIER'])(view_func)


def admin_required(view_func):
    return role_required(['ADMIN'])(view_func)
