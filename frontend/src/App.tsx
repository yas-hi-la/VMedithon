import { useEffect, useRef, useState, useCallback, ReactNode } from 'react';
import {
  analyzeVariant,
  loadSavedVariant,
  retrieveEvidence,
  type EvidenceItem,
  type AnalysisResult,
  type RetrievedEvidence,
} from './api';

// ─── Realistic molecular DNA canvas ──────────────────────────────────────────

function DNACanvas({ analyzing }: { analyzing: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef({ analyzing, t: 0 });
  stateRef.current.analyzing = analyzing;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // Capture as non-null so inner functions can reference them without TS narrowing loss
    const cvs = canvas;
    const c = ctx;

    // W/H tracked as mutable refs — no offsetWidth read per frame
    let W = 0, H = 0;
    let animId: number;
    let last: number | null = null;
    let resizeTimer: ReturnType<typeof setTimeout>;

    function resize() {
      W = cvs.offsetWidth;
      H = cvs.offsetHeight;
      cvs.width  = W * devicePixelRatio;
      cvs.height = H * devicePixelRatio;
      // setTransform instead of scale — safe to call repeatedly without stacking
      c.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    }
    resize();

    // Debounce so rapid resize events don't flash the canvas mid-frame
    const ro = new ResizeObserver(() => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 40);
    });
    ro.observe(canvas);

    // Pre-allocated point buffers — reused every frame, no GC allocation
    const STEPS = 200;
    const x1 = new Float32Array(STEPS + 1);
    const y1 = new Float32Array(STEPS + 1);
    const x2 = new Float32Array(STEPS + 1);
    const y2 = new Float32Array(STEPS + 1);
    const z1 = new Float32Array(STEPS + 1); // depth (cos) for strand 1
    const fr = new Float32Array(STEPS + 1); // fraction along axis

    const TURNS = 6.5;
    const PAIR_EVERY = 10;
    const TAU = Math.PI * 2;

    c.lineCap = 'round';

    function draw(ts: number) {
      const dt = last === null ? 0 : Math.min((ts - last) / 1000, 0.05);
      last = ts;

      const s = stateRef.current;
      s.t += dt * (s.analyzing ? 0.5 : 0.2);

      c.clearRect(0, 0, W, H);

      // Diagonal axis: upper-right → lower-left along the right portion
      const ax0 = W * 0.91, ay0 = H * 0.02;
      const ax1 = W * 0.54, ay1 = H * 0.98;
      const adx = ax1 - ax0, ady = ay1 - ay0;
      const alen = Math.sqrt(adx * adx + ady * ady);
      const perpX = -ady / alen, perpY = adx / alen;
      const amp = Math.min(W * 0.14, 90);

      // Traveling pulse — smooth sine envelope
      const pulsePos = (s.t * 0.35) % 1;
      const pStr = s.analyzing ? 0.5 : 0.25;

      function pulse(frac: number) {
        const d = Math.min(Math.abs(frac - pulsePos), 1 - Math.abs(frac - pulsePos));
        return Math.max(0, 1 - d / 0.13) * pStr;
      }

      // Fill point buffers
      const tOffset = s.t * TAU;
      for (let i = 0; i <= STEPS; i++) {
        const f = i / STEPS;
        const phase = f * TURNS * TAU + tOffset;
        const cx = ax0 + f * adx;
        const cy = ay0 + f * ady;
        const sinP = Math.sin(phase);
        const cosP = Math.cos(phase);
        x1[i] = cx + sinP * amp * perpX;
        y1[i] = cy + sinP * amp * perpY;
        x2[i] = cx - sinP * amp * perpX;
        y2[i] = cy - sinP * amp * perpY;
        z1[i] = cosP;   // depth for strand1; strand2 depth = -cosP
        fr[i] = f;
      }

      // Draw one strand, all segments, depth-modulated alpha & width
      function drawStrand(
        sx: Float32Array, sy: Float32Array, zSign: 1 | -1,
        r: number, g: number, b: number,
      ) {
        for (let i = 0; i < STEPS; i++) {
          const depth = z1[i] * zSign; // -1=back, +1=front
          const d01 = (depth + 1) * 0.5;
          const a = d01 * 0.65 + 0.1 + pulse(fr[i]) * 0.35;
          const w = d01 * 2.0 + 0.7;
          c.beginPath();
          c.moveTo(sx[i], sy[i]);
          c.lineTo(sx[i + 1], sy[i + 1]);
          c.strokeStyle = `rgba(${r},${g},${b},${Math.min(a, 1).toFixed(2)})`;
          c.lineWidth = w;
          c.stroke();
        }
      }

      // Collect + depth-sort base pairs (back to front)
      type Pair = { i: number; z: number };
      const pairs: Pair[] = [];
      for (let i = 0; i <= STEPS; i += PAIR_EVERY) pairs.push({ i, z: z1[i] });
      pairs.sort((a, b) => a.z - b.z);

      function drawPairs(front: boolean) {
        for (const { i, z } of pairs) {
          if (front ? z < 0 : z >= 0) continue;
          const d01 = (z + 1) * 0.5;
          const pa = pulse(fr[i]);
          // Rod
          const rodA = d01 * 0.35 + 0.12 + pa * 0.25;
          c.beginPath();
          c.moveTo(x1[i], y1[i]);
          c.lineTo(x2[i], y2[i]);
          c.strokeStyle = `rgba(100,170,160,${rodA.toFixed(2)})`;
          c.lineWidth = 0.8 + d01 * 0.4;
          c.stroke();
          // Nodes
          const nodeR = 1.8 + d01 * 2.0;
          const na1 = Math.min(d01 * 0.7 + 0.15 + pa, 1);
          const na2 = Math.min(d01 * 0.6 + 0.12 + pa, 1);
          c.beginPath();
          c.arc(x1[i], y1[i], nodeR, 0, TAU);
          c.fillStyle = `rgba(57,124,120,${na1.toFixed(2)})`;
          c.fill();
          c.beginPath();
          c.arc(x2[i], y2[i], nodeR, 0, TAU);
          c.fillStyle = `rgba(111,159,155,${na2.toFixed(2)})`;
          c.fill();
        }
      }

      // Render order: back strands → back pairs → front strands → front pairs
      drawStrand(x1, y1,  1, 57, 124, 120);
      drawStrand(x2, y2, -1, 111, 159, 155);
      drawPairs(false);
      drawStrand(x1, y1,  1, 57, 124, 120);
      drawStrand(x2, y2, -1, 111, 159, 155);
      drawPairs(true);

      animId = requestAnimationFrame(draw);
    }

    animId = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animId);
      clearTimeout(resizeTimer);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none select-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────

function Header() {
  return (
    <header className="relative z-10 flex items-center justify-between px-8 py-4 border-b" style={{ borderColor: 'var(--border)', background: 'rgba(246,248,247,0.9)', backdropFilter: 'blur(8px)' }}>
      <div className="flex items-center gap-2.5">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <path d="M11 1C11 1 8 4.5 8 8C8 11.5 11 11.5 11 11.5C11 11.5 14 11.5 14 15C14 18.5 11 21 11 21"
            stroke="#397C78" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M11 1C11 1 14 4.5 14 8C14 11.5 11 11.5 11 11.5C11 11.5 8 11.5 8 15C8 18.5 11 21 11 21"
            stroke="#6F9F9B" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="8" cy="8" r="1.2" fill="#397C78" />
          <circle cx="14" cy="15" r="1.2" fill="#6F9F9B" />
        </svg>
        <span className="font-display font-bold text-base tracking-tight" style={{ color: 'var(--foreground)' }}>
          VUSIGHT
        </span>
      </div>

      <nav className="hidden md:flex items-center gap-7 text-sm" style={{ color: 'var(--muted-foreground)' }}>
        <a href="#" className="hover:text-[#397C78] transition-colors">Variant Analysis</a>
        <a href="#" className="hover:text-[#397C78] transition-colors">Evidence</a>
        <a href="#" className="hover:text-[#397C78] transition-colors">About</a>
      </nav>

      <div className="flex items-center gap-2 text-xs font-mono" style={{ color: '#6F9F9B' }}>
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" style={{ opacity: 0.8 }} />
        Decision Support
      </div>
    </header>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <div className="relative pt-16 pb-10 px-8 md:px-12">
      <div className="max-w-xl">
        <div className="inline-flex items-center gap-2 text-xs font-mono mb-6 px-3 py-1.5 rounded-full"
          style={{ background: '#eaf1f0', color: '#397C78', border: '1px solid #c8dbd9' }}>
          ACMG/AMP Framework · Hereditary Cancer Variants
        </div>
        <h1 className="font-display font-bold text-4xl md:text-5xl tracking-tight mb-4 leading-tight"
          style={{ color: 'var(--foreground)' }}>
          Variant<br />Intelligence
        </h1>
        <p className="text-base leading-relaxed max-w-sm" style={{ color: 'var(--muted-foreground)' }}>
          Transparent evidence-driven analysis for hereditary cancer variants.
        </p>
      </div>
    </div>
  );
}

// ─── Evidence card ────────────────────────────────────────────────────────────

const CRITERIA  = ['PS3', 'PM2', 'PP3', 'BS1', 'BP4'];
const STRENGTHS = ['supporting', 'moderate', 'strong', 'very_strong', 'stand_alone'];
const DIRECTIONS = ['pathogenic', 'benign'];

function EvidenceCard({
  item,
  index,
  onChange,
  onRemove,
}: {
  item: EvidenceItem;
  index: number;
  onChange: (id: string, field: keyof EvidenceItem, val: string) => void;
  onRemove: (id: string) => void;
}) {
  return (
    <div className="evidence-card rounded-xl p-4" style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono" style={{ color: 'var(--muted-foreground)' }}>
          Record #{index + 1}
        </span>
        <button
          onClick={() => onRemove(item.id)}
          className="text-xs px-2 py-0.5 rounded transition-colors hover:text-red-600"
          style={{ color: 'var(--muted-foreground)' }}
          aria-label="Remove evidence"
        >
          Remove
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
        {([
          { label: 'Criterion', field: 'criterion' as const, options: CRITERIA },
          { label: 'Strength',  field: 'strength'  as const, options: STRENGTHS },
          { label: 'Direction', field: 'direction' as const, options: DIRECTIONS },
        ]).map(({ label, field, options }) => (
          <div key={field}>
            <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--muted-foreground)' }}>{label}</label>
            <select
              value={item[field]}
              onChange={(e) => onChange(item.id, field, e.target.value)}
              className="input-field w-full rounded-lg px-3 py-2 text-sm"
            >
              {!options.includes(item[field]) && <option value="">Select {label.toLowerCase()}</option>}
              {options.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--muted-foreground)' }}>Source</label>
          <input type="text" value={item.source_name}
            onChange={(e) => onChange(item.id, 'source_name', e.target.value)}
            placeholder="e.g. ClinVar, functional study"
            className="input-field w-full rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--muted-foreground)' }}>Reference</label>
          <input type="text" value={item.source_ref}
            onChange={(e) => onChange(item.id, 'source_ref', e.target.value)}
            placeholder="e.g. PMID:12345678"
            className="input-field w-full rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <div>
        <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--muted-foreground)' }}>Summary</label>
        <textarea rows={2} value={item.summary}
          onChange={(e) => onChange(item.id, 'summary', e.target.value)}
          placeholder="What does this evidence demonstrate?"
          className="input-field w-full rounded-lg px-3 py-2 text-sm resize-none" />
      </div>
    </div>
  );
}

function RetrievedEvidencePanel({
  items,
  status,
  message,
  onUse,
  usedIds,
}: {
  items: RetrievedEvidence[];
  status: 'idle' | 'loading' | 'found' | 'not_found' | 'error';
  message: string;
  onUse: (item: RetrievedEvidence) => void;
  usedIds: Set<string>;
}) {
  if (status === 'idle') return null;

  return (
    <div className="rounded-xl p-4 mb-4" style={{ background: '#f8faf9', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: 'var(--foreground)' }}>ClinVar public evidence</span>
        {status === 'loading' && <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>Retrieving…</span>}
      </div>
      {status === 'loading' && (
        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>Checking ClinVar for matching public records.</p>
      )}
      {status === 'not_found' && (
        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>No matching public evidence found.</p>
      )}
      {status === 'error' && (
        <p className="text-xs" style={{ color: '#9b3d2c' }}>{message}</p>
      )}
      {status === 'found' && (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="rounded-lg p-3" style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between gap-3 mb-1">
                <span className="criterion-tag" style={{ background: '#eaf1f0', color: '#397C78' }}>Source record</span>
                <button
                  onClick={() => onUse(item)}
                  disabled={usedIds.has(item.id)}
                  className="btn-secondary rounded-lg px-2.5 py-1 text-xs font-medium"
                >
                  {usedIds.has(item.id) ? 'Added for review' : 'Review in analysis'}
                </button>
              </div>
              <p className="text-sm mb-1" style={{ color: 'var(--foreground)' }}>{item.summary}</p>
              <div className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                ClinVar{item.source_ref && <> &middot; <span className="font-mono">{item.source_ref}</span></>}
              </div>
              <p className="text-[11px] mt-2" style={{ color: 'var(--muted-foreground)' }}>
                Not mapped to an ACMG criterion. Select the criterion, strength, and direction before analyzing.
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Loading state ────────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="surface-card rounded-2xl p-10 text-center">
      <div className="flex justify-center mb-5">
        <svg width="36" height="60" viewBox="0 0 36 60" fill="none" aria-hidden="true">
          <path d="M18 0C18 0 12 8 12 16C12 24 18 24 18 24C18 24 24 24 24 32C24 40 18 48 18 48"
            stroke="#397C78" strokeWidth="1.8" strokeLinecap="round" opacity="0.7">
            <animateTransform attributeName="transform" type="translate" values="0 0;0 -6;0 0" dur="1.8s" repeatCount="indefinite" />
          </path>
          <path d="M18 0C18 0 24 8 24 16C24 24 18 24 18 24C18 24 12 24 12 32C12 40 18 48 18 48"
            stroke="#6F9F9B" strokeWidth="1.8" strokeLinecap="round" opacity="0.7">
            <animateTransform attributeName="transform" type="translate" values="0 0;0 -6;0 0" dur="1.8s" repeatCount="indefinite" />
          </path>
          <circle cx="12" cy="16" r="2" fill="#397C78" opacity="0.8">
            <animate attributeName="r" values="2;3.5;2" dur="0.9s" repeatCount="indefinite" />
          </circle>
          <circle cx="24" cy="32" r="2" fill="#6F9F9B" opacity="0.8">
            <animate attributeName="r" values="2;3.5;2" dur="0.9s" begin="0.45s" repeatCount="indefinite" />
          </circle>
        </svg>
      </div>
      <h3 className="font-display font-semibold text-lg mb-2" style={{ color: 'var(--foreground)' }}>
        Analyzing variant
      </h3>
      <p className="text-sm mb-5" style={{ color: 'var(--muted-foreground)' }}>
        Evaluating structured evidence and decision rules...
      </p>
      <div className="dot-loader flex justify-center gap-1.5">
        <span /><span /><span />
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="surface-card rounded-2xl p-10 text-center">
      <div className="flex justify-center mb-4">
        <svg width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden="true">
          <circle cx="22" cy="22" r="21" stroke="#c8dbd9" strokeWidth="1" strokeDasharray="3 2.5" />
          <path d="M22 10C22 10 17 15 17 20C17 25 22 25 22 25C22 25 27 25 27 30C27 35 22 38 22 38"
            stroke="#6F9F9B" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
          <path d="M22 10C22 10 27 15 27 20C27 25 22 25 22 25C22 25 17 25 17 30C17 35 22 38 22 38"
            stroke="#397C78" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
        </svg>
      </div>
      <h3 className="font-display font-semibold text-base mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
        Ready for analysis
      </h3>
      <p className="text-sm" style={{ color: '#a8bcba' }}>
        Enter a gene, HGVS notation, and optional structured evidence to begin.
      </p>
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="surface-card rounded-2xl p-8 text-center" style={{ borderColor: '#e8d5cf' }}>
      <div className="flex justify-center mb-3">
        <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ background: '#fef6f2', border: '1px solid #f0cfc4' }}>
          <span className="text-base" aria-hidden="true">!</span>
        </div>
      </div>
      <h3 className="font-display font-semibold text-base mb-1.5" style={{ color: '#9b3d2c' }}>
        Analysis could not be completed
      </h3>
      <p className="text-sm mb-5 max-w-sm mx-auto" style={{ color: 'var(--muted-foreground)' }}>
        {message}
      </p>
      <button onClick={onRetry} className="btn-secondary rounded-lg px-5 py-2 text-sm font-medium">
        Try Again
      </button>
    </div>
  );
}

// ─── Classification helpers ───────────────────────────────────────────────────

function badgeClass(c: string) {
  const m: Record<string, string> = {
    'Pathogenic':            'badge-pathogenic',
    'Likely Pathogenic':     'badge-likely-pathogenic',
    'Uncertain Significance':'badge-uncertain',
    'Likely Benign':         'badge-likely-benign',
    'Benign':                'badge-benign',
    'Conflicting':           'badge-conflicting',
    'Insufficient Evidence': 'badge-insufficient',
  };
  return m[c] ?? 'badge-insufficient';
}

function classificationLabel(c: string) {
  const sym: Record<string, string> = {
    'Pathogenic':            'P',
    'Likely Pathogenic':     'LP',
    'Uncertain Significance':'VUS',
    'Likely Benign':         'LB',
    'Benign':                'B',
    'Conflicting':           'CF',
    'Insufficient Evidence': 'IE',
  };
  return sym[c] ?? '—';
}

// ─── Result card ──────────────────────────────────────────────────────────────

function ResultCard({ result }: { result: AnalysisResult }) {
  const [traceOpen, setTraceOpen] = useState(true);
  const [rulesOpen, setRulesOpen] = useState(true);

  return (
    <div className="result-appear space-y-4">
      {/* Classification */}
      <div className="surface-card rounded-2xl p-6">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
          <div>
            <h2 className="font-display font-bold text-lg mb-0.5" style={{ color: 'var(--foreground)' }}>Analysis Result</h2>
            <div className="text-xs font-mono flex items-center gap-2" style={{ color: 'var(--muted-foreground)' }}>
              <span>{result.gene}</span>
              <span>&middot;</span>
              <span>{result.hgvs_notation}</span>
            </div>
          </div>
          <div className={`px-4 py-2.5 rounded-xl text-center ${badgeClass(result.classification)}`}>
            <div className="font-mono text-xs mb-0.5 opacity-60">{classificationLabel(result.classification)}</div>
            <div className="font-display font-bold text-base leading-tight">{result.classification}</div>
            <div className="text-[10px] mt-1 opacity-60">Status: {result.status}</div>
          </div>
        </div>

        {result.reasoning && (
          <p className="text-sm leading-relaxed py-3 px-4 rounded-lg"
            style={{ color: 'var(--muted-foreground)', background: 'var(--muted)', borderLeft: '2px solid #c8dbd9' }}>
            {result.reasoning}
          </p>
        )}

        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
          {[
            { label: 'Gene', value: result.gene },
            { label: 'HGVS', value: result.hgvs_notation },
            { label: 'Criteria', value: `${result.criteria_considered.length} submitted` },
            { label: 'Satisfied', value: `${result.satisfied_rules.length} rules` },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg p-3" style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
              <div className="text-xs mb-0.5" style={{ color: 'var(--muted-foreground)' }}>{label}</div>
              <div className="font-mono text-xs font-medium" style={{ color: 'var(--foreground)' }}>{value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence & Decision Trace */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <button
          onClick={() => setTraceOpen((o) => !o)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-[#f8faf9] transition-colors text-left"
        >
          <span className="font-display font-semibold text-sm" style={{ color: 'var(--foreground)' }}>
            Evidence &amp; Decision Trace
          </span>
          <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{traceOpen ? '▲' : '▼'}</span>
        </button>

        {traceOpen && (
          <div className="px-6 pb-6">
            {result.evidence_trace.length === 0 ? (
              <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>No evidence items submitted.</p>
            ) : (
              <div className="space-y-0">
                {result.evidence_trace.map((ev, idx) => (
                  <div key={ev.id} className="flex gap-4">
                    {/* Timeline */}
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full border flex items-center justify-center flex-shrink-0 mt-1"
                        style={{
                          borderColor: ev.direction === 'pathogenic' ? '#e8b8a8' : '#b8ddc8',
                          background: ev.direction === 'pathogenic' ? '#fef6f2' : '#f2faf6',
                        }}>
                        <span className="text-[10px] font-mono font-medium"
                          style={{ color: ev.direction === 'pathogenic' ? '#b34b00' : '#2e6b52' }}>
                          {idx + 1}
                        </span>
                      </div>
                      {idx < result.evidence_trace.length - 1 && (
                        <div className="w-px flex-1 my-1" style={{ background: 'var(--border)' }} />
                      )}
                    </div>

                    <div className="flex-1 rounded-xl p-4 mb-3"
                      style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
                      <div className="flex flex-wrap items-center gap-1.5 mb-2">
                        <span className="criterion-tag">{ev.criterion}</span>
                        <span className="strength-tag">{ev.strength}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${ev.direction === 'pathogenic' ? 'dir-pathogenic' : 'dir-benign'}`}>
                          {ev.direction}
                        </span>
                      </div>
                      <p className="text-sm mb-1.5" style={{ color: 'var(--foreground)' }}>
                        {ev.summary || <span style={{ color: 'var(--muted-foreground)', fontStyle: 'italic' }}>No summary provided.</span>}
                      </p>
                      {ev.source_name && (
                        <div className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                          Source: <span style={{ color: '#397C78' }}>{ev.source_name}</span>
                          {ev.source_ref && <> &middot; <span className="font-mono">{ev.source_ref}</span></>}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Rule evaluation */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <button
          onClick={() => setRulesOpen((o) => !o)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-[#f8faf9] transition-colors text-left"
        >
          <span className="font-display font-semibold text-sm" style={{ color: 'var(--foreground)' }}>Rule Evaluation</span>
          <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{rulesOpen ? '▲' : '▼'}</span>
        </button>

        {rulesOpen && (
          <div className="px-6 pb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
              {/* Satisfied */}
              <div>
                <div className="text-xs font-medium mb-2.5" style={{ color: '#2e6b52' }}>
                  Satisfied ({result.satisfied_rules.length})
                </div>
                <div className="space-y-2">
                  {result.satisfied_rules.length === 0
                    ? <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>None</p>
                    : result.satisfied_rules.map((r) => (
                      <div key={r.rule + r.description} className="rounded-lg p-3"
                        style={{ background: '#f2faf6', border: '1px solid #b8ddc8' }}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="criterion-tag" style={{ background: '#e2f5eb', color: '#2e6b52', borderColor: '#b8ddc8' }}>{r.rule}</span>
                          <span className="text-xs" style={{ color: '#2e6b52' }}>satisfied</span>
                        </div>
                        <p className="text-xs" style={{ color: '#5a7a6a' }}>{r.description}</p>
                      </div>
                    ))}
                </div>
              </div>
              {/* Unsupported */}
              <div>
                <div className="text-xs font-medium mb-2.5" style={{ color: 'var(--muted-foreground)' }}>
                  Not met ({result.unsupported_rules.length})
                </div>
                <div className="space-y-2">
                  {result.unsupported_rules.length === 0
                    ? <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>None</p>
                    : result.unsupported_rules.map((r) => (
                      <div key={r.rule + r.description} className="rounded-lg p-3"
                        style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="criterion-tag" style={{ opacity: 0.55 }}>{r.rule}</span>
                          <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>not met</span>
                        </div>
                        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{r.description}</p>
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* Scientific reasoning pathway */}
            <div className="rounded-xl p-4" style={{ background: 'var(--muted)', border: '1px solid var(--border)' }}>
              <div className="text-xs font-medium mb-3" style={{ color: 'var(--muted-foreground)' }}>Reasoning pathway</div>
              <div className="flex flex-col gap-2 text-xs">
                {/* Evidence node */}
                <div className="flex items-start gap-2">
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: '#eaf1f0', border: '1px solid #c8dbd9' }}>
                    <span style={{ color: '#397C78', fontSize: '9px', fontWeight: 700 }}>E</span>
                  </div>
                  <div>
                    <div className="font-medium mb-1" style={{ color: 'var(--foreground)' }}>Evidence submitted</div>
                    <div className="flex flex-wrap gap-1">
                      {result.evidence_trace.length === 0
                        ? <span style={{ color: 'var(--muted-foreground)' }}>None</span>
                        : result.evidence_trace.map((e) => (
                          <span key={e.id} className="criterion-tag">{e.criterion}</span>
                        ))}
                    </div>
                  </div>
                </div>

                {/* Connector */}
                <div className="ml-2.5 pl-4" style={{ borderLeft: '1px dashed #c8dbd9' }}>
                  <div className="flex flex-wrap gap-1 py-1">
                    {result.satisfied_rules.map((r) => (
                      <span key={r.rule} className="px-2 py-0.5 rounded-full"
                        style={{ background: '#f2faf6', color: '#2e6b52', border: '1px solid #b8ddc8', fontSize: '11px' }}>
                        {r.rule} ✓
                      </span>
                    ))}
                  </div>
                </div>

                {/* Classification node */}
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: '#eaf1f0', border: '1px solid #c8dbd9' }}>
                    <span style={{ color: '#397C78', fontSize: '9px', fontWeight: 700 }}>C</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full font-display font-semibold ${badgeClass(result.classification)}`}
                    style={{ fontSize: '12px' }}>
                    {result.classification}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

type AppState = 'idle' | 'loading' | 'result' | 'error';

// Smoothly cross-fades between states: fades out, swaps content, fades in
function TransitionPanel({ stateKey, children }: { stateKey: string; children: ReactNode }) {
  const [opacity, setOpacity] = useState(1);
  const [translateY, setTranslateY] = useState(0);
  const [rendered, setRendered] = useState<ReactNode>(children);
  const shownKey = useRef(stateKey);
  const nextChildren = useRef(children);
  const rafHandle = useRef<number>(0);
  const timerHandle = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (stateKey === shownKey.current) return;
    shownKey.current = stateKey;
    nextChildren.current = children;

    // Step 1: fade out
    setOpacity(0);
    setTranslateY(6);

    // Step 2: after fade-out completes, swap content while invisible
    timerHandle.current = setTimeout(() => {
      setRendered(nextChildren.current);
      // Step 3: two rAF ticks so the browser paints the new content at opacity 0
      // before we start the fade-in transition
      rafHandle.current = requestAnimationFrame(() => {
        rafHandle.current = requestAnimationFrame(() => {
          setOpacity(1);
          setTranslateY(0);
        });
      });
    }, 180);

    return () => {
      if (timerHandle.current) clearTimeout(timerHandle.current);
      cancelAnimationFrame(rafHandle.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stateKey]);

  return (
    <div style={{
      opacity,
      transform: `translateY(${translateY}px)`,
      transition: opacity === 1
        ? 'opacity 0.28s ease, transform 0.28s ease'
        : 'opacity 0.18s ease, transform 0.18s ease',
      minHeight: '160px',
    }}>
      {rendered}
    </div>
  );
}

function uid() { return Math.random().toString(36).slice(2, 10); }

function newEvidence(): EvidenceItem {
  return { id: uid(), criterion: 'PS3', strength: 'moderate', direction: 'pathogenic', source_name: '', source_ref: '', summary: '' };
}

export default function App() {
  const [gene, setGene]       = useState('');
  const [hgvs, setHgvs]       = useState('');
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [appState, setAppState] = useState<AppState>('idle');
  const [result, setResult]   = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [validErr, setValidErr] = useState('');
  const [retrievedEvidence, setRetrievedEvidence] = useState<RetrievedEvidence[]>([]);
  const [retrievalState, setRetrievalState] = useState<'idle' | 'loading' | 'found' | 'not_found' | 'error'>('idle');
  const [retrievalMessage, setRetrievalMessage] = useState('');
  const [usedRetrievedIds, setUsedRetrievedIds] = useState<Set<string>>(new Set());

  const addEvidence    = () => setEvidence((p) => [...p, newEvidence()]);
  const removeEvidence = (id: string) => setEvidence((p) => p.filter((e) => e.id !== id));
  const updateEvidence = (id: string, field: keyof EvidenceItem, val: string) =>
    setEvidence((p) => p.map((e) => (e.id === id ? { ...e, [field]: val } : e)));

  const handleRetrieveEvidence = useCallback(async () => {
    if (!gene.trim() || !hgvs.trim()) {
      setValidErr('Enter a gene and HGVS notation first.');
      return;
    }
    setValidErr('');
    setRetrievalState('loading');
    setRetrievalMessage('');
    try {
      const result = await retrieveEvidence(gene.trim(), hgvs.trim());
      setRetrievedEvidence(result.evidence);
      setRetrievalState(result.status);
      setRetrievalMessage(result.message);
      setUsedRetrievedIds(new Set());
    } catch (e) {
      setRetrievedEvidence([]);
      setRetrievalState('error');
      setRetrievalMessage(e instanceof Error ? e.message : 'Unable to retrieve public evidence.');
    }
  }, [gene, hgvs]);

  const handleUseRetrievedEvidence = (item: RetrievedEvidence) => {
    setEvidence((current) => [...current, {
      id: item.id,
      criterion: '',
      strength: '',
      direction: '',
      source_name: item.source_name,
      source_ref: item.source_ref,
      summary: item.summary,
    }]);
    setUsedRetrievedIds((current) => new Set(current).add(item.id));
  };

  const handleLoadSaved = useCallback(async () => {
    if (!gene.trim() || !hgvs.trim()) {
      setValidErr('Enter a gene and HGVS notation first.');
      return;
    }
    setAppState('loading');
    try {
      const saved = await loadSavedVariant(gene.trim(), hgvs.trim());
      setAppState('idle');
      if (saved?.evidence?.length) {
        setEvidence(saved.evidence);
        setValidErr('');
      } else {
        setValidErr('No saved evidence found for this variant.');
      }
    } catch (e) {
      setAppState('idle');
      setValidErr(e instanceof Error ? e.message : 'Unable to load saved evidence.');
    }
  }, [gene, hgvs]);

  const handleAnalyze = useCallback(async () => {
    setValidErr('');
    if (!gene.trim()) { setValidErr('Please enter a gene symbol (e.g. BRCA1).'); return; }
    if (!hgvs.trim()) { setValidErr('Please enter an HGVS notation (e.g. c.5266dupC).'); return; }
    setAppState('loading');
    setResult(null);
    try {
      const res = await analyzeVariant({ gene: gene.trim(), hgvs_notation: hgvs.trim(), evidence });
      setResult(res);
      setAppState('result');
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'An unexpected error occurred.');
      setAppState('error');
    }
  }, [gene, hgvs, evidence]);

  const handleRetry = () => { setAppState('idle'); setErrorMsg(''); };

  return (
    <div className="min-h-full" style={{ background: 'var(--background)' }}>
      {/* DNA helix — behind everything, right side, diagonal */}
      <DNACanvas analyzing={appState === 'loading'} />

      <div className="relative z-10 flex flex-col min-h-screen">
        <Header />

        <main className="flex-1 max-w-2xl w-full mx-auto px-4 md:px-0">
          <Hero />

          <div className="space-y-4 pb-20 px-4 md:px-0">
            {/* Variant input */}
            <div className="surface-card rounded-2xl p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-display font-bold text-base" style={{ color: 'var(--foreground)' }}>
                  Analyze a Variant
                </h2>
                <button onClick={handleLoadSaved} className="btn-secondary rounded-lg px-3 py-1.5 text-xs font-medium">
                  Load Saved Evidence
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-2">
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>Gene</label>
                  <input type="text" value={gene}
                    onChange={(e) => { setGene(e.target.value); setValidErr(''); }}
                    placeholder="e.g. BRCA1"
                    className="input-field w-full rounded-lg px-3 py-2.5 text-sm font-mono" />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>HGVS notation</label>
                  <input type="text" value={hgvs}
                    onChange={(e) => { setHgvs(e.target.value); setValidErr(''); }}
                    placeholder="e.g. c.5266dupC"
                    className="input-field w-full rounded-lg px-3 py-2.5 text-sm font-mono" />
                </div>
              </div>
              <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                Enter the variant using HGVS notation.
              </p>

              {validErr && (
                <div className="mt-3 text-xs px-3 py-2 rounded-lg"
                  style={{ background: '#fef6f2', border: '1px solid #f0cfc4', color: '#9b3d2c' }}>
                  {validErr}
                </div>
              )}
            </div>

            {/* Evidence */}
            <div className="surface-card rounded-2xl p-6">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-display font-bold text-base" style={{ color: 'var(--foreground)' }}>Evidence</h2>
                <div className="flex items-center gap-2">
                  <button onClick={handleRetrieveEvidence} disabled={retrievalState === 'loading'}
                    className="btn-secondary rounded-lg px-3 py-1.5 text-xs font-medium">
                    {retrievalState === 'loading' ? 'Retrieving…' : 'Retrieve Evidence'}
                  </button>
                  <button onClick={addEvidence}
                    className="btn-secondary rounded-lg px-3 py-1.5 text-xs font-medium flex items-center gap-1">
                    <span>+</span> Add Evidence
                  </button>
                </div>
              </div>
              <p className="text-xs mb-4" style={{ color: 'var(--muted-foreground)' }}>
                Add structured evidence used in the analysis.
              </p>
              <RetrievedEvidencePanel
                items={retrievedEvidence}
                status={retrievalState}
                message={retrievalMessage}
                onUse={handleUseRetrievedEvidence}
                usedIds={usedRetrievedIds}
              />
              <div className="space-y-3">
                {evidence.length === 0 ? (
                  <div className="text-center py-6 rounded-xl"
                    style={{ border: '1px dashed var(--border)', background: 'var(--muted)' }}>
                    <p className="text-xs" style={{ color: '#a8bcba' }}>
                      No evidence added. Analysis will proceed on variant identity alone.
                    </p>
                  </div>
                ) : (
                  evidence.map((item, idx) => (
                    <EvidenceCard key={item.id} item={item} index={idx}
                      onChange={updateEvidence} onRemove={removeEvidence} />
                  ))
                )}
              </div>
            </div>

            {/* Analyze button */}
            <button
              onClick={handleAnalyze}
              disabled={appState === 'loading'}
              className="btn-primary w-full py-3.5 rounded-xl text-sm"
            >
              <span style={{ transition: 'opacity 0.15s ease', opacity: appState === 'loading' ? 0.7 : 1 }}>
                {appState === 'loading' ? 'Analyzing…' : 'Analyze Variant'}
              </span>
            </button>

            {/* Result area — smoothly cross-fades between states */}
            <TransitionPanel stateKey={appState}>
              {appState === 'loading' && <LoadingState />}
              {appState === 'idle' && <EmptyState />}
              {appState === 'error' && <ErrorState message={errorMsg} onRetry={handleRetry} />}
              {appState === 'result' && result && <ResultCard result={result} />}
            </TransitionPanel>
          </div>
        </main>

        <footer className="relative z-10 text-center py-5 text-xs border-t"
          style={{ borderColor: 'var(--border)', color: '#a8bcba' }}>
          VUSIGHT &middot; Hereditary Cancer Variant Decision Support &middot; Research use only
        </footer>
      </div>
    </div>
  );
}
