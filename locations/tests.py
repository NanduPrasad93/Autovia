from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from unittest.mock import patch, MagicMock
import io
import json

from accounts.models import UserProfile
from locations.views import haversine_distance


class LocationsNearbyStationsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'AutoVia@LocTest2026!'
        cache.clear()

        # Vehicle Owner
        self.owner_user = User.objects.create_user(
            username='owner_clara',
            email='clara@autovia.test',
            password=self.password
        )
        self.owner_user.profile.role = UserProfile.Role.VEHICLE_OWNER
        self.owner_user.profile.save()

    # 1. Nearby stations page loads for authenticated vehicle owner
    def test_01_nearby_stations_page_access_authenticated_owner(self):
        self.client.login(username='owner_clara', password=self.password)
        res = self.client.get(reverse('locations:nearby_stations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Nearby Fuel & EV Charging Stations")
        self.assertContains(res, "Location Privacy Notice")
        self.assertContains(res, "Locate Near Me (GPS)")

    # 2. Unauthenticated access redirected to login
    def test_02_nearby_stations_unauthenticated_redirect(self):
        res = self.client.get(reverse('locations:nearby_stations'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res.url)

    # 3. Stations API returns valid markers and distance calculations
    def test_03_stations_api_returns_markers_and_calculated_distances(self):
        self.client.login(username='owner_clara', password=self.password)

        res = self.client.get(reverse('locations:stations_api'), {'lat': '12.9716', 'lon': '77.5946', 'type': 'all'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('stations', data)
        self.assertGreater(len(data['stations']), 0)

        first_station = data['stations'][0]
        self.assertIn('name', first_station)
        self.assertIn('lat', first_station)
        self.assertIn('lon', first_station)
        self.assertIn('distance_km', first_station)
        self.assertIn('fuels', first_station)
        self.assertGreater(first_station['distance_km'], 0.0)

    # 4. Stations API distinct filtering: Petrol, Diesel, and EV
    def test_04_stations_api_filtering_petrol_diesel_ev(self):
        self.client.login(username='owner_clara', password=self.password)

        # Filter: EV charging stations
        res_ev = self.client.get(reverse('locations:stations_api'), {'lat': '12.9716', 'lon': '77.5946', 'type': 'ev'})
        self.assertEqual(res_ev.status_code, 200)
        data_ev = res_ev.json()
        for s in data_ev['stations']:
            self.assertTrue(s.get('is_ev') or s.get('type') in ['EV_CHARGING', 'ALL'])

        # Filter: Diesel stations
        res_diesel = self.client.get(reverse('locations:stations_api'), {'lat': '12.9716', 'lon': '77.5946', 'type': 'diesel'})
        self.assertEqual(res_diesel.status_code, 200)
        data_diesel = res_diesel.json()
        for s in data_diesel['stations']:
            self.assertTrue(s.get('type') in ['DIESEL', 'ALL'] or 'Diesel' in ' '.join(s.get('fuels', [])))

    # 5. Stations API caching behavior
    def test_05_stations_api_caching(self):
        self.client.login(username='owner_clara', password=self.password)
        lat, lon = '13.0827', '80.2707'

        # First request populates cache
        res_1 = self.client.get(reverse('locations:stations_api'), {'lat': lat, 'lon': lon, 'type': 'all'})
        self.assertEqual(res_1.status_code, 200)

        cache_key = f"osm_stations_{round(float(lat), 2)}_{round(float(lon), 2)}_all"
        cached_result = cache.get(cache_key)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result['status'], 'ok')

        # Second request served directly from cache
        res_2 = self.client.get(reverse('locations:stations_api'), {'lat': lat, 'lon': lon, 'type': 'all'})
        self.assertEqual(res_2.status_code, 200)
        self.assertEqual(res_1.json(), res_2.json())

    # 6. Fallback reliability when external Overpass API fails
    @patch('urllib.request.urlopen')
    def test_06_stations_api_fallback_when_external_api_fails(self, mock_urlopen):
        # Simulate external network timeout
        mock_urlopen.side_effect = Exception("Overpass API Connection Timeout")
        self.client.login(username='owner_clara', password=self.password)

        res = self.client.get(reverse('locations:stations_api'), {'lat': '28.6139', 'lon': '77.2090', 'type': 'all'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        # Deterministic fallback stations must still be delivered
        self.assertGreaterEqual(len(data['stations']), 4)

    # 7. Haversine distance unit test
    def test_07_haversine_distance_calculation(self):
        # Distance between London (51.5074, -0.1278) and Paris (48.8566, 2.3522) is approx 343 km
        dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertGreater(dist, 335.0)
        self.assertLess(dist, 350.0)

    # 8. Compliant Tile Provider: CARTO Voyager is used instead of volunteer OSM server
    def test_08_map_tile_provider_uses_compliant_carto_service(self):
        self.client.login(username='owner_clara', password=self.password)
        res = self.client.get(reverse('locations:nearby_stations'))
        self.assertEqual(res.status_code, 200)
        # Compliant tile URL and attribution present
        self.assertContains(res, 'basemaps.cartocdn.com')
        self.assertContains(res, 'CARTO')
        # Blocked volunteer OSM tile server URL must NOT be used
        self.assertNotContains(res, 'tile.openstreetmap.org/{z}/{x}/{y}.png')

    # 9. Map tile error fallback banner present in DOM
    def test_09_map_tile_error_fallback_banner_present(self):
        self.client.login(username='owner_clara', password=self.password)
        res = self.client.get(reverse('locations:nearby_stations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'id="mapErrorBanner"')
        self.assertContains(res, 'Map tile service is temporarily degraded')

    # 10. Map container sizing and responsive attributes
    def test_10_map_container_configuration(self):
        self.client.login(username='owner_clara', password=self.password)
        res = self.client.get(reverse('locations:nearby_stations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'id="map"')
        self.assertContains(res, 'height: 540px')

