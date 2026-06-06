import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const INDIA_CENTER = [22.9734, 78.6569];

const TRAFFIC_COLORS = {
  normal: "#2563eb",
  moderate: "#d97706",
  heavy: "#dc2626",
};

const BASE_LAYERS = {
  street: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    options: {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    },
  },
  light: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    options: {
      maxZoom: 20,
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    },
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    options: {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics, and the GIS user community",
    },
  },
};

function toLatLng(point) {
  return [point.latitude, point.longitude];
}

function routePath(route) {
  return (route?.route_points || []).map(toLatLng);
}

function extendBounds(bounds, latLng) {
  if (Number.isFinite(latLng[0]) && Number.isFinite(latLng[1])) {
    bounds.push(latLng);
  }
}

export default function MapPanel({ type, route, parking, damageReport, mapStyle = "satellite" }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const tileRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, {
        zoomControl: false,
        scrollWheelZoom: true,
      }).setView(INDIA_CENTER, 5);
      L.control.zoom({ position: "bottomright" }).addTo(mapRef.current);
    }

    const map = mapRef.current;
    const baseLayer = BASE_LAYERS[mapStyle] || BASE_LAYERS.satellite;
    if (tileRef.current) {
      tileRef.current.removeFrom(map);
    }
    tileRef.current = L.tileLayer(baseLayer.url, baseLayer.options).addTo(map);

    if (layerRef.current) {
      layerRef.current.removeFrom(map);
    }

    const layerGroup = L.layerGroup();
    const bounds = [];

    if (type === "traffic" && route?.route_segments?.length) {
      route.route_segments.forEach((segment) => {
        const path = segment.path.map(([longitude, latitude]) => [latitude, longitude]);
        path.forEach((latLng) => extendBounds(bounds, latLng));
        L.polyline(path, {
          color: TRAFFIC_COLORS[segment.status] || "#2563eb",
          weight: segment.status === "heavy" ? 8 : 6,
          opacity: 0.9,
        })
          .bindTooltip(segment.tooltip || segment.status_label || "Traffic segment")
          .addTo(layerGroup);
      });

      if (route.start) {
        L.circleMarker(toLatLng(route.start), {
          radius: 8,
          color: "#0f766e",
          fillColor: "#0f9f8f",
          fillOpacity: 1,
          weight: 2,
        })
          .bindTooltip(`Start: ${route.start.name}`)
          .addTo(layerGroup);
      }
      if (route.end) {
        L.circleMarker(toLatLng(route.end), {
          radius: 8,
          color: "#111827",
          fillColor: "#102033",
          fillOpacity: 1,
          weight: 2,
        })
          .bindTooltip(`Destination: ${route.end.name}`)
          .addTo(layerGroup);
      }
    }

    if (type === "parking" && parking?.stalls?.length) {
      parking.stalls.forEach((stall) => {
        const latLng = [Number(stall.latitude), Number(stall.longitude)];
        extendBounds(bounds, latLng);
        const available = Number(stall.available_slots || 0);
        const color = available > 0 ? "#0f9f8f" : "#dc2626";
        L.circleMarker(latLng, {
          radius: Math.max(5, Math.min(12, Number(stall.capacity || 40) / 18)),
          color,
          fillColor: color,
          fillOpacity: 0.78,
          weight: 1.5,
        })
          .bindTooltip(
            `${stall.name || "Parking"} | Available ${available}/${stall.capacity || "-"} slots`,
          )
          .addTo(layerGroup);
      });
    }

    if (type === "damage" && route?.route_points?.length) {
      const path = routePath(route);
      path.forEach((latLng) => extendBounds(bounds, latLng));
      L.polyline(path, {
        color: damageReport?.severity === "High" ? "#dc2626" : "#d97706",
        weight: 8,
        opacity: 0.88,
      })
        .bindTooltip("Damaged road survey route")
        .addTo(layerGroup);

      (damageReport?.detections || []).forEach((item) => {
        const latLng = [Number(item.map_latitude), Number(item.map_longitude)];
        extendBounds(bounds, latLng);
        const color = item.severity === "High" ? "#dc2626" : item.severity === "Moderate" ? "#d97706" : "#2563eb";
        L.circleMarker(latLng, {
          radius: item.severity === "High" ? 10 : 8,
          color,
          fillColor: color,
          fillOpacity: 0.9,
          weight: 2,
        })
          .bindTooltip(`${item.id} | ${item.severity} | ${item.type} | ${item.damage_location}`)
          .addTo(layerGroup);
      });
    }

    layerGroup.addTo(map);
    layerRef.current = layerGroup;

    window.setTimeout(() => {
      map.invalidateSize();
      if (bounds.length) {
        map.fitBounds(bounds, { padding: [26, 26], maxZoom: type === "parking" ? 17 : 14 });
      } else {
        map.setView(INDIA_CENTER, 5);
      }
    }, 80);

    return undefined;
  }, [type, route, parking, damageReport, mapStyle]);

  return <div className="map-panel" ref={containerRef} />;
}
