from app.core.database import engine, Base
from app.modules.auth import models as auth_models
from app.modules.pedidos import models as pedidos_models

# Create all tables
Base.metadata.create_all(bind=engine)
print("Tablas creadas exitosamente")