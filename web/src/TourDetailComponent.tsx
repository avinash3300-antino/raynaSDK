import React from "react";
import { createRoot } from "react-dom/client";
import { useToolOutput, useTheme } from "./hooks";
import type { TourDetailOutput } from "./types";

function TourDetailApp() {
  const toolOutput = useToolOutput<TourDetailOutput>();
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
    star: "#f59e0b",
    imagePlaceholder: isDark
      ? "linear-gradient(135deg, #222 0%, #333 50%, #222 100%)"
      : "linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 50%, #e2e8f0 100%)",
  };

  if (!toolOutput) {
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
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>🔍</div>
        <div style={{ fontSize: "14px", fontWeight: 600 }}>Tour details not available</div>
      </div>
    );
  }

  const tour = toolOutput;

  const formatPrice = (price: number): string => {
    if (price >= 1000) return price.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    return price.toFixed(price % 1 === 0 ? 0 : 2);
  };

  const hasDiscount =
    tour.originalPrice != null && tour.currentPrice != null && tour.originalPrice > tour.currentPrice;

  return (
    <div
      style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        padding: "16px",
        background: colors.background,
        maxWidth: "600px",
        margin: "0 auto",
      }}
    >
      {/* Hero Image */}
      <div
        style={{
          position: "relative",
          height: "200px",
          width: "100%",
          borderRadius: "12px",
          overflow: "hidden",
          marginBottom: "16px",
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
              fontSize: "48px",
            }}
          >
            🌍
          </div>
        )}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 60%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            left: "16px",
            right: "16px",
          }}
        >
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#ffffff", textShadow: "0 1px 4px rgba(0,0,0,0.4)" }}>
            {tour.title}
          </div>
          <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.85)", marginTop: "4px" }}>
            📍 {tour.location} · {tour.category}
          </div>
        </div>
      </div>

      {/* Price Card */}
      <div
        style={{
          background: colors.cardBg,
          border: `1px solid ${colors.border}`,
          borderRadius: "12px",
          padding: "16px",
          marginBottom: "16px",
          textAlign: "center",
        }}
      >
        {hasDiscount && (
          <div style={{ fontSize: "13px", color: colors.textTertiary, textDecoration: "line-through", marginBottom: "4px" }}>
            {tour.currency} {formatPrice(tour.originalPrice!)}
          </div>
        )}
        <div
          style={{
            display: "inline-block",
            background: colors.accent,
            color: "#ffffff",
            padding: "8px 20px",
            borderRadius: "20px",
            fontSize: "18px",
            fontWeight: 700,
          }}
        >
          {tour.currentPrice
            ? `${tour.currency} ${formatPrice(tour.currentPrice)}`
            : "Check price"}
        </div>
        {tour.currentPrice ? <div style={{ fontSize: "11px", color: colors.textTertiary, marginTop: "4px" }}>per person</div> : null}
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        {/* Duration */}
        <div
          style={{
            textAlign: "center",
            padding: "14px 8px",
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
          }}
        >
          <div style={{ fontSize: "18px", fontWeight: 700, color: colors.accent }}>
            {tour.duration || "N/A"}
          </div>
          <div style={{ fontSize: "10px", color: colors.textSecondary, textTransform: "uppercase", marginTop: "4px" }}>
            Duration
          </div>
        </div>

        {/* Rating */}
        <div
          style={{
            textAlign: "center",
            padding: "14px 8px",
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
          }}
        >
          <div style={{ fontSize: "18px", fontWeight: 700, color: colors.star }}>
            {tour.rating != null ? `★ ${tour.rating.toFixed(1)}` : "N/A"}
          </div>
          <div style={{ fontSize: "10px", color: colors.textSecondary, textTransform: "uppercase", marginTop: "4px" }}>
            Rating
          </div>
        </div>

        {/* R-Points */}
        <div
          style={{
            textAlign: "center",
            padding: "14px 8px",
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
          }}
        >
          <div style={{ fontSize: "18px", fontWeight: 700, color: colors.accent }}>
            {tour.rPoints ?? 0}
          </div>
          <div style={{ fontSize: "10px", color: colors.textSecondary, textTransform: "uppercase", marginTop: "4px" }}>
            R-Points
          </div>
        </div>
      </div>

      {/* Description */}
      {tour.description && (
        <div
          style={{
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "16px",
          }}
        >
          <div style={{ fontSize: "14px", fontWeight: 600, color: colors.text, marginBottom: "8px" }}>
            About this tour
          </div>
          <div style={{ fontSize: "13px", color: colors.textSecondary, lineHeight: "1.5" }}>
            {tour.description}
          </div>
        </div>
      )}

      {/* Highlights */}
      {tour.highlights && tour.highlights.length > 0 && (
        <div
          style={{
            background: colors.cardBg,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "16px",
          }}
        >
          <div style={{ fontSize: "14px", fontWeight: 600, color: colors.text, marginBottom: "10px" }}>
            Highlights
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {tour.highlights.map((h, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "13px",
                  color: colors.textSecondary,
                }}
              >
                <span style={{ color: colors.accent, fontWeight: 700 }}>✓</span>
                {h}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inclusions / Exclusions */}
      {((tour.inclusions && tour.inclusions.length > 0) || (tour.exclusions && tour.exclusions.length > 0)) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: tour.inclusions?.length && tour.exclusions?.length ? "1fr 1fr" : "1fr",
            gap: "12px",
            marginBottom: "16px",
          }}
        >
          {tour.inclusions && tour.inclusions.length > 0 && (
            <div
              style={{
                background: colors.cardBg,
                border: `1px solid ${colors.border}`,
                borderRadius: "8px",
                padding: "12px",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: 600, color: colors.accent, marginBottom: "8px" }}>
                Included
              </div>
              {tour.inclusions.map((item, i) => (
                <div key={i} style={{ fontSize: "12px", color: colors.textSecondary, marginBottom: "4px" }}>
                  ✓ {item}
                </div>
              ))}
            </div>
          )}
          {tour.exclusions && tour.exclusions.length > 0 && (
            <div
              style={{
                background: colors.cardBg,
                border: `1px solid ${colors.border}`,
                borderRadius: "8px",
                padding: "12px",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#ef4444", marginBottom: "8px" }}>
                Not Included
              </div>
              {tour.exclusions.map((item, i) => (
                <div key={i} style={{ fontSize: "12px", color: colors.textSecondary, marginBottom: "4px" }}>
                  ✗ {item}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Book Now CTA */}
      <button
        onClick={() => {
          if (window.openai?.openExternal) {
            window.openai.openExternal({ href: tour.url });
          } else {
            window.open(tour.url, "_blank");
          }
        }}
        style={{
          width: "100%",
          padding: "14px 0",
          borderRadius: "12px",
          border: "none",
          background: colors.accent,
          color: "#ffffff",
          fontSize: "15px",
          fontWeight: 700,
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
        Book Now on Rayna Tours
      </button>
    </div>
  );
}

const root = document.getElementById("rayna-tour-detail-root");
if (root) {
  createRoot(root).render(<TourDetailApp />);
}
