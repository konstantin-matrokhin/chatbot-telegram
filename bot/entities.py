import datetime
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, func, Date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from telegram import Update

from utils import is_admin

engine = create_engine('sqlite:///data.db', echo=False)

Base = declarative_base()

class ChatUser(Base):
    __tablename__ = 'user'

    chat_id = Column(Integer, primary_key=True)
    username = Column(String())
    created_at = Column(DateTime(), nullable=False, default=func.now())
    last_active = Column(DateTime(), nullable=False, default=func.now())

    transactions = relationship('Transaction', back_populates='user')
    daily_stats = relationship('DailyStats', back_populates='user')


class DailyStats(Base):
    __tablename__ = 'daily_stats'

    user_id = Column(Integer, ForeignKey('user.chat_id'), primary_key=True)
    messages = Column(Integer, nullable=False, default=0)
    images = Column(Integer, nullable=False, default=0)
    for_day = Column(Date(), nullable=False, default=func.current_date(), primary_key=True)

    user = relationship('ChatUser', back_populates='daily_stats')


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(Integer, primary_key=True)
    plan_name = Column(String)
    transaction_id = Column(Integer, ForeignKey('transaction.id'))
    start_date = Column(DateTime, nullable=False, default=func.now())
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    transaction = relationship('Transaction', back_populates='subscription')

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.chat_id'), nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)
    ref_id = Column(String)
    created_at = Column(DateTime, nullable=False, default=func.now())

    user = relationship('ChatUser', back_populates='transactions')
    subscription = relationship('Subscription', back_populates='transaction')

Session = sessionmaker(bind=engine, expire_on_commit=False)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f'Error occurred: {e}')
        raise
    finally:
        session.close()


def create_chat_user_or_get(update: Update):
    chat_id = update.message.chat_id
    with Session() as session:
        chat_user = session.query(ChatUser).get(chat_id)
        if chat_user is not None:
            chat_user.last_active = datetime.datetime.now()
            session.commit()
            return chat_user
        try:
            chat_user = ChatUser()
            chat_user.chat_id = chat_id
            chat_user.username = f"@{update.message.from_user.username}" if update.message.from_user.username else f"{update.message.from_user.first_name} {update.message.from_user.last_name}"

            daily_stats = session.query(DailyStats).filter(DailyStats.user_id.is_(chat_id), DailyStats.for_day.is_(func.current_date())).first()
            if daily_stats is None:
                daily_stats = DailyStats(user_id=chat_id)
            daily_stats.for_day = func.current_date()
            session.add(chat_user)
            session.add(daily_stats)
            session.commit()
            return chat_user
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(e)
            raise

def update_stats(chat_id, messages=0, images=0):
    with Session() as session:
        daily_stats = get_stats_internal(session, chat_id)
        try:
            daily_stats.messages += messages
            daily_stats.images += images
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(e)
            raise

def get_stats_internal(session, chat_id):
    daily_stats = session.query(DailyStats).filter(DailyStats.user_id.is_(chat_id), DailyStats.for_day.is_(func.current_date())).first()
    if daily_stats is None:
        daily_stats = DailyStats(user_id=chat_id)
        session.add(daily_stats)
        session.commit()
    return daily_stats

def get_stats(chat_id) -> DailyStats:
    with session_scope() as session:
        return get_stats_internal(session, chat_id)

def is_user_within_messages_limit(chat_id, config):
    if is_admin(config, chat_id) or is_premium(chat_id):
        return True
    max_free_messages_daily = int(config['max_free_messages_daily'])
    with session_scope() as session:
        messages_today = get_stats_internal(session, chat_id).messages
    if messages_today >= max_free_messages_daily:
        return False
    return True

def is_user_within_images_limit(chat_id, config):
    if is_admin(config, chat_id) or is_premium(chat_id):
        return True
    max_free_images_daily = int(config['max_free_images_daily'])
    with session_scope() as session:
        images_today = get_stats_internal(session, chat_id).images
    if images_today >= max_free_images_daily:
        return False
    return True

def create_transaction(session: Session, chat_id, amount, ref_id, status) -> Transaction:
    user = session.query(ChatUser).get(chat_id)
    transaction = Transaction()
    transaction.user_id = user.chat_id
    transaction.currency = 'XTR'
    transaction.amount = amount
    transaction.status = status
    transaction.ref_id = ref_id
    session.add(transaction)
    session.flush()
    return transaction

# def update_transaction(session: Session, transaction_id: int, status: str):
#     transaction = session.query(Transaction).get(transaction_id)
#     transaction.status = status

# def cancel_transaction(transaction_id: int):
#     with session_scope() as session:
#         update_transaction(session, transaction_id, 'canceled')

def create_subscription(chat_id, amount, ref_id) -> Subscription:
    with session_scope() as session:
        transaction = create_transaction(session, chat_id, amount, ref_id, 'successful')
        start_date = datetime.datetime.today()
        end_date = datetime.datetime.today() + datetime.timedelta(days=30)
        subscription = Subscription(plan_name='Premium',
                                    transaction_id=transaction.id,
                                    start_date=start_date,
                                    end_date=end_date)
        session.add(subscription)
        return subscription

def is_premium(chat_id):
    with session_scope() as session:
        transaction = session.query(Transaction).filter(Transaction.user_id.is_(chat_id), Transaction.status.is_('successful')).first()
        if transaction is None:
            return False
        subscription = session.query(Subscription).filter(Subscription.transaction_id.is_(transaction.id), Subscription.end_date >= datetime.datetime.today()).first()
        return subscription is not None
