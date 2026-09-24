import { useEffect, useMemo, useRef, useState } from "react";
import { fetchBoardMap, type BoardMapData } from "./api";
import boardImageUrl from "./assets/map/board.jpg";
import { PHOTO_HEX_SIZE, PHOTO_IMAGE_H, PHOTO_IMAGE_W, hexPoints, photoGridPositions, photoHexCenter } from "./hexGeometry";

// A compact, read-only-of-game-state version of MapTab's clickable board
// photo - no tile placement, no modal, just "click a hex, get its id back"
// - for embedding in forms elsewhere (CompaniesTab's home/destination
// pickers) that want the same click-to-pick affordance without pulling in
// everything else MapTab does.
type Props = {
  onPick: (hexId: string) => void;
  // hexId -> a short CSS-safe tag (e.g. "home", "destination") to
  // highlight that hex distinctly, so the picker can show where the
  // field(s) being edited currently point.
  highlights?: Record<string, string>;
};

export default function MapHexPicker({ onPick, highlights = {} }: Props) {
  const [mapData, setMapData] = useState<BoardMapData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const polygonRefs = useRef(new Map<string, SVGPolygonElement>());

  useEffect(() => {
    fetchBoardMap()
      .then(setMapData)
      .catch((e) => setLoadError((e as Error).message));
  }, []);

  const grid = useMemo(
    () => (mapData ? photoGridPositions(mapData.columns, Object.keys(highlights)) : []),
    [mapData, highlights]
  );

  const highlightedHexId = Object.keys(highlights)[0];
  useEffect(() => {
    if (!highlightedHexId) return;
    polygonRefs.current.get(highlightedHexId)?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  }, [highlightedHexId]);

  if (loadError) return <p className="error">{loadError}</p>;
  if (!mapData) return <p className="hint">Loading map...</p>;

  return (
    <div className="hex-picker-scroll">
      <div className="hex-picker-wrap">
        <img src={boardImageUrl} alt="1822 board map" className="hex-picker-image" />
        <svg className="hex-picker-overlay" viewBox={`0 0 ${PHOTO_IMAGE_W} ${PHOTO_IMAGE_H}`}>
          {grid.map(({ hexId, col, row }) => {
            const { x, y } = photoHexCenter(col, row);
            const highlight = highlights[hexId];
            return (
              <polygon
                key={hexId}
                ref={(el) => {
                  if (el) polygonRefs.current.set(hexId, el);
                  else polygonRefs.current.delete(hexId);
                }}
                points={hexPoints(x, y, PHOTO_HEX_SIZE)}
                className={`hex-picker-hex${highlight ? ` hex-picker-hex-${highlight}` : ""}`}
                onClick={() => onPick(hexId)}
              >
                <title>{hexId}</title>
              </polygon>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
