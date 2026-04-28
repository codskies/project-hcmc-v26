import folium
from folium.plugins import HeatMap, Geocoder

STATIONS = [
    {"name": "Ben Thanh",       "district": "District 1",          "lat": 10.7720, "lng": 106.6985, "price": 700_000_000},
    {"name": "Ba Son",          "district": "District 1",          "lat": 10.7847, "lng": 106.7052, "price": 450_000_000},
    {"name": "Van Thanh Park",  "district": "Binh Thanh",          "lat": 10.7908, "lng": 106.7150, "price": 120_000_000},
    {"name": "Tan Cang",        "district": "Binh Thanh",          "lat": 10.7985, "lng": 106.7235, "price": 100_000_000},
    {"name": "Thao Dien",       "district": "Thu Duc (former D2)", "lat": 10.8020, "lng": 106.7380, "price": 180_000_000},
    {"name": "An Phu",          "district": "Thu Duc (former D2)", "lat": 10.8015, "lng": 106.7495, "price": 150_000_000},
    {"name": "Rach Chiec",      "district": "Thu Duc (former D2)", "lat": 10.8075, "lng": 106.7600, "price":  80_000_000},
    {"name": "Phuoc Long",      "district": "Thu Duc (former D9)", "lat": 10.8138, "lng": 106.7710, "price":  65_000_000},
    {"name": "Binh Thai",       "district": "Thu Duc",             "lat": 10.8210, "lng": 106.7815, "price":  55_000_000},
    {"name": "Thu Duc",         "district": "Thu Duc",             "lat": 10.8490, "lng": 106.7540, "price":  50_000_000},
    {"name": "High-Tech Park",  "district": "Thu Duc",             "lat": 10.8536, "lng": 106.7975, "price":  45_000_000},
    {"name": "VNU-HCM",         "district": "Thu Duc",             "lat": 10.8700, "lng": 106.8020, "price":  40_000_000},
    {"name": "Tang Nhon Phu B", "district": "Thu Duc",             "lat": 10.8820, "lng": 106.8195, "price":  35_000_000},
    {"name": "Suoi Tien",       "district": "Thu Duc (former D9)", "lat": 10.8882, "lng": 106.8318, "price":  30_000_000},
]

# Investment tier configuration keyed by minimum price threshold
TIERS = [
    {
        "min": 400_000_000,
        "label": "Prime Asset",
        "desc": "Core CBD · Maximum liquidity",
        "tier_num": "1",
        "color": "#a50026",
        "star_color": "#f57c00",
        "stars": "★★★★★",
        "bg": "#fff5f5",
        "marker_color": "#a50026",
    },
    {
        "min": 150_000_000,
        "label": "High Growth",
        "desc": "Expat belt · Strong appreciation",
        "tier_num": "2",
        "color": "#d73027",
        "star_color": "#f57c00",
        "stars": "★★★★☆",
        "bg": "#fff8f0",
        "marker_color": "#d73027",
    },
    {
        "min": 70_000_000,
        "label": "Strong Value",
        "desc": "Mid-corridor · Solid fundamentals",
        "tier_num": "3",
        "color": "#e06c00",
        "star_color": "#9e9e9e",
        "stars": "★★★☆☆",
        "bg": "#f0fff4",
        "marker_color": "#f46d43",
    },
    {
        "min": 0,
        "label": "Emerging Zone",
        "desc": "Outer suburban · High upside risk",
        "tier_num": "4",
        "color": "#0277bd",
        "star_color": "#9e9e9e",
        "stars": "★★☆☆☆",
        "bg": "#f0f8ff",
        "marker_color": "#4fc3f7",
    },
]


def get_tier(price: int) -> dict:
    for t in TIERS:
        if price >= t["min"]:
            return t
    return TIERS[-1]


def format_price(price: int) -> str:
    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:.1f} Ty"
    return f"{price / 1_000_000:.0f}M"


def make_popup(s: dict, idx: int) -> folium.Popup:
    tier = get_tier(s["price"])
    price_label = format_price(s["price"])

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;width:295px;border-radius:14px;
                overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.22);border:1px solid #eee;">

      <!-- ── Header ── -->
      <div style="background:linear-gradient(135deg,#e84393 0%,#c0392b 100%);padding:16px 18px;">
        <div style="font-size:9px;letter-spacing:3px;color:rgba(255,255,255,0.7);
                    text-transform:uppercase;margin-bottom:5px;">
          Metro Line 1 &nbsp;·&nbsp; Station {idx + 1} / {len(STATIONS)}
        </div>
        <div style="font-size:21px;font-weight:800;color:#fff;line-height:1.15;">
          {s['name']}
        </div>
        <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:3px;">
          {s['district']}
        </div>
      </div>

      <!-- ── Body ── -->
      <div style="background:#fff;padding:16px 18px;">

        <!-- Price block -->
        <div style="background:{tier['bg']};border-left:4px solid {tier['color']};
                    padding:11px 14px;border-radius:0 10px 10px 0;margin-bottom:13px;">
          <div style="font-size:9px;color:#aaa;letter-spacing:2px;
                      text-transform:uppercase;">Market Price &nbsp;·&nbsp; 2026</div>
          <div style="font-size:30px;font-weight:900;color:{tier['color']};
                      line-height:1.1;margin-top:3px;">
            {price_label}
          </div>
          <div style="font-size:11px;color:#999;margin-top:2px;">VND per m²</div>
        </div>

        <!-- Investment rating block -->
        <div style="background:#f8f9fa;border-radius:10px;padding:11px 14px;
                    margin-bottom:13px;display:flex;align-items:center;
                    justify-content:space-between;">
          <div style="flex:1;min-width:0;">
            <div style="font-size:9px;color:#aaa;letter-spacing:2px;
                        text-transform:uppercase;">2026 Investment Rating</div>
            <div style="font-size:15px;font-weight:800;color:{tier['color']};
                        margin-top:3px;">{tier['label']}</div>
            <div style="font-size:11px;color:#999;margin-top:2px;">{tier['desc']}</div>
          </div>
          <div style="text-align:center;padding-left:12px;flex-shrink:0;">
            <div style="font-size:17px;color:{tier['star_color']};
                        letter-spacing:1px;">{tier['stars']}</div>
            <div style="font-size:9px;color:#ccc;letter-spacing:1px;
                        text-transform:uppercase;margin-top:3px;">
              Tier {tier['tier_num']}
            </div>
          </div>
        </div>

        <!-- Stats row -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
          <div style="background:#f8f9fa;border-radius:8px;padding:9px 10px;text-align:center;">
            <div style="font-size:9px;color:#bbb;letter-spacing:1px;
                        text-transform:uppercase;">Walking Zone</div>
            <div style="font-size:15px;font-weight:700;color:#333;margin-top:3px;">500 m</div>
          </div>
          <div style="background:#f8f9fa;border-radius:8px;padding:9px 10px;text-align:center;">
            <div style="font-size:9px;color:#bbb;letter-spacing:1px;
                        text-transform:uppercase;">Route</div>
            <div style="font-size:15px;font-weight:700;color:#e84393;margin-top:3px;">
              Metro 1
            </div>
          </div>
        </div>

        <div style="text-align:center;font-size:10px;color:#ddd;">
          Data for illustrative purposes only
        </div>
      </div>
    </div>
    """
    return folium.Popup(html, max_width=315)


def build_map() -> folium.Map:
    center_lat = sum(s["lat"] for s in STATIONS) / len(STATIONS)
    center_lng = sum(s["lng"] for s in STATIONS) / len(STATIONS)

    # tiles=None so we control all base layers explicitly
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles=None)

    # ── Base map layers ────────────────────────────────────────────────────────
    folium.TileLayer("CartoDB positron",    name="☀️ Light Mode",  control=True).add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="🌙 Dark Mode",   control=True).add_to(m)
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr=(
            "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, "
            "GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        ),
        name="🛰️ Satellite",
        control=True,
    ).add_to(m)

    # ── Feature groups (shown in layer control) ────────────────────────────────
    heatmap_fg = folium.FeatureGroup(name="Price Heatmap",     show=True)
    buffer_fg  = folium.FeatureGroup(name="500m Walking Zone", show=True)
    line_fg    = folium.FeatureGroup(name="Metro Line Route",  show=True)
    station_fg = folium.FeatureGroup(name="Metro Stations",    show=True)

    # ── Heatmap ────────────────────────────────────────────────────────────────
    max_price = max(s["price"] for s in STATIONS)
    HeatMap(
        [[s["lat"], s["lng"], s["price"] / max_price] for s in STATIONS],
        min_opacity=0.35,
        max_zoom=16,
        radius=45,
        blur=30,
        gradient={
            "0.0":  "#313695",
            "0.2":  "#74add1",
            "0.4":  "#fee090",
            "0.65": "#f46d43",
            "0.85": "#d73027",
            "1.0":  "#a50026",
        },
    ).add_to(heatmap_fg)

    # ── 500m walking zone buffers ──────────────────────────────────────────────
    for s in STATIONS:
        folium.Circle(
            location=[s["lat"], s["lng"]],
            radius=500,
            color="#4fc3f7",
            weight=1.5,
            opacity=0.55,
            fill=True,
            fill_color="#4fc3f7",
            fill_opacity=0.07,
            tooltip=f"{s['name']} · 500m walking zone",
        ).add_to(buffer_fg)

    # ── Metro line polyline ────────────────────────────────────────────────────
    folium.PolyLine(
        [[s["lat"], s["lng"]] for s in STATIONS],
        color="#e84393",
        weight=4,
        opacity=0.85,
        tooltip="Metro Line 1",
    ).add_to(line_fg)

    # ── Station markers ────────────────────────────────────────────────────────
    for idx, s in enumerate(STATIONS):
        tier = get_tier(s["price"])
        price_label = format_price(s["price"])

        folium.CircleMarker(
            location=[s["lat"], s["lng"]],
            radius=10,
            color="white",
            weight=2.5,
            fill=True,
            fill_color=tier["marker_color"],
            fill_opacity=0.95,
            popup=make_popup(s, idx),
            tooltip=(
                f"<b>{s['name']}</b>"
                f"&nbsp;·&nbsp;{price_label}/m²"
                f"&nbsp;·&nbsp;<i>{tier['label']}</i>"
            ),
        ).add_to(station_fg)

    # Add feature groups to map in draw order
    heatmap_fg.add_to(m)
    buffer_fg.add_to(m)
    line_fg.add_to(m)
    station_fg.add_to(m)

    # ── Geocoder / search bar ──────────────────────────────────────────────────
    try:
        Geocoder(
            collapsed=False,
            position="topleft",
            add_marker=True,
        ).add_to(m)
    except Exception as exc:
        print(f"Geocoder unavailable: {exc}")

    # ── Floating map title ─────────────────────────────────────────────────────
    m.get_root().html.add_child(folium.Element("""
    <div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);
                z-index:2000;pointer-events:none;">
      <div style="background:rgba(255,255,255,0.95);backdrop-filter:blur(8px);
                  padding:10px 24px;border-radius:30px;
                  box-shadow:0 4px 20px rgba(0,0,0,0.14);
                  font-family:'Segoe UI',Arial,sans-serif;text-align:center;">
        <span style="font-size:15px;font-weight:800;color:#1a1a2e;letter-spacing:0.5px;">
          HCMC Metro Line 1
        </span>
        <span style="font-size:12px;color:#e84393;font-weight:700;margin:0 8px;">|</span>
        <span style="font-size:12px;color:#888;">
          Real Estate Price Map 2026
        </span>
      </div>
    </div>
    """))

    # ── Professional legend ────────────────────────────────────────────────────
    m.get_root().html.add_child(folium.Element("""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1500;
                background:rgba(255,255,255,0.97);backdrop-filter:blur(12px);
                padding:18px 20px;border-radius:14px;
                box-shadow:0 4px 24px rgba(0,0,0,0.16);
                font-family:'Segoe UI',Arial,sans-serif;
                min-width:230px;max-width:248px;
                border:1px solid rgba(0,0,0,0.06);">

      <!-- Title -->
      <div style="font-size:10px;font-weight:800;color:#1a1a2e;
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:2px;">
        Price Heatmap
      </div>
      <div style="font-size:11px;color:#aaa;margin-bottom:10px;">
        VND per m&sup2; &nbsp;&middot;&nbsp; 2026 Mock Data
      </div>

      <!-- Gradient bar -->
      <div style="height:10px;border-radius:6px;margin-bottom:5px;
                  background:linear-gradient(to right,
                    #313695,#74add1,#fee090,#f46d43,#d73027,#a50026);">
      </div>
      <div style="display:flex;justify-content:space-between;
                  font-size:9px;color:#bbb;letter-spacing:0.5px;margin-bottom:16px;">
        <span>LOW</span><span>HIGH</span>
      </div>

      <!-- Tier heading -->
      <div style="font-size:10px;font-weight:700;color:#555;
                  letter-spacing:1.5px;text-transform:uppercase;margin-bottom:9px;">
        Investment Tiers
      </div>

      <!-- T1 -->
      <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
        <span style="background:#a50026;width:12px;height:12px;border-radius:50%;
                     display:inline-block;margin-right:9px;flex-shrink:0;margin-top:2px;">
        </span>
        <div>
          <div style="font-size:11px;font-weight:700;color:#333;">
            Prime Asset &nbsp;<span style="color:#ccc;font-weight:400;">T1</span>
          </div>
          <div style="font-size:10px;color:#bbb;">&gt; 400M/m&sup2;</div>
        </div>
      </div>

      <!-- T2 -->
      <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
        <span style="background:#d73027;width:12px;height:12px;border-radius:50%;
                     display:inline-block;margin-right:9px;flex-shrink:0;margin-top:2px;">
        </span>
        <div>
          <div style="font-size:11px;font-weight:700;color:#333;">
            High Growth &nbsp;<span style="color:#ccc;font-weight:400;">T2</span>
          </div>
          <div style="font-size:10px;color:#bbb;">150M – 400M/m&sup2;</div>
        </div>
      </div>

      <!-- T3 -->
      <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
        <span style="background:#f46d43;width:12px;height:12px;border-radius:50%;
                     display:inline-block;margin-right:9px;flex-shrink:0;margin-top:2px;">
        </span>
        <div>
          <div style="font-size:11px;font-weight:700;color:#333;">
            Strong Value &nbsp;<span style="color:#ccc;font-weight:400;">T3</span>
          </div>
          <div style="font-size:10px;color:#bbb;">70M – 150M/m&sup2;</div>
        </div>
      </div>

      <!-- T4 -->
      <div style="display:flex;align-items:flex-start;margin-bottom:14px;">
        <span style="background:#4fc3f7;width:12px;height:12px;border-radius:50%;
                     display:inline-block;margin-right:9px;flex-shrink:0;margin-top:2px;">
        </span>
        <div>
          <div style="font-size:11px;font-weight:700;color:#333;">
            Emerging Zone &nbsp;<span style="color:#ccc;font-weight:400;">T4</span>
          </div>
          <div style="font-size:10px;color:#bbb;">&lt; 70M/m&sup2;</div>
        </div>
      </div>

      <hr style="border:none;border-top:1px solid #f0f0f0;margin:0 0 10px 0;">

      <!-- Map symbols -->
      <div style="display:flex;align-items:center;margin-bottom:6px;">
        <span style="background:#4fc3f7;width:22px;height:3px;display:inline-block;
                     margin-right:9px;border-radius:2px;opacity:0.55;flex-shrink:0;">
        </span>
        <span style="font-size:10px;color:#bbb;">500m walking zone</span>
      </div>
      <div style="display:flex;align-items:center;margin-bottom:12px;">
        <span style="background:#e84393;width:22px;height:3px;display:inline-block;
                     margin-right:9px;border-radius:2px;flex-shrink:0;">
        </span>
        <span style="font-size:10px;color:#bbb;">Metro Line 1 route</span>
      </div>

      <div style="text-align:center;font-size:9px;color:#ddd;letter-spacing:0.5px;">
        Click markers &nbsp;&middot;&nbsp; Toggle layers top-right
      </div>
    </div>
    """))

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    return m


if __name__ == "__main__":
    output_file = "hcmc_metro_heatmap.html"
    metro_map = build_map()
    metro_map.save(output_file)
    print(f"Saved -> {output_file}")
    print(f"Stations: {len(STATIONS)}")
    for s in STATIONS:
        t = get_tier(s["price"])
        print(f"  {s['name']:<20} {format_price(s['price']):<8}/m²  [{t['label']}]")
