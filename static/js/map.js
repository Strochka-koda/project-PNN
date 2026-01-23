let map;
let vectorSource;
let markers = [];
let currentCategory = 'all';

function initMap() {
    const rubtsovskCenter = [81.2061, 51.5147];
    vectorSource = new ol.source.Vector();
    const vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: function(feature) {
            return new ol.style.Style({
                image: new ol.style.Icon({
                    anchor: [0.5, 1],
                    src: 'https://cdnjs.cloudflare.com/ajax/libs/openlayers/4.6.5/ol.css',
                    img: 'https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.15.1/build/ol.css'
                })
            });
        }
    });
    map = new ol.Map({
        target: 'map',
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            }),
            vectorLayer
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat(rubtsovskCenter),
            zoom: 13
        })
    });
    hideOSMAttribution();
    loadPoints();
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            filterMarkers();
        });
    });
}

function hideOSMAttribution() {
    setTimeout(() => {
        const attribution = document.querySelector('.ol-attribution');
        if (attribution) {
            attribution.style.display = 'none';
        }
    }, 100);
}

function loadPoints() {
    fetch('/api/points')
        .then(response => response.json())
        .then(points => {
            vectorSource.clear();
            markers = [];
            points.forEach(point => {
                const feature = new ol.Feature({
                    geometry: new ol.geom.Point(
                        ol.proj.fromLonLat([point.lng, point.lat])
                    ),
                    data: point
                });
                feature.setStyle(createMarkerStyle(point.category));
                feature.on('click', function(evt) {
                    showPopup(point);
                });

                vectorSource.addFeature(feature);
                markers.push(feature);
            });
        })
        .catch(error => console.error('Error loading points:', error));
}

function createMarkerStyle(category) {
    const colors = {
        'sport': '#FF5722',
        'culture': '#4CAF50',
        'food': '#FF9800',
        'shop': '#9C27B0',
        'default': '#2196F3'
    };

    const color = colors[category] || colors.default;

    return new ol.style.Style({
        image: new ol.style.Circle({
            radius: 8,
            fill: new ol.style.Fill({ color: color }),
            stroke: new ol.style.Stroke({
                color: '#FFFFFF',
                width: 2
            })
        }),
        text: new ol.style.Text({
            text: '📍',
            font: '18px Arial',
            fill: new ol.style.Fill({ color: color }),
            offsetY: -15
        })
    });
}

function showPopup(point) {
    const popup = document.createElement('div');
    popup.className = 'ol-popup';
    popup.innerHTML = `
        <div style="max-width: 300px; padding: 10px;">
            <h6>${point.title}</h6>
            <p class="small">${point.description.substring(0, 100)}...</p>
            <div class="d-flex justify-content-between align-items-center">
                <span class="badge bg-primary">${point.category}</span>
                <a href="/point/${point.id}" class="btn btn-sm btn-primary">Подробнее</a>
            </div>
        </div>
    `;

    alert(`Точка: ${point.title}\nКатегория: ${point.category}\nОписание: ${point.description.substring(0, 50)}...`);
}

function filterMarkers() {
    markers.forEach(feature => {
        const point = feature.get('data');
        if (currentCategory === 'all' || point.category === currentCategory) {
            feature.setStyle(createMarkerStyle(point.category));
        } else {
            feature.setStyle(null);
        }
    });
}
document.addEventListener('DOMContentLoaded', initMap);