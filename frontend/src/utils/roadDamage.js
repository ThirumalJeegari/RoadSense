function routePointAtFraction(routePoints, fraction) {
  if (!routePoints?.length) {
    return { latitude: 0, longitude: 0 };
  }
  if (routePoints.length === 1) {
    return routePoints[0];
  }

  const bounded = Math.max(0, Math.min(1, fraction));
  const position = bounded * (routePoints.length - 1);
  const index = Math.floor(position);
  const nextIndex = Math.min(index + 1, routePoints.length - 1);
  const ratio = position - index;
  const start = routePoints[index];
  const end = routePoints[nextIndex];

  return {
    latitude: start.latitude + (end.latitude - start.latitude) * ratio,
    longitude: start.longitude + (end.longitude - start.longitude) * ratio,
  };
}

function damageTypeFor(index, surveyMode) {
  if (surveyMode === "After heavy rain") {
    return ["pothole risk", "waterlogging erosion", "edge break", "surface distress"][index % 4];
  }
  if (surveyMode === "Construction zone") {
    return ["surface cut", "uneven patch", "loose gravel", "edge break"][index % 4];
  }
  return ["linear crack", "pothole risk", "surface distress", "edge break"][index % 4];
}

function damageSeverityFor(index, surveyMode) {
  if (["After heavy rain", "Construction zone"].includes(surveyMode) && index % 3 === 0) {
    return "High";
  }
  return index % 2 === 0 ? "Moderate" : "Low";
}

function priorityFor(severity) {
  return { High: "Urgent", Moderate: "Schedule", Low: "Monitor" }[severity] || "Monitor";
}

function actionFor(severity) {
  if (severity === "High") {
    return "Dispatch inspection crew and mark repair zone.";
  }
  if (severity === "Moderate") {
    return "Add to maintenance queue and monitor deterioration.";
  }
  return "Monitor during next routine survey.";
}

function recommendationFor(severity, count) {
  if (severity === "High") {
    return `${count} damaged points found. Prioritize red markers for field inspection.`;
  }
  if (severity === "Moderate") {
    return `${count} damaged points found. Schedule maintenance for marked locations.`;
  }
  return `${count} minor damaged points found. Keep monitoring this road stretch.`;
}

export function routeDamageReport(route, roadStart, roadEnd, surveyMode) {
  const routePoints = route?.route_points || [];
  const distanceKm = Number(route?.summary?.distance_km || 0);

  if (!routePoints.length) {
    return {
      score: 0,
      severity: "Low",
      damage_area_percent: 0,
      detection_count: 0,
      detections: [],
      recommendation: "No route geometry available for this road segment.",
    };
  }

  const baseCount = distanceKm < 3 ? 2 : distanceKm < 12 ? 3 : 5;
  const modeBoost = {
    "Routine survey": 0,
    "After heavy rain": 2,
    "Citizen complaints": 1,
    "Construction zone": 3,
  };
  const detectionCount = Math.min(8, baseCount + (modeBoost[surveyMode] || 0));

  const detections = Array.from({ length: detectionCount }, (_, index) => {
    const fraction = (index + 1) / (detectionCount + 1);
    const point = routePointAtFraction(routePoints, fraction);
    const severity = damageSeverityFor(index, surveyMode);
    return {
      id: `D${index + 1}`,
      type: damageTypeFor(index, surveyMode),
      severity,
      road_segment: `${roadStart} to ${roadEnd}`,
      damage_location: `${(distanceKm * fraction).toFixed(2)} km from ${roadStart}`,
      map_latitude: Number(point.latitude.toFixed(6)),
      map_longitude: Number(point.longitude.toFixed(6)),
      estimated_length_m: Number((4.5 + index * 2.2 + distanceKm * 0.03).toFixed(1)),
      lane: ["left lane", "center lane", "right lane", "road shoulder"][index % 4],
      priority: priorityFor(severity),
      action: actionFor(severity),
      fraction,
    };
  });

  const score = Math.min(
    100,
    detections.reduce((total, item) => total + { Low: 12, Moderate: 24, High: 38 }[item.severity], 0),
  );
  const severity = detections.some((item) => item.severity === "High")
    ? "High"
    : detections.some((item) => item.severity === "Moderate")
      ? "Moderate"
      : "Low";

  return {
    score,
    severity,
    damage_area_percent: Number(Math.min(18, detectionCount * 1.8 + distanceKm * 0.02).toFixed(1)),
    detection_count: detections.length,
    detections,
    recommendation: recommendationFor(severity, detections.length),
  };
}
