from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence,
    ForeignKey,
    Date,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSON

engine = create_engine("postgresql://katcha@localhost:5432/erg_track", echo=False)
Session = sessionmaker(bind=engine)

Base = declarative_base()


class UserTable(Base):
    __tablename__ = "user"

    user_id = Column(
        Integer,
        Sequence("user_user_id_seq"),
        primary_key=True,
        server_default="nextval('user_user_id_seq')",
    )
    auth_uid = Column(String)  # from firebase
    user_name = Column(String)  # from firebase or edited by user
    email = Column(String)  # from firebase

    def __repr__(self):
        return (
            "<UserTable(user_id='%s', auth_uid='%s',  user_name='%s', email='%s')>"
            % (self.user_id, self.auth_uid, self.user_name, self.email)
        )


class WorkoutLogTable(Base):
    __tablename__ = "workout_log"

    workout_id = Column(
        Integer,
        Sequence("workout_log_workout_id_seq"),
        primary_key=True,
        server_default="nextval('workout_log_workout_id_seq')",
    )
    user_id = Column(Integer, ForeignKey("user.user_id"))
    date = Column(Date)
    time = Column(String)
    meter = Column(Integer)
    split = Column(String)
    stroke_rate = Column(Integer)
    interval = Column(Boolean)
    image_hash = Column(String)
    subworkouts = Column(JSON)
    comment = Column(String)

    def __repr__(self):
        return f"<WorkoutLogTable(workout_id={self.workout_id}, user_id={self.user_id}, date={self.date}, time={self.time}, meter={self.meter}, split={self.split}, stroke_rate={self.stroke_rate}, interval={self.interval}, image_hash={self.image_hash}, subworkouts={self.subworkouts}, comment={self.comment})>"


# Below:  uses SQLAlchemy directly to make tables, confuses aleembic. Don't use/
# Base.metadata.create_all(engine)


# class SubWorkoutTable(Base):
#     __tablename__ = "subworkout"

#     sub_id = Column(Integer, Sequence("subworkout_id_sequ"), primary_key=True)
#     workout_id = Column(Integer, ForeignKey("workout_log.workout_id"))
#     sub_time = Column(String)
#     sub_meter = Column(Integer)
#     sub_split = Column(String)
#     sub_stroke_rate = Column(Integer)
#     rest = Column(String)
