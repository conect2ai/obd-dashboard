"""
ODB Controller
"""
import datetime
import pandas
import re

from io import StringIO
from typing import List
from structlog import get_logger

from app.constants.odb import ODBSensorLabels, ODBSensorPrefixes, CSV_COLUM_SENSOR_MAP
from app.controllers.odb import BaseODBController
from app.controllers.odb.engine import EngineController
from app.controllers.odb.fuel import FuelController
from app.controllers.odb.gps import GPSController
from app.controllers.odb.session import SessionController
from app.models.obd import (
    OBDSensorUnit,
    OBDSensor,
    OBDSensorUser,
    OBDSensorValue,
)
from app.models.odb.session import ODBSession
from app.models.user import User


LOGGER = get_logger(__name__)


class ODBControllerError(Exception):
    """ Exception class for ODB Controller """
    pass


class ODBController(BaseODBController):
    """
    Controller class for ODB-related data manipulations.

    Attributes:
        - PREFIXES (app.constants.odb.ODBSensorPrefixes): Set of prefixes used to extract data from TORQUE request.
    """
    PREFIXES = ODBSensorPrefixes

    def _resolve_user(self, data: dict):
        """
        Resolves user from data.

        Raises:
            - ODBControllerError:
                If user email is not found in <data>;
                If there is no user corresponding to the email found in <data>;

        Args:
            - data (dict): Map of arguments received by TORQUE request.

        Returns:
            - user (app.models.user.User): User instance.
        """
        user_email = data.get('eml')
        if not user_email:
            raise ODBControllerError('User email not found')

        user: User = self.db_session.query(User).filter(User.email == user_email).first()
        if not user:
            raise ODBControllerError('User does not exist')

        return user

    def process_sensor_params(self, data: dict):
        """
        Process data receive from TORQUE.
        If identifies that the data is composed by keys identifying sensor specs, will register such specs in the DB.
        Sensors currently considered are described in <ODBSensorLabels>.

        Args:
            - data (dict): Data to be processed.
        """
        LOGGER.info('Receiving sensor data from TORQUE', **data)
        has_full_name_keys = any(filter(re.compile(f'{self.PREFIXES.FULL_NAME}.*').match, data.keys()))
        if has_full_name_keys:
            LOGGER.info('Will ignore request since it\'s related to sensor params')
            return

        user = self._resolve_user(data)
        LOGGER.info(f'Request is attached to {user.first_name} {user.last_name}', user_id=user.id)
        session = SessionController(user_id=user.id).get_or_create(data['session'])
        LOGGER.info('Resolved session to proceed', **session.to_dict())
        now = datetime.datetime.now()
        data_keys = list(data.keys())

        # GPS Reading
        if ODBSensorLabels.GPS.LATITUDE in data_keys and ODBSensorLabels.GPS.LONGITUDE in data_keys:
            LOGGER.info('Will save GPS reading')
            gps_controller = GPSController(db_session=self.db_session)
            gps_reading = gps_controller.register_gps_reading(
                session=session,
                lat=data[ODBSensorLabels.GPS.LATITUDE],
                lng=data[ODBSensorLabels.GPS.LONGITUDE],
                date=now,
            )
            LOGGER.info('Saved GPS Reading', **gps_reading.to_dict())

        # Fuel Level
        if ODBSensorLabels.Fuel.LEVEL in data_keys:
            LOGGER.info('Will save Fuel Level')
            fuel_controller = FuelController(db_session=self.db_session)
            fuel_level = fuel_controller.register_fuel_level(session, data[ODBSensorLabels.Fuel.LEVEL], now)
            LOGGER.info('Saved Fuel Level', **fuel_level.to_dict())

        # Engine sensors
        engine_controller = EngineController(db_session=self.db_session)
        if ODBSensorLabels.Engine.LOAD in data_keys:
            LOGGER.info('Will save Engine Load value')
            load = engine_controller.register_load(session, data[ODBSensorLabels.Engine.LOAD], now)
            LOGGER.info('Saved Engine Load', **load.to_dict())
        if ODBSensorLabels.Engine.RPM in data_keys:
            LOGGER.info('Will save Engine RPM value')
            rpm = engine_controller.register_rpm(session, data[ODBSensorLabels.Engine.RPM], now)
            LOGGER.info('Saved Engine RPM', **rpm.to_dict())

    def process_csv(self, user: User, csv_file):
        """
        Will process a CSV file generated by the TORQUE application, registering the values for each
        considered sensor in the database.

        Args:
            - user (app.models.user.User): User instance;
            - csv_file (werkzeug.FileStorage): A file representation of the CSV file created by TORQUE.
        """
        csv = pandas.read_csv(StringIO(csv_file.read().decode('utf-8')), usecols=CSV_COLUM_SENSOR_MAP.values())
        start_datetime = self._resolve_date_from_csv_row(csv.iloc[0])
        gen_session_id = str(start_datetime.timestamp()).replace('.', '')[:12]

        if self.db_session.query(ODBSession).filter(ODBSession.id == gen_session_id).first():
            return

        session = ODBSession(id=gen_session_id, user_id=user.id, date=start_datetime)
        self.db_session.add(session)
        self.db_session.flush()

        gps_controller = GPSController(db_session=self.db_session)
        gps_controller.register_gps_from_csv(session, csv, flush=True)

        engine_controller = EngineController(db_session=self.db_session)
        engine_controller.register_load_from_csv(session, csv, flush=True)
        engine_controller.register_rpm_from_csv(session, csv, flush=True)
        engine_controller.register_speed_from_csv(session, csv, flush=True)

        fuel_controller = FuelController(db_session=self.db_session)
        fuel_controller.register_fuel_level_from_csv(session, csv, flush=True)

        self.db_session.commit()
