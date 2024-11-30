import logging

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, func, Date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from telegram import Update

from bot.utils import is_admin

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
    created_at = Column(DateTime, nullable=False, default=func.now())

    user = relationship('ChatUser', back_populates='transactions')
    subscription = relationship('Subscription', back_populates='transaction')

Session = sessionmaker(bind=engine)

def create_chat_user_or_get(update: Update):
    session = Session()
    chat_user = session.query(ChatUser).get(update.message.chat_id)
    if chat_user is not None:
        return chat_user
    try:
        chat_user = ChatUser()
        chat_user.chat_id = update.message.chat_id
        chat_user.username = f"@{update.message.from_user.username}" if update.message.from_user.username else f"{update.message.from_user.first_name} {update.message.from_user.last_name}"
        daily_stats = DailyStats(user_id=chat_user.chat_id)
        session.add(chat_user)
        session.add(daily_stats)
        session.commit()
        return chat_user
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(e)
        raise e
    finally:
        session.close()

def update_stats(chat_id, messages=0, images=0):
    with Session() as session:
        daily_stats = get_stats(session, chat_id)
        try:
            daily_stats.messages += messages
            daily_stats.images += images
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(e)
            raise

def get_stats(session, chat_id):
    daily_stats = session.query(DailyStats).filter(DailyStats.user_id.is_(chat_id), DailyStats.for_day.is_(func.current_date())).first()
    if daily_stats is None:
        daily_stats = DailyStats(user_id=chat_id)
        session.add(daily_stats)
        session.commit()
    return daily_stats

def is_user_within_messages_limit(chat_id, config):
    if is_admin(config, chat_id):
        return True
    max_free_messages_daily = int(config['max_free_messages_daily'])
    with Session() as session:
        messages_today = get_stats(session, chat_id).messages
    if messages_today >= max_free_messages_daily:
        return False
    return True

def is_user_within_images_limit(chat_id, config):
    if is_admin(config, chat_id):
        return True
    max_free_images_daily = int(config['max_free_images_daily'])
    with Session() as session:
        images_today = get_stats(session, chat_id).images
    if images_today >= max_free_images_daily:
        return False
    return True
