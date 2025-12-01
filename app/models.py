from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    city = Column(String, nullable=True)
    subscribed = Column(Boolean, default=False)

    def __repr__(self):
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, "
            f"username={self.username}, city={self.city}, subscribed={self.subscribed})>"
        )

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    city = Column(String, nullable=False)
    daily_notifications = Column(Boolean, default=True)
    notification_time = Column(String, nullable=True)

    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return (
            f"<Subscription(id={self.id}, user_id={self.user_id}, "
            f"city={self.city}, daily_notifications={self.daily_notifications})>"
        )

User.subscriptions = relationship(
    "Subscription",
    order_by=Subscription.id,
    back_populates="user",
)