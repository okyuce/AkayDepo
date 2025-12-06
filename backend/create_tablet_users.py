from sqlmodel import Session, select
from app.core.database import engine
from app.models import Station
from app.models.user import User
import re

# Get all stations
session = Session(engine)
stations = session.exec(select(Station).order_by(Station.name)).all()

print(f"Found {len(stations)} stations")

for station in stations:
    # Extract station number from name (İstasyon-1, İstasyon-2, etc.)
    match = re.match(r'İstasyon-(\d+)', station.name)
    if not match:
        print(f"Skipping station {station.name} - invalid name format")
        continue
    
    station_number = int(match.group(1))
    username = f"tablet{station_number}"
    
    # Check if user already exists
    existing_user = session.exec(
        select(User).where(User.username == username)
    ).first()
    
    if existing_user:
        print(f"User {username} already exists - updating station_id")
        existing_user.station_id = station.id
        existing_user.is_active = True
        session.add(existing_user)
    else:
        print(f"Creating user {username} for station {station.name}")
        user = User(
            username=username,
            role="tablet",
            station_id=station.id,
            is_active=True
        )
        user.set_password("tablet123")
        session.add(user)

session.commit()
print("Done!")
