from flask import request
import connexion
from Src.start_service import start_service

# Инициализируем сервисы
service = start_service()
service.start()

app = connexion.FlaskApp(__name__)

# Настраиваем роуты фильтрации
service.filter_service.setup_routes(app.app)

# Настраиваем роуты ОСВ
service.turnover_service.setup_routes(app.app)

"""
Проверить доступность REST API
"""
@app.route("/api/accessibility", methods=['GET'])
def formats():
    return "SUCCESS"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port = 8080)