"use client";

import { useMemo, useState, useEffect } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  GeoJSON,
  ZoomControl,
} from "react-leaflet";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { getRiskZones } from "@/lib/api";

const CARTO_KEY = process.env.NEXT_PUBLIC_CARTO_KEY ?? "";
const TILE_URL = CARTO_KEY
  ? `https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${CARTO_KEY}`
  : "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = CARTO_KEY
  ? "&copy; OpenStreetMap contributors &copy; CARTO"
  : "&copy; OpenStreetMap contributors";

interface Property {
  id: string;
  title: string;
  lat: number;
  lng: number;
  riskLevel: "low" | "medium" | "high";
  price: number;
}

interface Props {
  properties: Property[];
  center?: [number, number];
  zoom?: number;
  showRiskLayer?: boolean;
  onPropertyClick?: (id: string) => void;
}

const RISK_COLORS = {
  low: "#16a34a",
  medium: "#d97706",
  high: "#dc2626",
};

type LayerKey = "flood" | "schools" | "kindergartens" | "hospitals";
type RiskKey = "low" | "medium" | "high";
type FieldId = LayerKey | `risk-${RiskKey}`;

interface FieldDef {
  id: FieldId;
  label: string;
  color: string;
  icon: string;
}

interface FieldGroup {
  id: string;
  label: string;
  fields: FieldDef[];
}

const FIELD_GROUPS: FieldGroup[] = [
  {
    id: "risk",
    label: "Үл хөдлөх хөрөнгийн эрсдэл",
    fields: [
      {
        id: "risk-low",
        label: "Аюулгүй",
        color: RISK_COLORS.low,
        icon: "🏠",
      },
      {
        id: "risk-medium",
        label: "Дунд",
        color: RISK_COLORS.medium,
        icon: "🏠",
      },
      {
        id: "risk-high",
        label: "Эрсдэлтэй",
        color: RISK_COLORS.high,
        icon: "🏠",
      },
    ],
  },
  {
    id: "safety",
    label: "Аюултай бүс",
    fields: [
      {
        id: "flood",
        label: "Үерийн бүс",
        color: "#ef4444",
        icon: "🌊",
      },
    ],
  },
  {
    id: "education",
    label: "Боловсрол",
    fields: [
      {
        id: "kindergartens",
        label: "Цэцэрлэг",
        color: "#eab308",
        icon: "🧸",
      },
      {
        id: "schools",
        label: "Сургууль",
        color: "#3b82f6",
        icon: "🏫",
      },
    ],
  },
  {
    id: "health",
    label: "Эрүүл мэндийн үйлчилгээ",
    fields: [
      {
        id: "hospitals",
        label: "Эмнэлэг",
        color: "#a855f7",
        icon: "🏥",
      },
    ],
  },
];

const ALL_FIELD_IDS: FieldId[] = FIELD_GROUPS.flatMap((g) =>
  g.fields.map((f) => f.id)
);

export default function MapView({
  properties,
  center = [47.8864, 106.9057],
  zoom = 12,
  showRiskLayer = true,
  onPropertyClick,
}: Props) {
  const [floodZones, setFloodZones] = useState<any>(null);
  const [schools, setSchools] = useState<any>(null);
  const [kindergartens, setKindergartens] = useState<any>(null);
  const [hospitals, setHospitals] = useState<any>(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [activeFields, setActiveFields] = useState<Set<FieldId>>(
    new Set(ALL_FIELD_IDS)
  );

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(FIELD_GROUPS.map((g) => g.id))
  );

  const toggleField = (id: FieldId) => {
    setActiveFields((prev) => {
      const next = new Set(prev);

      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }

      return next;
    });
  };

  const toggleGroup = (id: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);

      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }

      return next;
    });
  };

  useEffect(() => {
    if (!showRiskLayer) return;

    getRiskZones("flood_risk_zones")
      .then((data) => {
        if (data?.features?.length > 0) {
          setFloodZones(data);
        }
      })
      .catch(console.error);

    getRiskZones("schools")
      .then((data) => {
        if (data?.features?.length > 0) {
          setSchools(data);
        }
      })
      .catch(console.error);

    getRiskZones("kindergartens")
      .then((data) => {
        if (data?.features?.length > 0) {
          setKindergartens(data);
        }
      })
      .catch(console.error);

    getRiskZones("hospitals")
      .then((data) => {
        if (data?.features?.length > 0) {
          setHospitals(data);
        }
      })
      .catch(console.error);
  }, [showRiskLayer]);

  const renderPoint = (
    feature: any,
    latlng: any,
    color: string
  ) => {
    const name =
      feature.properties?.name ||
      feature.properties?.title ||
      "Мэдээлэлгүй";

    return L.circleMarker(latlng, {
      radius: 5,
      fillColor: color,
      color: "#ffffff",
      weight: 1.5,
      opacity: 1,
      fillOpacity: 0.9,
    }).bindPopup(`
      <div style="font-family:sans-serif;font-size:13px;font-weight:600;">
        ${name}
      </div>
    `);
  };

  const visibleProperties = useMemo(() => {
    return properties.filter((p) =>
      activeFields.has(`risk-${p.riskLevel}`)
    );
  }, [properties, activeFields]);

  const markerIcon = useMemo(
    () =>
      L.divIcon({
        className: "",
        html: `
          <span
            style="
              display:block;
              width:18px;
              height:18px;
              border-radius:9999px;
              border:2px solid white;
              box-shadow:0 2px 8px rgba(15,23,42,0.25);
              background:${RISK_COLORS.medium};
            "
          ></span>
        `,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      }),
    []
  );

  return (
    <div className="relative w-full h-[700px] overflow-hidden rounded-xl border border-slate-200 bg-white">

      {/* MAP */}
      <MapContainer
        center={center}
        zoom={zoom}
        className="w-full h-full z-0"
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <ZoomControl position="topright" />

        <TileLayer
          attribution={TILE_ATTRIBUTION}
          url={TILE_URL}
          referrerPolicy="strict-origin-when-cross-origin"
          maxZoom={19}
        />

        {/* Flood */}
        {showRiskLayer &&
          activeFields.has("flood") &&
          floodZones && (
            <GeoJSON
              data={floodZones}
              style={{
                color: "#ef4444",
                weight: 1,
                fillColor: "#ef4444",
                fillOpacity: 0.35,
              }}
            />
          )}

        {/* Schools */}
        {showRiskLayer &&
          activeFields.has("schools") &&
          schools && (
            <GeoJSON
              data={schools}
              pointToLayer={(feature, latlng) =>
                renderPoint(feature, latlng, "#3b82f6")
              }
            />
          )}

        {/* Kindergartens */}
        {showRiskLayer &&
          activeFields.has("kindergartens") &&
          kindergartens && (
            <GeoJSON
              data={kindergartens}
              pointToLayer={(feature, latlng) =>
                renderPoint(feature, latlng, "#eab308")
              }
            />
          )}

        {/* Hospitals */}
        {showRiskLayer &&
          activeFields.has("hospitals") &&
          hospitals && (
            <GeoJSON
              data={hospitals}
              pointToLayer={(feature, latlng) =>
                renderPoint(feature, latlng, "#a855f7")
              }
            />
          )}

        {/* Properties */}
        {visibleProperties.map((p) => (
          <Marker
            key={p.id}
            position={[p.lat, p.lng]}
            icon={L.divIcon({
              className: "",
              html: `
                <span
                  style="
                    display:block;
                    width:18px;
                    height:18px;
                    border-radius:9999px;
                    border:2px solid white;
                    box-shadow:0 2px 8px rgba(15,23,42,0.25);
                    background:${RISK_COLORS[p.riskLevel]};
                  "
                ></span>
              `,
              iconSize: [18, 18],
              iconAnchor: [9, 9],
            })}
            eventHandlers={{
              click: () => onPropertyClick?.(p.id),
            }}
          >
            <Popup>
              <div className="text-sm space-y-1">
                <div className="font-semibold text-slate-800">
                  {p.title}
                </div>

                <div className="text-slate-500">
                  {(p.price / 1_000_000).toFixed(0)}M ₮
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* TOGGLE BUTTON */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="
          absolute
          top-4
          left-4
          z-[1000]
          w-10
          h-10
          rounded-full
          bg-white
          shadow-lg
          border
          border-slate-200
          flex
          items-center
          justify-center
          hover:bg-slate-50
          transition-all
        "
      >
        <svg
          className={`w-5 h-5 text-slate-700 transition-transform duration-300 ${sidebarOpen ? "rotate-180" : ""
            }`}
          fill="none"
          viewBox="0 0 24 24"
        >
          <path
            d="M15 19L8 12L15 5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* SIDEBAR */}
      <div
        className={`
          absolute
          top-0
          left-0
          h-full
          w-72
          bg-white
          z-[999]
          border-r
          border-slate-200
          shadow-xl
          transition-transform
          duration-300
          ease-in-out
          overflow-y-auto
          ${sidebarOpen
            ? "translate-x-0"
            : "-translate-x-full"
          }
        `}
      >
        <div className="pt-16 pb-4">

          {FIELD_GROUPS.map((group) => {
            const isExpanded = expandedGroups.has(group.id);

            return (
              <div
                key={group.id}
                className="border-b border-slate-100"
              >
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className="
                    w-full
                    flex
                    items-center
                    justify-between
                    px-4
                    py-3
                    text-sm
                    font-semibold
                    text-slate-700
                    hover:bg-slate-50
                  "
                >
                  <span>{group.label}</span>

                  <svg
                    className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""
                      }`}
                    viewBox="0 0 12 12"
                    fill="none"
                  >
                    <path
                      d="M2.5 4.5L6 8L9.5 4.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>

                {isExpanded && (
                  <div className="pb-2">
                    {group.fields.map((field) => {
                      const isActive = activeFields.has(field.id);

                      return (
                        <button
                          key={field.id}
                          type="button"
                          onClick={() => toggleField(field.id)}
                          className="
                            w-full
                            flex
                            items-center
                            gap-3
                            px-4
                            py-2
                            hover:bg-slate-50
                          "
                        >
                          <span
                            className="
                              flex
                              items-center
                              justify-center
                              w-8
                              h-8
                              rounded-lg
                              text-sm
                              flex-shrink-0
                            "
                            style={{
                              backgroundColor: `${field.color}20`,
                            }}
                          >
                            {field.icon}
                          </span>

                          <span className="flex-1 text-left text-sm text-slate-700">
                            {field.label}
                          </span>

                          <span
                            className="w-4 h-4 rounded-full border-2"
                            style={{
                              borderColor: isActive
                                ? field.color
                                : "#cbd5e1",
                              backgroundColor: isActive
                                ? field.color
                                : "transparent",
                            }}
                          />
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {floodZones && (
            <div className="px-4 py-4 text-xs text-slate-400 border-t border-slate-100">
              Эх сурвалж:{" "}
              {floodZones.metadata?.source ||
                "manaikhoroo.ub.gov.mn"}{" "}
              ({floodZones.metadata?.updated_at || "2026"})
            </div>
          )}
        </div>
      </div>
    </div>
  );
}