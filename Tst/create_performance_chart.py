import matplotlib.pyplot as plt
import numpy as np
import json
from datetime import datetime


def create_performance_chart():
    """
    Создает графики производительности на основе результатов тестов
    """
    # Пример данных (будут заменены реальными результатами)
    performance_data = {
        'block_period_scenarios': [
            {'scenario': 'Блокировка ДО', 'time': 0.45, 'transactions': 1500},
            {'scenario': 'Блокировка в НАЧАЛЕ', 'time': 0.52, 'transactions': 1500},
            {'scenario': 'Блокировка в СЕРЕДИНЕ', 'time': 0.48, 'transactions': 1500},
            {'scenario': 'Блокировка в КОНЦЕ', 'time': 0.51, 'transactions': 1500},
            {'scenario': 'Блокировка ПОСЛЕ', 'time': 0.47, 'transactions': 1500}
        ],
        'scalability_data': [
            {'transactions': 100, 'time': 0.12},
            {'transactions': 500, 'time': 0.25},
            {'transactions': 1000, 'time': 0.38},
            {'transactions': 1500, 'time': 0.52},
            {'transactions': 2000, 'time': 0.68}
        ]
    }

    # Создаем графики
    plt.figure(figsize=(15, 6))

    # График 1: Время при разных датах блокировки
    plt.subplot(1, 2, 1)
    scenarios = [item['scenario'] for item in performance_data['block_period_scenarios']]
    times = [item['time'] for item in performance_data['block_period_scenarios']]

    bars = plt.bar(scenarios, times, color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'])
    plt.title('⏱Время расчета при разных датах блокировки\n(1500 транзакций)', fontsize=12, fontweight='bold')
    plt.ylabel('Время (секунды)')
    plt.xticks(rotation=45, ha='right')

    # Добавляем значения на столбцы
    for bar, time in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f'{time:.2f}s', ha='center', va='bottom')

    # График 2: Масштабируемость
    plt.subplot(1, 2, 2)
    transactions = [item['transactions'] for item in performance_data['scalability_data']]
    scalability_times = [item['time'] for item in performance_data['scalability_data']]

    plt.plot(transactions, scalability_times, 'o-', linewidth=2, markersize=8, color='#ff6b6b')
    plt.title('Масштабируемость системы', fontsize=12, fontweight='bold')
    plt.xlabel('Количество транзакций')
    plt.ylabel('Время расчета (секунды)')
    plt.grid(True, alpha=0.3)

    # Добавляем точки на график
    for i, (x, y) in enumerate(zip(transactions, scalability_times)):
        plt.annotate(f'{y:.2f}s', (x, y), textcoords="offset points",
                     xytext=(0, 10), ha='center', fontsize=9)

    plt.tight_layout()

    # Сохраняем график
    chart_filename = 'performance_chart.png'
    plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"График сохранен как: {chart_filename}")


if __name__ == '__main__':
    create_performance_chart()