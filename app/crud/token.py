from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.token import AccessToken

class CRUDToken(CRUDBase[AccessToken, dict, dict]):
    def create_token(
        self, db: Session, *, name: str, expires_in_days: Optional[int] = None
    ) -> AccessToken:
        """
        Create a new access token.
        
        Args:
            db: Database session
            name: A friendly name for the token
            expires_in_days: Number of days until token expires (None for no expiration)
            
        Returns:
            The created AccessToken
        """
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
            
        token = AccessToken(
            name=name,
            expires_at=expires_at
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token
    
    def get_by_token(self, db: Session, *, token: str) -> Optional[AccessToken]:
        """
        Get a token by its value.
        
        Args:
            db: Database session
            token: The token string to look up
            
        Returns:
            The AccessToken if found, None otherwise
        """
        return db.query(AccessToken).filter(AccessToken.token == token).first()
    
    def get_active_tokens(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[AccessToken]:
        """
        Get all active tokens.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active AccessToken objects
        """
        return db.query(AccessToken).filter(
            AccessToken.is_active == True
        ).offset(skip).limit(limit).all()
    
    def invalidate(self, db: Session, *, token_obj: AccessToken) -> AccessToken:
        """
        Invalidate a token.
        
        Args:
            db: Database session
            token_obj: The token to invalidate
            
        Returns:
            The updated AccessToken
        """
        token_obj.is_active = False
        db.add(token_obj)
        db.commit()
        db.refresh(token_obj)
        return token_obj
    
    def validate_token(self, db: Session, *, token: str) -> bool:
        """
        Validate if a token is valid.
        
        Args:
            db: Database session
            token: The token string to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        token_obj = self.get_by_token(db, token=token)
        if not token_obj or not token_obj.is_valid:
            return False
        return True

token = CRUDToken(AccessToken)
