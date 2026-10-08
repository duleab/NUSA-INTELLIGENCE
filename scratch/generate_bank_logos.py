"""Generate handcrafted vector SVG logos for all IDX banks and demo banks."""

from pathlib import Path

LOGOS_DIR = Path("assets") / "logos"
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

SVGS = {
    "BNLI": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bnliGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#059669"/>
      <stop offset="100%" stop-color="#064E3B"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bnliGrad)"/>
  <polygon points="50,20 78,42 50,80 22,42" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linejoin="round"/>
  <polygon points="50,32 70,46 50,72 30,46" fill="#34D399" opacity="0.9"/>
  <line x1="22" y1="42" x2="78" y2="42" stroke="#FFFFFF" stroke-width="4"/>
</svg>""",

    "MEGA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="megaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#B45309"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#megaGrad)"/>
  <path d="M 24 74 L 24 30 L 50 56 L 76 30 L 76 74" fill="none" stroke="#FFFFFF" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "NISP": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="nispGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#EF4444"/>
      <stop offset="100%" stop-color="#991B1B"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#nispGrad)"/>
  <path d="M 50 20 C 50 20 74 38 74 60 C 74 74 62 80 50 80 C 38 80 26 74 26 60 C 26 38 50 20 50 20 Z" fill="#FFFFFF"/>
  <circle cx="50" cy="55" r="14" fill="#DC2626"/>
  <path d="M 50 45 L 50 65 M 40 55 L 60 55" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round"/>
</svg>""",

    "BTPN": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="btpnGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#047857"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#btpnGrad)"/>
  <path d="M 28 42 L 50 22 L 72 42 L 50 62 Z" fill="#FFFFFF"/>
  <path d="M 28 62 L 50 42 L 72 62 L 50 82 Z" fill="#38BDF8" opacity="0.85"/>
</svg>""",

    "BINA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="binaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#0369A1"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#binaGrad)"/>
  <circle cx="50" cy="50" r="26" fill="none" stroke="#FDE047" stroke-width="6"/>
  <circle cx="50" cy="50" r="14" fill="#FFFFFF"/>
  <path d="M 50 16 L 50 24 M 50 76 L 50 84 M 16 50 L 24 50 M 76 50 L 84 50" stroke="#FDE047" stroke-width="5" stroke-linecap="round"/>
</svg>""",

    "PNBN": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="pnbnGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#15803D"/>
      <stop offset="100%" stop-color="#14532D"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#pnbnGrad)"/>
  <rect x="36" y="22" width="28" height="56" rx="4" fill="#FFFFFF"/>
  <rect x="22" y="36" width="56" height="28" rx="4" fill="#F97316"/>
  <circle cx="50" cy="50" r="8" fill="#15803D"/>
</svg>""",

    "BSIM": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bsimGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#E11D48"/>
      <stop offset="100%" stop-color="#881337"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bsimGrad)"/>
  <circle cx="50" cy="50" r="16" fill="#FFFFFF"/>
  <polygon points="50,18 56,36 74,38 60,50 64,68 50,58 36,68 40,50 26,38 44,36" fill="#FDE047"/>
</svg>""",

    "BBTN": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bbtnGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1D4ED8"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bbtnGrad)"/>
  <path d="M 50 22 L 78 48 L 68 48 L 68 76 L 32 76 L 32 48 L 22 48 Z" fill="#FFFFFF"/>
  <rect x="42" y="52" width="16" height="24" fill="#1D4ED8"/>
</svg>""",

    "BNII": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bniiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#B45309"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bniiGrad)"/>
  <polygon points="50,22 76,40 68,74 32,74 24,40" fill="#1E293B"/>
  <polygon points="50,30 70,44 64,68 36,68 30,44" fill="#F59E0B"/>
  <circle cx="42" cy="48" r="4" fill="#FFFFFF"/>
  <circle cx="58" cy="48" r="4" fill="#FFFFFF"/>
  <polygon points="50,56 46,62 54,62" fill="#FFFFFF"/>
</svg>""",

    "BSWD": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bswdGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E293B"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bswdGrad)"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="#EA580C" stroke-width="6"/>
  <circle cx="50" cy="50" r="14" fill="none" stroke="#FFFFFF" stroke-width="4"/>
  <polygon points="50,26 54,46 50,50 46,46" fill="#EA580C"/>
  <polygon points="50,74 54,54 50,50 46,54" fill="#EA580C"/>
  <polygon points="26,50 46,46 50,50 46,54" fill="#EA580C"/>
  <polygon points="74,50 54,46 50,50 54,54" fill="#EA580C"/>
</svg>""",

    "BMAS": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bmasGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bmasGrad)"/>
  <path d="M 24 72 L 36 28 L 50 54 L 64 28 L 76 72" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "BBMD": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bbmdGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E3A8A"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bbmdGrad)"/>
  <rect x="26" y="32" width="12" height="42" rx="3" fill="#E2E8F0"/>
  <rect x="44" y="24" width="12" height="50" rx="3" fill="#F59E0B"/>
  <rect x="62" y="32" width="12" height="42" rx="3" fill="#E2E8F0"/>
  <line x1="20" y1="78" x2="80" y2="78" stroke="#E2E8F0" stroke-width="4" stroke-linecap="round"/>
</svg>""",

    "BJBR": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bjbrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#0369A1"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bjbrGrad)"/>
  <polygon points="50,22 80,74 20,74" fill="none" stroke="#FDE047" stroke-width="7" stroke-linejoin="round"/>
  <polygon points="50,38 70,70 30,70" fill="#FFFFFF"/>
</svg>""",

    "BBKP": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bbkpGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#D97706"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bbkpGrad)"/>
  <circle cx="50" cy="50" r="28" fill="#FFFFFF"/>
  <polygon points="50,28 56,44 72,44 60,54 64,70 50,60 36,70 40,54 28,44 44,44" fill="#78350F"/>
</svg>""",

    "BJTM": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bjtmGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#16A34A"/>
      <stop offset="100%" stop-color="#15803D"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bjtmGrad)"/>
  <polygon points="50,22 76,36 76,64 50,78 24,64 24,36" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linejoin="round"/>
  <polygon points="50,32 68,42 68,60 50,70 32,60 32,42" fill="#FACC15"/>
</svg>""",

    "BTPS": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="btpsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#5B21B6"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#btpsGrad)"/>
  <path d="M 64 26 C 46 28 32 42 32 60 C 32 78 46 90 64 88 C 48 84 40 70 40 58 C 40 44 50 32 64 26 Z" fill="#FFFFFF"/>
  <polygon points="68,40 71,48 79,48 73,53 75,61 68,56 61,61 63,53 57,48 65,48" fill="#FDE047"/>
</svg>""",

    "MAYA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="mayaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#DC2626"/>
      <stop offset="100%" stop-color="#991B1B"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#mayaGrad)"/>
  <polygon points="50,22 74,48 50,74 26,48" fill="#FDE047"/>
  <polygon points="50,32 64,48 50,64 36,48" fill="#FFFFFF"/>
</svg>""",

    "MASB": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="masbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0891B2"/>
      <stop offset="100%" stop-color="#0E7490"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#masbGrad)"/>
  <rect x="22" y="48" width="16" height="30" rx="3" fill="#FFFFFF"/>
  <rect x="42" y="34" width="16" height="44" rx="3" fill="#FFFFFF"/>
  <rect x="62" y="20" width="16" height="58" rx="3" fill="#FDE047"/>
</svg>""",

    "AMAR": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="amarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#amarGrad)"/>
  <path d="M 24 64 C 36 78 64 78 76 64" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round"/>
  <circle cx="36" cy="40" r="7" fill="#FFFFFF"/>
  <circle cx="64" cy="40" r="7" fill="#FFFFFF"/>
</svg>""",

    "NOBU": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="nobuGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C3AED"/>
      <stop offset="100%" stop-color="#4C1D95"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#nobuGrad)"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="#FFFFFF" stroke-width="6"/>
  <circle cx="50" cy="50" r="14" fill="#F472B6"/>
</svg>""",

    "BANK": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bankGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0D9488"/>
      <stop offset="100%" stop-color="#115E59"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bankGrad)"/>
  <polygon points="50,18 78,50 50,82 22,50" fill="none" stroke="#FDE047" stroke-width="7"/>
  <circle cx="50" cy="50" r="12" fill="#FFFFFF"/>
</svg>""",

    "AGRO": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="agroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#059669"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#agroGrad)"/>
  <path d="M 50 78 C 50 78 28 58 28 40 C 28 26 38 18 50 18 C 62 18 72 26 72 40 C 72 58 50 78 50 78 Z" fill="#FFFFFF"/>
  <path d="M 50 28 L 50 68 M 50 42 L 36 34 M 50 52 L 64 44" stroke="#059669" stroke-width="4" stroke-linecap="round"/>
</svg>""",

    "INPC": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="inpcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#inpcGrad)"/>
  <path d="M 20 40 L 50 26 L 80 40 L 50 78 Z" fill="none" stroke="#F59E0B" stroke-width="6" stroke-linejoin="round"/>
  <path d="M 32 46 L 50 36 L 68 46 L 50 68 Z" fill="#FFFFFF"/>
</svg>""",

    "SDRA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="sdraGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#075985"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#sdraGrad)"/>
  <circle cx="50" cy="50" r="26" fill="none" stroke="#FFFFFF" stroke-width="7"/>
  <circle cx="50" cy="50" r="12" fill="#38BDF8"/>
</svg>""",

    "AGRS": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="agrsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1D4ED8"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#agrsGrad)"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="#FFFFFF" stroke-width="6"/>
  <ellipse cx="50" cy="50" rx="14" ry="28" fill="none" stroke="#FFFFFF" stroke-width="4"/>
  <line x1="22" y1="50" x2="78" y2="50" stroke="#FFFFFF" stroke-width="4"/>
</svg>""",

    "BNBA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bnbaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F766E"/>
      <stop offset="100%" stop-color="#134E4A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bnbaGrad)"/>
  <circle cx="50" cy="50" r="26" fill="#14B8A6"/>
  <path d="M 30 50 Q 50 30 70 50 Q 50 70 30 50 Z" fill="#FFFFFF"/>
</svg>""",

    "BBYB": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bbybGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FACC15"/>
      <stop offset="100%" stop-color="#EAB308"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bbybGrad)"/>
  <polygon points="50,20 78,48 50,76 22,48" fill="#18181B"/>
  <circle cx="42" cy="48" r="5" fill="#FACC15"/>
  <circle cx="58" cy="48" r="5" fill="#FACC15"/>
  <path d="M 46 56 Q 50 60 54 56" fill="none" stroke="#FACC15" stroke-width="3" stroke-linecap="round"/>
</svg>""",

    "BGTG": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bgtgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#EA580C"/>
      <stop offset="100%" stop-color="#9A3412"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bgtgGrad)"/>
  <circle cx="50" cy="42" r="18" fill="#FFFFFF"/>
  <path d="M 50 60 L 50 78 C 50 82 56 82 56 78" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/>
  <path d="M 30 42 C 22 42 22 30 30 30" fill="none" stroke="#FFFFFF" stroke-width="4"/>
  <path d="M 70 42 C 78 42 78 30 70 30" fill="none" stroke="#FFFFFF" stroke-width="4"/>
</svg>""",

    "MCOR": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="mcorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E40AF"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#mcorGrad)"/>
  <path d="M 64 32 C 40 32 30 42 30 50 C 30 58 40 68 64 68" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round"/>
  <path d="M 72 40 C 56 40 50 46 50 50 C 50 54 56 60 72 60" fill="none" stroke="#38BDF8" stroke-width="6" stroke-linecap="round"/>
</svg>""",

    "BCIC": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bcicGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#0369A1"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bcicGrad)"/>
  <circle cx="42" cy="50" r="20" fill="none" stroke="#FFFFFF" stroke-width="6"/>
  <circle cx="58" cy="50" r="20" fill="none" stroke="#FDE047" stroke-width="6"/>
</svg>""",

    "BACA": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bacaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bacaGrad)"/>
  <path d="M 66 32 C 42 32 32 40 32 50 C 32 60 42 68 66 68" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round"/>
  <circle cx="66" cy="50" r="5" fill="#60A5FA"/>
</svg>""",

    "DNAR": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="dnarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#E11D48"/>
      <stop offset="100%" stop-color="#9F1239"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#dnarGrad)"/>
  <circle cx="50" cy="50" r="26" fill="none" stroke="#FFFFFF" stroke-width="7"/>
  <path d="M 38 50 L 46 58 L 64 40" fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "BKSW": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bkswGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#881337"/>
      <stop offset="100%" stop-color="#4C0519"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bkswGrad)"/>
  <path d="M 28 68 C 28 68 40 32 72 28 C 72 28 58 48 42 72 Z" fill="#FFFFFF"/>
</svg>""",

    "PNBS": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="pnbsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#047857"/>
      <stop offset="100%" stop-color="#064E3B"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#pnbsGrad)"/>
  <rect x="30" y="30" width="40" height="40" rx="2" fill="none" stroke="#FDE047" stroke-width="5"/>
  <rect x="30" y="30" width="40" height="40" rx="2" transform="rotate(45 50 50)" fill="none" stroke="#FFFFFF" stroke-width="5"/>
  <circle cx="50" cy="50" r="7" fill="#FDE047"/>
</svg>""",

    "BVIC": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="bvicGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#991B1B"/>
      <stop offset="100%" stop-color="#450A0A"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#bvicGrad)"/>
  <path d="M 26 28 L 50 74 L 74 28" fill="none" stroke="#FDE047" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="50" cy="34" r="6" fill="#FFFFFF"/>
</svg>""",

    "BEKS": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="beksGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6D28D9"/>
      <stop offset="100%" stop-color="#4C1D95"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#beksGrad)"/>
  <path d="M 30 76 L 30 38 L 50 22 L 70 38 L 70 76 Z" fill="none" stroke="#F59E0B" stroke-width="6" stroke-linejoin="round"/>
  <rect x="42" y="52" width="16" height="24" fill="#FFFFFF"/>
</svg>""",

    "BABP": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="babpGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E3A8A"/>
      <stop offset="100%" stop-color="#DC2626"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#babpGrad)"/>
  <polygon points="50,22 80,74 20,74" fill="#FFFFFF"/>
  <polygon points="50,42 70,74 30,74" fill="#DC2626"/>
</svg>""",

    "DEMOBANK1": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="demo1Grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#demo1Grad)"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="#FFFFFF" stroke-width="5"/>
  <polygon points="50,22 56,44 78,50 56,56 50,78 44,56 22,50 44,44" fill="#FDE047"/>
</svg>""",

    "DEMOBANK2": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="demo2Grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#059669"/>
      <stop offset="100%" stop-color="#047857"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#demo2Grad)"/>
  <circle cx="50" cy="42" r="22" fill="#FFFFFF"/>
  <rect x="46" y="58" width="8" height="22" rx="2" fill="#FFFFFF"/>
  <circle cx="50" cy="42" r="14" fill="#34D399"/>
</svg>""",

    "DEMOBANK3": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="demo3Grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#D97706"/>
      <stop offset="100%" stop-color="#B45309"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#demo3Grad)"/>
  <polygon points="50,20 62,38 80,50 62,62 50,80 38,62 20,50 38,38" fill="#FFFFFF"/>
  <circle cx="50" cy="50" r="9" fill="#FDE047"/>
</svg>""",

    "DEMOBANK4": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="demo4Grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7C3AED"/>
      <stop offset="100%" stop-color="#5B21B6"/>
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="24" fill="url(#demo4Grad)"/>
  <polygon points="50,22 78,50 50,78 22,50" fill="#FFFFFF"/>
  <polygon points="50,34 66,50 50,66 34,50" fill="#C084FC"/>
</svg>""",
}

for ticker, content in SVGS.items():
    file_path = LOGOS_DIR / f"{ticker}.svg"
    file_path.write_text(content.strip(), encoding="utf-8")
    print(f"Wrote {file_path}")

print(f"Total SVGs written: {len(SVGS)}")
