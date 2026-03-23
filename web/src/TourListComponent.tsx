import React from "react";
import { createRoot } from "react-dom/client";
import { useToolOutput, useWidgetState, useTheme } from "./hooks";
import type { TourCard, TourListOutput, TourListWidgetState } from "./types";

function TourListApp() {
  const toolOutput = useToolOutput<TourListOutput>();
  const theme = useTheme();
  const [widgetState, setWidgetState] = useWidgetState<TourListWidgetState>({
    favorites: [],
  });

  const isDark = theme === "dark";
  const favorites = widgetState?.favorites ?? [];

  const colors = {
    background: isDark ? "#1a1a1a" : "#ffffff",
    cardBg: isDark ? "#2d2d2d" : "#f8f9fa",
    cardBgHover: isDark ? "#353535" : "#f0f1f3",
    text: isDark ? "#ffffff" : "#000000",
    textSecondary: isDark ? "#a0a0a0" : "#6e6e6e",
    textTertiary: isDark ? "#707070" : "#999999",
    border: isDark ? "#3d3d3d" : "#e5e7eb",
    accent: "#000000",
    accentHover: "#333333",
    discount: "#ef4444",
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
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>🌍</div>
        <div style={{ fontSize: "14px", fontWeight: 600 }}>No tours found</div>
        <div style={{ fontSize: "12px", marginTop: "4px", color: colors.textTertiary }}>
          Try searching for Dubai, Bangkok, or Singapore
        </div>
      </div>
    );
  }

  const { tours, title, subtitle, totalResults } = toolOutput;

  const toggleFavorite = (tourId: string) => {
    const newFavorites = favorites.includes(tourId)
      ? favorites.filter((id) => id !== tourId)
      : [...favorites, tourId];
    setWidgetState({ ...widgetState!, favorites: newFavorites });
  };

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
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontSize: "16px", fontWeight: 700, color: colors.text }}>
          {title}
        </div>
        {subtitle && (
          <div style={{ fontSize: "12px", color: colors.textSecondary, marginTop: "2px" }}>
            {subtitle}
          </div>
        )}
      </div>

      {/* Tour Cards - Horizontal Scroll */}
      <div
        style={{
          display: "flex",
          overflowX: "auto",
          gap: "16px",
          paddingBottom: "8px",
          scrollSnapType: "x mandatory",
          WebkitOverflowScrolling: "touch",
          scrollbarWidth: "thin",
        }}
      >
        {tours.map((tour, index) => {
          const isFavorite = favorites.includes(tour.id);
          const hasDiscount =
            tour.originalPrice != null &&
            tour.currentPrice != null &&
            tour.originalPrice > tour.currentPrice;

          return (
            <div
              key={tour.id || index}
              style={{
                background: colors.cardBg,
                border: `1px solid ${colors.border}`,
                borderRadius: "12px",
                overflow: "hidden",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
                display: "flex",
                flexDirection: "column",
                minWidth: "260px",
                maxWidth: "280px",
                flexShrink: 0,
                scrollSnapAlign: "start",
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
              {/* Image Section */}
              <div
                style={{
                  position: "relative",
                  height: "140px",
                  width: "100%",
                  overflow: "hidden",
                  background: colors.imagePlaceholder,
                }}
              >
                {tour.image ? (
                  <img
                    src={tour.image}
                    alt={tour.title}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      display: "block",
                    }}
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
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      color: colors.textTertiary,
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ fontSize: "28px", marginBottom: "4px" }}>🌍</span>
                    <span>{tour.category || "Tour"}</span>
                  </div>
                )}

                {/* Gradient overlay */}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.05) 50%, transparent 100%)",
                    pointerEvents: "none",
                  }}
                />

                {/* Discount badge */}
                {tour.discountPercentage && tour.discountPercentage > 0 && (
                  <span
                    style={{
                      position: "absolute",
                      top: "8px",
                      left: "8px",
                      background: "#ffffff",
                      color: "#000000",
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "3px 8px",
                      borderRadius: "12px",
                      boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                    }}
                  >
                    -{tour.discountPercentage}%
                  </span>
                )}

                {/* New / Category badge */}
                <span
                  style={{
                    position: "absolute",
                    top: "8px",
                    right: "8px",
                    background: "rgba(0,0,0,0.5)",
                    backdropFilter: "blur(4px)",
                    color: "#ffffff",
                    fontSize: "11px",
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: "12px",
                  }}
                >
                  {tour.isNew ? "New" : "Tour"}
                </span>

                {/* Favorite button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(tour.id);
                  }}
                  style={{
                    position: "absolute",
                    top: "8px",
                    right: tour.isNew || true ? "60px" : "8px",
                    background: "rgba(0,0,0,0.4)",
                    backdropFilter: "blur(4px)",
                    border: "none",
                    borderRadius: "50%",
                    width: "28px",
                    height: "28px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    fontSize: "14px",
                    padding: 0,
                  }}
                >
                  {isFavorite ? "❤️" : "🤍"}
                </button>

                {/* Location on image */}
                {tour.location && (
                  <span
                    style={{
                      position: "absolute",
                      bottom: "8px",
                      left: "8px",
                      color: "#ffffff",
                      fontSize: "12px",
                      fontWeight: 500,
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      textShadow: "0 1px 3px rgba(0,0,0,0.6)",
                    }}
                  >
                    📍 {tour.location}
                  </span>
                )}

                {/* Rating on image */}
                {typeof tour.rating === "number" && tour.rating > 0 && (
                  <span
                    style={{
                      position: "absolute",
                      bottom: "8px",
                      right: "8px",
                      background: "rgba(0,0,0,0.4)",
                      backdropFilter: "blur(4px)",
                      color: "#ffffff",
                      fontSize: "12px",
                      fontWeight: 600,
                      padding: "2px 6px",
                      borderRadius: "6px",
                      display: "flex",
                      alignItems: "center",
                      gap: "3px",
                    }}
                  >
                    <span style={{ color: colors.star }}>★</span>
                    {tour.rating.toFixed(1)}
                  </span>
                )}
              </div>

              {/* Content Section */}
              <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
                {/* Title */}
                <h3
                  style={{
                    fontSize: "13px",
                    fontWeight: 700,
                    color: colors.text,
                    margin: 0,
                    lineHeight: "1.3",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    minHeight: "34px",
                  }}
                >
                  {tour.title}
                </h3>

                {/* Duration chip */}
                {tour.duration && (
                  <span
                    style={{
                      fontSize: "11px",
                      color: colors.textSecondary,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "3px",
                    }}
                  >
                    ⏱ {tour.duration}
                  </span>
                )}

                {/* Price section */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-end",
                    justifyContent: "space-between",
                    paddingTop: "8px",
                    borderTop: `1px solid ${colors.border}`,
                    marginTop: "auto",
                  }}
                >
                  <div>
                    {hasDiscount && (
                      <span
                        style={{
                          fontSize: "11px",
                          color: colors.textTertiary,
                          textDecoration: "line-through",
                          display: "block",
                          marginBottom: "2px",
                        }}
                      >
                        {tour.currency} {formatPrice(tour.originalPrice!)}
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: "16px",
                        fontWeight: 800,
                        color: colors.text,
                      }}
                    >
                      {tour.currentPrice
                        ? `${tour.currency} ${formatPrice(tour.currentPrice)}`
                        : tour.priceLabel || "Check price"}
                    </span>
                  </div>
                  {tour.currentPrice ? <span
                    style={{
                      fontSize: "10px",
                      color: colors.textTertiary,
                      fontWeight: 500,
                      paddingBottom: "2px",
                    }}
                  >
                    per person
                  </span> : null}
                </div>

                {/* Highlights */}
                {tour.highlights && tour.highlights.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", paddingTop: "4px" }}>
                    {tour.highlights.slice(0, 3).map((h) => (
                      <span
                        key={h}
                        style={{
                          fontSize: "10px",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background: isDark ? "#3d3d3d" : "#f0f1f3",
                          color: colors.textSecondary,
                          fontWeight: 500,
                          border: `1px solid ${colors.border}`,
                        }}
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                )}

                {/* Book Now button */}
                <button
                  onClick={() => {
                    if (window.openai?.openExternal) {
                      window.openai.openExternal({ href: tour.url });
                    } else {
                      window.open(tour.url, "_blank");
                    }
                  }}
                  style={{
                    marginTop: "4px",
                    width: "100%",
                    padding: "8px 0",
                    borderRadius: "8px",
                    border: "none",
                    background: colors.accent,
                    color: "#ffffff",
                    fontSize: "12px",
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
                  Book on Rayna Tours
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {totalResults > tours.length && (
        <div
          style={{
            textAlign: "center",
            marginTop: "12px",
            fontSize: "12px",
            color: colors.textTertiary,
          }}
        >
          Showing {tours.length} of {totalResults} tours
        </div>
      )}
    </div>
  );
}

const root = document.getElementById("rayna-tour-list-root");
if (root) {
  createRoot(root).render(<TourListApp />);
}
