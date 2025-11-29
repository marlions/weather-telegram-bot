from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    city = Column(String, nullable=True)
    subscribed = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    city = Column(String, nullable=False)
    daily_notifications = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, city={self.city})>"

User.subscriptions = relationship("Subscription", order_by=Subscription.id, back_populates="user")