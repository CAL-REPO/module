"""Common mixin base class for structured data operations.

This module defines the base mixin class that all specific mixins
(DataFrame mixins, Database mixins, etc.) should inherit from.
"""

from typing import TypeVar, Generic, Optional


# Type variable for policy generics
PolicyT = TypeVar('PolicyT')


class BaseOperationsMixin(Generic[PolicyT]):
    """Base class for all operations mixins.
    
    This class provides the common foundation for all mixin-based
    operations on structured data. It enforces a policy-driven design
    where each operation can be controlled by a policy object.
    
    Type Parameters:
        PolicyT: The type of policy object this mixin uses.
    
    Attributes:
        policy: The policy object controlling this mixin's behavior.
    """
    
    def __init__(self, policy: Optional[PolicyT] = None) -> None:
        """Initialize the mixin with an optional policy.
        
        Args:
            policy: Optional policy object. If not provided, a default
                policy will be created using :meth:`_default_policy`.
        """
        self.policy: PolicyT = policy if policy is not None else self._default_policy()
    
    def _default_policy(self) -> PolicyT:
        """Create a default policy instance.
        
        Subclasses must override this method to provide their specific
        default policy.
        
        Returns:
            A new policy instance with default values.
        
        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _default_policy()"
        )
    
    def validate(self) -> None:
        """Validate the current state based on policy settings.
        
        If :attr:`policy.auto_validate` is ``True``, this calls
        :meth:`_perform_validation`. Otherwise, it does nothing.
        """
        if hasattr(self.policy, 'auto_validate') and self.policy.auto_validate:
            self._perform_validation()
    
    def _perform_validation(self) -> None:
        """Perform actual validation logic.
        
        Subclasses should override this method to implement their
        specific validation rules. The default implementation does nothing.
        """
        pass
