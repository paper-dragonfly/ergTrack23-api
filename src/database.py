from sqlalchemy import (
    Column,
    Integer,
    String,
    Sequence,
    ForeignKey,
    Date,
    Boolean,
    Float
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func


Base = declarative_base()


class AthleteTable(Base):
    __tablename__ = "athlete"

    user_id = Column(
        Integer,
        Sequence("user_user_id_seq"),
        primary_key=True,
        server_default="nextval('user_user_id_seq')",
    )
    auth_uid = Column(String)  # from firebase
    user_name = Column(String)  # from firebase or edited by user
    email = Column(String)  # from firebase
    last_post = Column(Date)
    dob = Column(Date)
    sex = Column(String)
    weight_class = Column(String)
    para_class = Column(String)
    country = Column(String)
    joined = Column(Date, server_default=func.now())
    team = Column(Integer, ForeignKey("team.team_id"))
    team_admin = Column(Boolean)

    def __repr__(self):
        return (
            "<AthleteTable(user_id='%s', auth_uid='%s',  user_name='%s', email='%s', last_post='%s', dob='%s', sex='%s', weight_class='%s', para_class='%s', country='%s', joined='%s', team='%s', team_admin='%s')>"
            % (
                self.user_id,
                self.auth_uid,
                self.user_name,
                self.email,
                self.last_post,
                self.dob,
                self.sex,
                self.weight_class,
                self.para_class,
                self.country,
                self.joined,
                self.team,
                self.team_admin
            )
        )


class WorkoutLogTable(Base):
    __tablename__ = "workout_log"

    workout_id = Column(
        Integer,
        Sequence("workout_log_workout_id_seq"),
        primary_key=True,
        server_default="nextval('workout_log_workout_id_seq')",
    )
    user_id = Column(Integer, ForeignKey("athlete.user_id"))
    description = Column(String)
    date = Column(Date)
    time = Column(String)
    meter = Column(Integer)
    split = Column(String)
    stroke_rate = Column(Integer)
    heart_rate = Column(Integer)
    split_variance = Column(Float)
    watts = Column(Integer)
    cal = Column(Integer) 
    image_hash = Column(String)
    subworkouts = Column(JSON)
    comment = Column(String)
    post_to_team = Column(Boolean)
    var_ints_rest = Column(JSON)

    def __repr__(self):
        return f"""<WorkoutLogTable(
            workout_id={self.workout_id}, user_id={self.user_id}, date={self.date}, 
            time={self.time}, meter={self.meter}, split={self.split}, 
            stroke_rate={self.stroke_rate}, heart_rate={self.heart_rate}, split_variance={self.split_variance}, 
            watts={self.watts}, cal={self.cal}, image_hash={self.image_hash}, 
            subworkouts={self.subworkouts}, comment={self.comment}, post_to_team={self.post_to_team},
            var_ints_rest_info={self.var_ints_rest})>"""
    
class TeamTable(Base):
    __tablename__ = 'team'

    team_id = Column(
        Integer,
        Sequence("team_team_id_seq"),
        primary_key=True,
        server_default="nextval('team_team_id_seq')"
    )
    team_name = Column(String)
    team_code = Column(String)

    def __repr__(self):
        return f"<TeamTable(team_id={self.team_id}, team_name={self.team_name}, team_code={self.team_code})>"

class FeedbackTable(Base):
    __tablename__ = 'feedback'
    
    feedback_id = Column(
        Integer,
        Sequence("feedback_feedback_id_seq"),
        primary_key=True,
    )
    date = Column(Date)
    user_id = Column(Integer, ForeignKey("athlete.user_id"))
    feedback_type = Column(String) 
    comment = Column(String)
    
    def __repr__(self):
        return f"<FeedbackTable(feedback_id={self.feedback_id}, date={self.date}, user_id={self.user_id}, feedback_type='{self.feedback_type}', comment='{self.comment}')>"
