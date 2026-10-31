import { useEffect, useRef, useState } from 'react'
import './App.css'

const PHOTOS = [
  { id: 1, name: 'IMG_1042.jpg', kind: 'photo', hue: 210 },
  { id: 2, name: 'Screen Shot 2026-10-28 at 9.14.03 AM.png', kind: 'screenshot', hue: 0 },
  { id: 3, name: 'IMG_1043.jpg', kind: 'photo', hue: 32 },
  { id: 4, name: 'IMG_1042-copy.jpg', kind: 'duplicate', hue: 210 },
  { id: 5, name: 'Beach_0917.jpg', kind: 'photo', hue: 160 },
  { id: 6, name: 'Screenshot 2026-10-30 at 14.02.51.png', kind: 'screenshot', hue: 0 },
  { id: 7, name: 'Dinner_Rooftop.jpg', kind: 'photo', hue: 275 },
  { id: 8, name: 'Family_Christmas.tif', kind: 'photo', hue: 8 },
]

const VERDICTS = ['keep', 'noise', 'skip']

function photoStyle(photo) {
  if (photo.kind === 'screenshot') {
    return {
      background:
        'linear-gradient(160deg, #f4f5f7 0%, #e8eaee 55%, #dfe2e7 100%)',
    }
  }
  return {
    background: `linear-gradient(${140 + photo.id * 17}deg,
      hsl(${photo.hue} 26% 70%) 0%,
      hsl(${(photo.hue + 40) % 360} 24% 54%) 55%,
      hsl(${(photo.hue + 300) % 360} 18% 38%) 100%)`,
  }
}

function ReviewDemo() {
  const [index, setIndex] = useState(0)
  const [marks, setMarks] = useState({})
  const cardRef = useRef(null)

  const current = PHOTOS[index]
  const counts = {
    keep: Object.values(marks).filter((v) => v === 'keep').length,
    noise: Object.values(marks).filter((v) => v === 'noise').length,
  }

  const advance = () => setIndex((i) => Math.min(i + 1, PHOTOS.length - 1))
  const goBack = () => setIndex((i) => Math.max(i - 1, 0))

  const mark = (verdict) => {
    if (verdict === 'skip') {
      advance()
      return
    }
    setMarks((m) => ({ ...m, [current.id]: verdict }))
    advance()
  }

  useEffect(() => {
    const onKey = (e) => {
      const k = e.key.toLowerCase()
      if (k === 'k') mark('keep')
      else if (k === 'n') mark('noise')
      else if (k === 's') mark('skip')
      else if (e.key === 'ArrowRight') advance()
      else if (e.key === 'ArrowLeft') goBack()
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [current])

  const verdict = marks[current.id]

  return (
    <div className="demo" ref={cardRef}>
      <div className="demo-bar">
        <span className="demo-dot" />
        <span className="demo-title">Sift — Review</span>
        <span className="demo-counts">
          <span className="chip chip-keep">Keep {counts.keep}</span>
          <span className="chip chip-noise">Noise {counts.noise}</span>
        </span>
      </div>

      <div className={`demo-stage ${current.kind}`}>
        <div className="demo-photo" style={photoStyle(current)}>
          {current.kind === 'screenshot' && (
            <div className="fake-shot">
              <div className="fake-shot-bar" />
              <div className="fake-shot-row" />
              <div className="fake-shot-row short" />
              <div className="fake-shot-row" />
            </div>
          )}
          {current.kind === 'duplicate' && (
            <span className="dup-badge">near-duplicate of #1</span>
          )}
        </div>
        {verdict && (
          <span className={`verdict verdict-${verdict}`}>
            {verdict === 'keep' ? 'K · Keep' : 'N · Noise'}
          </span>
        )}
      </div>

      <div className="demo-meta">
        <span className="demo-filename">{current.name}</span>
        <span className="demo-pos">
          {index + 1} / {PHOTOS.length}
        </span>
      </div>

      <div className="demo-keys">
        <button className="key-btn key-keep" onClick={() => mark('keep')}>
          <kbd>K</kbd> Keep
        </button>
        <button className="key-btn" onClick={() => mark('noise')}>
          <kbd>N</kbd> Noise
        </button>
        <button className="key-btn" onClick={() => mark('skip')}>
          <kbd>S</kbd> Skip
        </button>
        <span className="key-hint">← → to move</span>
      </div>

      <div className="demo-strip">
        {PHOTOS.map((p, i) => (
          <button
            key={p.id}
            className={`strip-tile ${i === index ? 'active' : ''} ${
              marks[p.id] ? `marked-${marks[p.id]}` : ''
            }`}
            style={photoStyle(p)}
            onClick={() => setIndex(i)}
            aria-label={p.name}
          />
        ))}
      </div>
    </div>
  )
}

const STEPS = [
  {
    n: '01',
    title: 'Scan a folder',
    body: 'Sift indexes JPEG, PNG, WebP, GIF, and TIFF files where they already live. Scanning only reads — nothing moves, nothing is deleted.',
    cmd: 'sift scan ~/Pictures',
  },
  {
    n: '02',
    title: 'Review at speed',
    body: 'One photo at a time. K keeps, N discards, arrows move. Screenshots are suggested as noise; near-duplicates are flagged side by side.',
    cmd: 'sift app',
  },
  {
    n: '03',
    title: 'Trash or move — on confirm',
    body: 'Nothing is removed until you say so. Trash and Move both ask first, and near-duplicate copies can go together while the keeper stays.',
    cmd: '⌘ + confirm',
  },
]

const FEATURES = [
  {
    title: 'Local-first, always',
    body: 'The index lives at ~/Library/Application Support/Sift with mode 0600. No account, no cloud, no telemetry — scanning reads files and stops there.',
  },
  {
    title: 'Near-duplicate finder',
    body: 'A 64-bit difference hash groups photos that differ by at most 8 bits, so the burst shots collapse into one decision instead of twelve.',
  },
  {
    title: 'Screenshot detection',
    body: 'Names, EXIF, and aspect ratio combine to spot screenshots automatically — they start suggested as Noise until you say otherwise.',
  },
  {
    title: 'Face grouping',
    body: "Apple's Vision framework finds and clusters faces on-device. Name a group, and the face data never leaves the local index.",
  },
  {
    title: 'Incremental scans',
    body: 'Re-scanning skips files whose path, size, and mtime are unchanged. Your Keep and Noise marks always survive the next pass.',
  },
  {
    title: 'Nothing is permanent',
    body: 'There is no permanent delete in Sift. Every removal is a confirmation away — trash it or move it to a folder you choose.',
  },
]

function Nav() {
  return (
    <header className="nav">
      <div className="nav-inner">
        <a href="#top" className="brand">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" fill="currentColor" />
          </svg>
          Sift
        </a>
        <nav className="nav-links">
          <a href="#review">Review</a>
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
          <a href="#install">Install</a>
        </nav>
        <div className="nav-cta">
          <a
            className="btn btn-ghost"
            href="https://github.com/alokkr016/sift"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <a className="btn btn-solid" href="#install">
            Get Sift
          </a>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="hero" id="top">
      <div className="hero-glow" aria-hidden="true" />
      <div className="hero-inner">
        <div className="hero-copy">
          <p className="eyebrow">Photo culling for macOS</p>
          <h1>
            Keep the photos.
            <br />
            Trash the noise.
          </h1>
          <p className="hero-sub">
            Sift reads the folders already on your Mac and turns culling into a
            rhythm — one keypress per photo. Nothing is uploaded, nothing is
            deleted until you confirm it.
          </p>
          <div className="hero-actions">
            <a className="btn btn-solid btn-lg" href="#install">
              Get Sift
            </a>
            <a
              className="btn btn-outline btn-lg"
              href="https://github.com/alokkr016/sift"
              target="_blank"
              rel="noreferrer"
            >
              View source
            </a>
          </div>
        </div>
        <div className="hero-demo" id="review">
          <ReviewDemo />
          <p className="demo-note">Live demo — try pressing K, N, or the arrows.</p>
        </div>
      </div>
      <div className="trust-strip">
        <span>100% local</span>
        <span>No uploads</span>
        <span>MIT licensed</span>
        <span>Python 3.11+</span>
        <span>Apple Vision faces</span>
      </div>
    </section>
  )
}

function How() {
  return (
    <section className="section" id="how">
      <div className="section-head">
        <p className="eyebrow">How it works</p>
        <h2>
          Three commands, start to <span className="underlined">finish</span>
        </h2>
      </div>
      <div className="steps">
        {STEPS.map((s) => (
          <article className="step" key={s.n}>
            <span className="step-n">{s.n}</span>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
            <code className="step-cmd">{s.cmd}</code>
          </article>
        ))}
      </div>
    </section>
  )
}

function Features() {
  return (
    <section className="section" id="features">
      <div className="section-head">
        <p className="eyebrow">What it does</p>
        <h2>Everything runs on your Mac</h2>
      </div>
      <div className="feature-grid">
        {FEATURES.map((f) => (
          <article className="feature" key={f.title}>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

function Privacy() {
  return (
    <section className="section privacy">
      <div className="privacy-card">
        <div className="privacy-copy">
          <p className="eyebrow">Privacy</p>
          <h2>Your library never leaves the room.</h2>
          <p>
            The index is a single SQLite file on disk, permissions 0600. Face
            crops, hashes, and marks all live inside it. Sift has no network
            code — there is nothing to send even if it wanted to.
          </p>
        </div>
        <pre className="privacy-term">
          <code>{`$ sift stats
photos        8,412
keep / noise  2,109 / 6,303
duplicate grp   148
faces           916
index  ~/Library/Application Support/Sift/sift.sqlite`}</code>
        </pre>
      </div>
    </section>
  )
}

function Install() {
  return (
    <section className="section install" id="install">
      <div className="section-head">
        <p className="eyebrow">Install</p>
        <h2>Two minutes to your first review</h2>
        <p className="section-sub">
          Needs Python 3.11 or newer. Clone, install the package, then point it
          at a folder.
        </p>
      </div>
      <div className="install-card">
        <pre>
          <code>{`git clone https://github.com/alokkr016/sift
cd sift
python3.13 -m venv .venv
.venv/bin/pip install -e .

.venv/bin/sift scan ~/Pictures
.venv/bin/sift app`}</code>
        </pre>
        <button
          className="btn btn-solid copy-btn"
          onClick={() =>
            navigator.clipboard.writeText(
              `git clone https://github.com/alokkr016/sift
cd sift
python3.13 -m venv .venv
.venv/bin/pip install -e .

.venv/bin/sift scan ~/Pictures
.venv/bin/sift app`
            )
          }
        >
          Copy
        </button>
      </div>
      <p className="install-alt">
        Prefer reading first? The{' '}
        <a
          href="https://github.com/alokkr016/sift#readme"
          target="_blank"
          rel="noreferrer"
        >
          full README
        </a>{' '}
        covers commands, limits, and the hashing details.
      </p>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <span className="brand brand-sm">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" fill="currentColor" />
          </svg>
          Sift
        </span>
        <div className="footer-links">
          <a
            href="https://github.com/alokkr016/sift"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <a
            href="https://github.com/alokkr016/sift#readme"
            target="_blank"
            rel="noreferrer"
          >
            Docs
          </a>
          <a
            href="https://github.com/alokkr016/sift/blob/main/LICENSE"
            target="_blank"
            rel="noreferrer"
          >
            MIT License
          </a>
        </div>
        <span className="footer-note">Runs entirely on your Mac.</span>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <How />
        <Features />
        <Privacy />
        <Install />
      </main>
      <Footer />
    </>
  )
}
