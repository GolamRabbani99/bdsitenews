import { ImageResponse } from "next/og";
import { site } from "@/lib/site";

/** Default social-share card (used when an article has no photo).
 * Satori's built-in fonts can't render Bangla, so this card is English. */
export const runtime = "edge";
export const alt = site.name;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #1c1815 0%, #3d2020 100%)",
          color: "#faf7f1",
        }}
      >
        <div style={{ height: 10, width: "100%", background: "#b3202c", position: "absolute", top: 0 }} />
        <div style={{ fontSize: 92, fontWeight: 700, letterSpacing: -2 }}>
          {site.name}
        </div>
        <div style={{ marginTop: 18, fontSize: 34, color: "#d8d1c5", fontStyle: "italic" }}>
          {site.tagline}
        </div>
        <div style={{ marginTop: 36, fontSize: 24, color: "#b3202c", fontWeight: 700, letterSpacing: 6 }}>
          BDSITENEWS.COM
        </div>
      </div>
    ),
    size,
  );
}
