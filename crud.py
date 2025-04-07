import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def save_expense(db_session, expense_obj):
    """
    Save an Expense object to the database.
    Returns the saved object on success, None on failure.
    """
    try:
        db_session.add(expense_obj)
        db_session.commit()
        db_session.refresh(expense_obj)
        logger.info(f"Saved expense to DB: {expense_obj}")
        return expense_obj
    except SQLAlchemyError as e:
        logger.error(f"Database error during save_expense: {e}", exc_info=True)
        db_session.rollback()
        return None