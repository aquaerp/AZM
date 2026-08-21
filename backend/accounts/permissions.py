from rest_framework.permissions import BasePermission


class HasWorkshopRole(BasePermission):
    """Base permission for future API modules that require a workshop role."""

    allowed_roles: set[str] = set()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or (user.workshop_id and user.role in self.allowed_roles))
        )


class IsManager(HasWorkshopRole):
    """Compatibility permission: owners inherit all existing manager access."""

    allowed_roles = {"owner", "manager"}


class IsOwner(HasWorkshopRole):
    allowed_roles = {"owner"}


class IsOperationalStaff(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "receptionist"}


class IsWorkshopReader(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "accountant", "receptionist", "storekeeper"}


class IsFinancialStaff(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "accountant"}


class IsWorkshopTeamMember(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "accountant", "technician", "receptionist", "storekeeper"}


class IsManagerOrAccountant(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "accountant"}


class IsManagerOrTechnician(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "technician"}


class CanManageInventory(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "storekeeper"}


class CanIssueParts(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "storekeeper", "accountant", "receptionist"}


class CanReviewPartRequests(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "storekeeper", "accountant", "receptionist"}


class IsInventoryReader(HasWorkshopRole):
    allowed_roles = {"owner", "manager", "storekeeper", "accountant", "receptionist", "technician"}


class IsTechnician(HasWorkshopRole):
    allowed_roles = {"technician"}
