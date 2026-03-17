import React from "react";
import { createRoot } from "react-dom/client";
import { useToolOutput, useTheme } from "./hooks";
import type { TourCard, TourComparisonOutput } from "./types";

function TourCompareApp() {
  const toolOutput = useToolOutput<TourComparisonOutput>();
  const theme = useTheme();
  const isDark = theme === "dark";

  const colors = {
    background: isDark ? "#1a1a1a" : "#ffffff",
    cardBg: isDark ? "#2d2d2d" : "#f8f9fa",
    text: isDark ? "#ffffff" : "#000000",
    textSecondary: isDark ? "#a0a0a0" : "#6e6e6e",
    textTertiary: isDark ? "#707070" : "#999999",
    border: isDark ? "#3d3d3d" : "#e5e7eb",
    accent: "#10a37f",
    accentHover: "#0e8c6b",
    better: "#10a37f",
    betterBg: isDark ? "rgba(16, 163, 127, 0.1)" : "rgba(16, 163, 127, 0.05)",
    star: "#f59e0b",
    imagePlaceholder: isDark
      ? "linear-gradient(135deg, #222 0%, #333 50%, #222 100%)"
      : "linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 50%, #e2e8f0 100%)",
  };

  if (!toolOutput || !toolOutput.tours || toolOutput.tours.length === 0) {
    return (
      <div
        style={{
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          padding: "24px",
          textAlign: "center",
          color: colors.textSecondary,
          background: colors.cardBg,
          borderRadius: "12px",
          border: `1px solid ${colors.border}`,
        }}
      >
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>⚖️</div>
        <div style={{ fontSize: "14px", fontWeight: 600 }}>No tours to compare</div>
      </div>
    );
  }

  const { tours, comparison } = toolOutput;

  const formatPrice = (price: number): string => {
    if (price >= 1000) return price.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    return price.toFixed(price % 1 === 0 ? 0 : 2);
  };

  return (
    <div
      style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        padding: "16px",
        background: colors.background,
      }}
    >
      {/* Header */}
      <div style={{ fontSize: "16px", fontWeight: 700, color: colors.text, marginBottom: "16px", textAlign: "center" }}>
        Tour Comparison
      </div>

      {/* Tour Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.min(tours.length, 3)}, 1fr)`,
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        {tours.map((tour, index) => (
          <div
            key={tour.id || index}
            style={{
              background: colors.cardBg,
              border: `1px solid ${colors.border}`,
              borderRadius: "12px",
              overflow: "hidden",
              transition: "transform 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (window.openai?.userAgent?.capabilities?.hover) {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = isDark
                  ? "0 4px 12px rgba(0,0,0,0.3)"
                  : "0 4px 12px rgba(0,0,0,0.1)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            {/* Image */}
            <div
              style={{
                height: "100px",
                width: "100%",
                overflow: "hidden",
                background: colors.imagePlaceholder,
              }}
            >
              {tour.image ? (
                <img
                  src={tour.image}
                  alt={tour.title}
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "24px",
                  }}
                >
                  🌍
                </div>
              )}
            </div>

            {/* Content */}
            <div style={{ padding: "10px" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: colors.text, marginBottom: "4px", lineHeight: "1.3" }}>
                {tour.title}
              </div>
              <div style={{ fontSize: "11px", color: colors.textSecondary, marginBottom: "6px" }}>
                📍 {tour.location} · {tour.category}
              </div>
              <div style={{ fontSize: "14px", fontWeight: 800, color: colors.accent }}>
                {tour.currentPrice
                  ? `${tour.currency} ${formatPrice(tour.currentPrice)}`
                  : "Check price"}
              </div>
              {typeof tour.rating === "number" && tour.rating > 0 && (
                <div style={{ fontSize: "11px", color: colors.star, marginTop: "2px" }}>
                  ★ {tour.rating.toFixed(1)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Comparison Table */}
      {comparison && comparison.stats && comparison.stats.length > 0 && (
        <div
          style={{
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "12px",
            padding: "16px",
          }}
        >
          <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px", textAlign: "center", color: colors.text }}>
            Detailed Comparison
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                  <th
                    style={{
                      textAlign: "left",
                      padding: "8px",
                      fontWeight: 600,
                      color: colors.textSecondary,
                      fontSize: "12px",
                    }}
                  >
                    Stat
                  </th>
                  {tours.map((tour, i) => (
                    <th
                      key={i}
                      style={{
                        textAlign: "center",
                        padding: "8px",
                        fontWeight: 600,
                        color: colors.textSecondary,
                        fontSize: "12px",
                      }}
                    >
                      {tour.title.length > 20 ? tour.title.slice(0, 18) + "…" : tour.title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparison.stats.map((stat, statIndex) => (
                  <tr key={statIndex} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: "8px", fontWeight: 500, color: colors.text }}>
                      {stat.name}
                    </td>
                    {stat.values.map((value, colIndex) => {
                      const isBetter = stat.better === tours[colIndex]?.title;
                      return (
                        <td
                          key={colIndex}
                          style={{
                            textAlign: "center",
                            padding: "8px",
                            fontWeight: isBetter ? 700 : 500,
                            color: isBetter ? colors.better : colors.text,
                            background: isBetter ? colors.betterBg : "transparent",
                          }}
                        >
                          {value}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Book buttons */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(tours.length, 3)}, 1fr)`, gap: "8px", marginTop: "16px" }}>
        {tours.map((tour, i) => (
          <button
            key={i}
            onClick={() => {
              if (window.openai?.openExternal) {
                window.openai.openExternal({ href: tour.url });
              } else {
                window.open(tour.url, "_blank");
              }
            }}
            style={{
              padding: "10px 8px",
              borderRadius: "8px",
              border: "none",
              background: colors.accent,
              color: "#ffffff",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "background 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.accentHover;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = colors.accent;
            }}
          >
            Book {tour.title.length > 15 ? tour.title.slice(0, 13) + "…" : tour.title}
          </button>
        ))}
      </div>
    </div>
  );
}

const root = document.getElementById("rayna-tour-compare-root");
if (root) {
  createRoot(root).render(<TourCompareApp />);
}
