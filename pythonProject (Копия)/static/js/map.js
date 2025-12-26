// Инициализация карты Рубцовска
let map;
let markers = [];
let currentCategory = 'all';

function initMap() {
    // Координаты центра Рубцовска
    const rubtsovskCenter = [51.5147, 81.2061];

    // Создаем карту
    map = L.map('map').setView(rubtsovskCenter, 13);

    // Добавляем слой OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // Загружаем точки с сервера
    loadPoints();

    // Добавляем обработчики для фильтров категорий
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            filterMarkers();
        });
    });
}

function loadPoints() {
    fetch('/api/points')
        .then(response => response.json())
        .then(points => {
            // Очищаем старые маркеры
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];

            // Добавляем новые маркеры
            points.forEach(point => {
                const marker = L.marker([point.lat, point.lng])
                    .addTo(map)
                    .bindPopup(`
                        <div style="max-width: 300px;">
                            <h6>${point.title}</h6>
                            <p class="small">${point.description.substring(0, 100)}...</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="badge bg-primary">${point.category}</span>
                                <a href="/point/${point.id}" class="btn btn-sm btn-primary">Подробнее</a>
                            </div>
                        </div>
                    `);

                marker.pointData = point;
                markers.push(marker);
            });
        })
        .catch(error => console.error('Error loading points:', error));
}

function filterMarkers() {
    markers.forEach(marker => {
        if (currentCategory === 'all' || marker.pointData.category === currentCategory) {
            map.addLayer(marker);
        } else {
            map.removeLayer(marker);
        }
    });
}

// Инициализируем карту при загрузке страницы
document.addEventListener('DOMContentLoaded', initMap);