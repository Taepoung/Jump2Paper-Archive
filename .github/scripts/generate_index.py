import os
import re
import glob
import json
from datetime import datetime

import yake
from datamuse import datamuse

# Initialize YAKE and Datamuse
kw_extractor = yake.KeywordExtractor(
    lan="en", n=3, dedupLim=0.9, top=5, features=None
)
dm = datamuse.Datamuse()

KNOWN_LANGS = {
    "kr": "Korean (KR)",
    "en": "English (EN)",
    "jp": "Japanese (JP)",
    "cn": "Chinese (CN)",
    "fr": "French (FR)",
    "de": "German (DE)",
    "es": "Spanish (ES)",
}
METADATA_FILE = ".github/papers_metadata.json"


def get_synonyms(word):
    """Fetches up to 3 synonyms/related terms using the Datamuse API."""
    try:
        results = dm.words(ml=word, max=3)
        return [r["word"] for r in results]
    except Exception:
        return []


def discover_acronyms(text):
    """Finds patterns like 'Full Name (ABC)' in text and returns synonym pairs."""
    pairs = set()
    matches = re.finditer(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\(([A-Z]{2,})\)", text
    )
    for match in matches:
        pairs.add((match.group(1).strip(), match.group(2).strip()))
    return pairs


def load_metadata():
    """Loads the persistent metadata file if it exists."""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as exc:
            print(f"Warning: Could not load metadata: {exc}")
    return {}


def save_metadata(metadata):
    """Saves the metadata dictionary back to the JSON file."""
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"Error saving metadata: {exc}")


def get_html_metadata(filepath, existing_metadata):
    """Categorizes metadata into prioritized groups."""
    rel_path = os.path.relpath(filepath).replace("\\", "/")

    if rel_path in existing_metadata:
        meta = existing_metadata[rel_path]
        return (
            meta["title"],
            meta.get("p1_tags", ""),
            meta.get("p2_tags", ""),
            meta.get("p3_tags", ""),
            meta.get("p4_tags", ""),
        )

    title = ""
    p1_tags, p2_tags, p3_tags, p4_tags = set(), set(), set(), set()

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            full_content = file.read()

        match = re.search(
            r"p2w-hero[^>]*>.*?<h1>(.*?)</h1>",
            full_content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            title = re.sub(r"<[^>]+>", "", match.group(1).strip())
        else:
            match = re.search(
                r"<title>(.*?)</title>", full_content, re.IGNORECASE | re.DOTALL
            )
            if match:
                title = match.group(1).strip()

        kw_matches = re.findall(
            r'<a[^>]*class="p2w-keyword"[^>]*>(.*?)</a>',
            full_content,
            re.IGNORECASE | re.DOTALL,
        )
        for kw in kw_matches:
            kw_text = re.sub(r"<[^>]+>", "", kw).strip()
            if kw_text:
                p1_tags.add(kw_text)

        clean_body = re.sub(
            r"<(style|script)[^>]*>.*?</\1>",
            " ",
            full_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        clean_text = re.sub(r"<[^>]+>", " ", clean_body)
        clean_text = " ".join(clean_text.split())

        body_text = clean_text[:5000]
        yake_keywords = kw_extractor.extract_keywords(body_text)
        p1_lower = {tag.lower() for tag in p1_tags}

        for kw, _score in yake_keywords:
            if kw.lower() not in p1_lower:
                p2_tags.add(kw)

        acronym_pairs = discover_acronyms(body_text)
        for full, acro in acronym_pairs:
            p4_tags.add(full)
            p4_tags.add(acro)

        p2_lower = {tag.lower() for tag in p2_tags}
        for tag in list(p1_tags) + list(p4_tags):
            if len(tag) > 2:
                for synonym in get_synonyms(tag):
                    synonym_lower = synonym.lower()
                    if synonym_lower not in p1_lower and synonym_lower not in p2_lower:
                        p3_tags.add(synonym)

    except Exception as exc:
        print(f"Error reading {filepath}: {exc}")

    if title:
        title = re.sub(r"<[^>]+>", "", title)
    if not title:
        title = os.path.basename(filepath).split(".")[0].replace("-", " ").title()

    return (
        title,
        ", ".join(sorted(p1_tags)),
        ", ".join(sorted(p2_tags)),
        ", ".join(sorted(p3_tags)),
        ", ".join(sorted(p4_tags)),
    )


def clean_attr(value):
    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace('"', "&quot;")
        .strip()
    )


def build_stats_html(total_files, active_langs):
    stat_items = [
        ("Records", str(total_files).zfill(3)),
        ("Languages", str(len(active_langs)).zfill(2)),
        ("Updated", datetime.now().strftime("%Y.%m.%d")),
    ]
    return "\n".join(
        [
            f"""        <span class="archive-stat"><span class="archive-stat-label">{label}</span> {value}</span>"""
            for label, value in stat_items
        ]
    )


def generate_index():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(base_dir)

    metadata = load_metadata()
    new_metadata = {}
    all_files = []
    active_langs = set()

    for entry in os.listdir("."):
        if os.path.isdir(entry) and not entry.startswith(".") and entry not in {
            "node_modules",
            "__pycache__",
        }:
            html_files = glob.glob(os.path.join(entry, "*.html"))
            if html_files:
                active_langs.add(entry)
                for filepath in html_files:
                    rel_path = os.path.relpath(filepath).replace("\\", "/")
                    title, p1, p2, p3, p4 = get_html_metadata(filepath, metadata)
                    paper_entry = {
                        "lang": entry,
                        "path": rel_path,
                        "title": title,
                        "p1": p1,
                        "p2": p2,
                        "p3": p3,
                        "p4": p4,
                    }
                    all_files.append(paper_entry)
                    new_metadata[rel_path] = {
                        "title": title,
                        "lang": entry,
                        "p1_tags": p1,
                        "p2_tags": p2,
                        "p3_tags": p3,
                        "p4_tags": p4,
                    }

    save_metadata(new_metadata)
    all_files.sort(key=lambda item: item["title"])
    active_langs = sorted(active_langs)

    filters_html = '<button class="filter-btn active" data-lang="all">All</button>\n'
    for lang in active_langs:
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        filters_html += (
            f'        <button class="filter-btn" data-lang="{lang}">'
            f"{display_name}</button>\n"
        )

    stats_html = build_stats_html(len(all_files), active_langs)

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jump2Paper archive</title>

  <meta property="og:type" content="website">
  <meta property="og:title" content="Jump2Paper archive">
  <meta property="og:description" content="Explore Academic Papers in Professional Web Format. Optimized for readability and accessibility.">
  <meta property="og:image" content="./.github/images/og-image.png">
  <meta property="og:site_name" content="Jump2Paper archive">

  <script src="https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.min.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
      --color-bg: #ffffff;
      --color-bg-soft: #f8f7f4;
      --color-text: #1a1a1a;
      --color-text-muted: #6b6b6b;
      --color-accent: #e8601c;
      --color-accent-light: #fdf0e8;
      --color-positive: #2d7d46;
      --color-positive-bg: #edf7f1;
      --color-border: #e0ddd8;
      --color-code-bg: #f4f2ee;

      --font-body: 'Lora', Georgia, serif;
      --font-ui: 'DM Sans', system-ui, sans-serif;
      --font-code: 'JetBrains Mono', monospace;

      --text-base: 17px;
      --line-height: 1.8;
      --content-width: 800px;
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html {{
      scroll-behavior: smooth;
      font-size: var(--text-base);
    }}

    body {{
      background: var(--color-bg);
      color: var(--color-text);
      font-family: var(--font-body);
      line-height: var(--line-height);
    }}

    .p2w-content {{
      max-width: var(--content-width);
      margin: 0 auto;
      padding: 0 2rem;
    }}

    h1, h2, h3, h4, h5 {{
      font-family: var(--font-ui);
      line-height: 1.3;
      color: var(--color-text);
    }}

    h1 {{
      font-size: 2.4rem;
      font-weight: 600;
    }}

    a {{
      color: var(--color-accent);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .p2w-hero {{
      padding: 5rem 0 4rem;
      border-bottom: 1px solid var(--color-border);
    }}

    .p2w-hero .p2w-content {{
      text-align: center;
    }}

    .p2w-hero h1 {{
      margin-bottom: 1.25rem;
    }}

    .archive-stats {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 0.75rem;
      margin-top: 1.5rem;
    }}

    .archive-stat {{
      font-family: var(--font-ui);
      font-size: 0.84rem;
      color: var(--color-text-muted);
    }}

    .archive-stat-label {{
      font-weight: 600;
      color: var(--color-text);
      margin-right: 0.2rem;
    }}

    .p2w-keywords {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 1.25rem;
    }}

    .p2w-keyword {{
      font-family: var(--font-ui);
      font-size: 0.8rem;
      padding: 0.25rem 0.7rem;
      border: 1px solid var(--color-border);
      border-radius: 20px;
      color: var(--color-text-muted);
      background: var(--color-bg);
    }}

    .p2w-keyword:hover {{
      border-color: var(--color-accent);
      color: var(--color-accent);
      text-decoration: none;
    }}

    .controls-section {{
      position: sticky;
      top: 0;
      z-index: 120;
      padding: 0;
      background: var(--color-bg-soft);
      border-bottom: 1px solid var(--color-border);
      box-shadow: 0 8px 18px rgba(26, 26, 26, 0.04);
    }}

    .controls-container {{
      padding-top: 2rem;
      padding-bottom: 2rem;
    }}

    .controls-heading {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: baseline;
      margin-bottom: 1rem;
      font-family: var(--font-ui);
    }}

    .controls-heading strong {{
      font-size: 1rem;
      font-weight: 600;
    }}

    .controls-heading span {{
      font-size: 0.85rem;
      color: var(--color-text-muted);
    }}

    .search-input {{
      width: 100%;
      padding: 0.9rem 1rem;
      font-size: 1rem;
      font-family: var(--font-ui);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      background: var(--color-bg);
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}

    .search-input:focus {{
      border-color: var(--color-accent);
      box-shadow: 0 0 0 3px var(--color-accent-light);
    }}

    .filter-group {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-top: 1rem;
    }}

    .filter-btn {{
      font-family: var(--font-ui);
      font-size: 0.82rem;
      padding: 0.35rem 0.85rem;
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      color: var(--color-text-muted);
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .filter-btn:hover {{
      border-color: var(--color-accent);
      color: var(--color-accent);
    }}

    .filter-btn.active {{
      background: var(--color-accent);
      color: #fff;
      border-color: var(--color-accent);
    }}

    .papers-section {{
      padding: 3rem 0;
      min-height: 50vh;
    }}

    .paper-list {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}

    .paper-card {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 1rem;
      align-items: start;
      padding: 1.25rem 1.35rem;
      border: 1px solid var(--color-border);
      border-radius: 8px;
      text-decoration: none;
      color: var(--color-text);
      background: var(--color-bg);
      transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
    }}

    .paper-card:hover {{
      border-color: var(--color-accent);
      transform: translateY(-2px);
      box-shadow: 0 10px 22px rgba(26, 26, 26, 0.05);
      text-decoration: none;
    }}

    .paper-index {{
      font-family: var(--font-ui);
      font-size: 0.82rem;
      color: var(--color-text-muted);
      margin-bottom: 0.35rem;
    }}

    .paper-info h3 {{
      font-size: 1.15rem;
      margin-bottom: 0.5rem;
    }}

    .paper-card:hover .paper-info h3 {{
      color: var(--color-accent);
    }}

    .paper-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      margin-top: 0.9rem;
    }}

    .tag-item {{
      font-family: var(--font-ui);
      font-size: 0.8rem;
      padding: 0.25rem 0.7rem;
      border: 1px solid var(--color-border);
      border-radius: 20px;
      color: var(--color-text-muted);
      background: var(--color-bg);
    }}

    .paper-meta {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 0.6rem;
      min-width: 112px;
    }}

    .lang-badge {{
      font-family: var(--font-ui);
      font-size: 0.78rem;
      font-weight: 600;
      padding: 0.18rem 0.55rem;
      border-radius: 4px;
      background: var(--color-bg-soft);
      color: var(--color-text-muted);
      border: 1px solid var(--color-border);
      text-transform: uppercase;
    }}

    .lang-badge.en {{
      background: var(--color-positive-bg);
      color: var(--color-positive);
      border-color: #b8e0c8;
    }}

    .paper-link {{
      display: inline-block;
      font-family: var(--font-ui);
      font-size: 0.82rem;
      padding: 0.35rem 0.85rem;
      border: 1px solid var(--color-accent);
      border-radius: 4px;
      color: var(--color-accent);
      transition: background 0.15s, color 0.15s;
    }}

    .paper-card:hover .paper-link {{
      background: var(--color-accent);
      color: #fff;
    }}

    .pagination-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;
      margin-top: 3rem;
      font-family: var(--font-ui);
      flex-wrap: wrap;
    }}

    .page-btn {{
      padding: 0.45rem 0.8rem;
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }}

    .page-btn:hover:not(:disabled) {{
      border-color: var(--color-accent);
      color: var(--color-accent);
    }}

    .page-btn.active {{
      background: var(--color-accent);
      color: white;
      border-color: var(--color-accent);
    }}

    .page-btn:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    .no-results {{
      text-align: center;
      padding: 5rem 0;
      color: var(--color-text-muted);
      font-family: var(--font-ui);
      display: none;
    }}

    @media (max-width: 760px) {{
      .paper-card {{
        grid-template-columns: 1fr;
      }}

      .paper-meta {{
        align-items: flex-start;
      }}
    }}

    @media (max-width: 560px) {{
      .p2w-content {{
        padding: 0 1rem;
      }}

      .controls-heading {{
        flex-direction: column;
        align-items: flex-start;
      }}

      .p2w-hero h1 {{
        font-size: 2rem;
      }}

      .controls-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
      }}
    }}
  </style>
</head>
<body>

  <div class="p2w-hero">
    <div class="p2w-content">
      <h1>Jump2Paper Archive</h1>
      <div class="archive-stats">
{stats_html}
      </div>
    </div>
  </div>

  <div class="controls-section">
    <div class="p2w-content controls-container">
      <div class="controls-heading">
        <strong>문서 찾기</strong>
        <span>제목, 키워드, 약어, 언어별 탐색</span>
      </div>
      <input type="text" id="searchInput" class="search-input" placeholder="Search by title or category (e.g. LLM, RL)..." autocomplete="off">
      <div class="filter-group" id="filterGroup">
        {filters_html}      </div>
    </div>
  </div>

  <div class="papers-section p2w-content">
    <div class="paper-list" id="papersList">
"""

    for index, item in enumerate(all_files, start=1):
        lang = item["lang"]
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        short_label = display_name.split(" (")[0] if " (" in display_name else display_name

        t_attr = clean_attr(item["title"])
        p1_attr = clean_attr(item["p1"])
        p2_attr = clean_attr(item["p2"])
        p3_attr = clean_attr(item["p3"])
        p4_attr = clean_attr(item["p4"])

        tags_html = ""
        ui_tags = [tag.strip() for tag in p1_attr.split(",") if tag.strip()]
        if ui_tags:
            tag_items = "".join(
                [f'<span class="tag-item">{tag}</span>' for tag in ui_tags[:5]]
            )
            tags_html = f'<div class="paper-tags">{tag_items}</div>'

        html_content += f"""
      <a href="{item["path"]}" class="paper-card" data-title="{t_attr}" data-lang="{lang}" data-p1="{p1_attr}" data-p2="{p2_attr}" data-p3="{p3_attr}" data-p4="{p4_attr}">
        <div class="paper-info">
          <div class="paper-index">문서 {index:03d}</div>
          <h3>{item["title"]}</h3>
          {tags_html}
        </div>
        <div class="paper-meta">
          <div class="lang-badge {lang}">{short_label}</div>
          <div class="paper-link">읽기 →</div>
        </div>
      </a>"""

    html_content += """
    </div>
    <div id="noResults" class="no-results">
      No papers found matching your criteria.
    </div>

    <div class="pagination-container" id="paginationControls">
      <!-- Dynamic Pagination Buttons -->
    </div>
  </div>

  <script>
    const searchInput = document.getElementById('searchInput');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const cards = Array.from(document.querySelectorAll('.paper-card'));
    const noResults = document.getElementById('noResults');
    const paginationControls = document.getElementById('paginationControls');

    let currentLang = 'all';
    let currentSearch = '';
    let currentPage = 1;
    const pageSize = 10;

    const paperData = cards.map(card => {
      const title = card.getAttribute('data-title') || '';
      const p1 = card.getAttribute('data-p1') || '';
      const p2 = card.getAttribute('data-p2') || '';
      const p3 = card.getAttribute('data-p3') || '';
      const p4 = card.getAttribute('data-p4') || '';

      return {
        el: card,
        title,
        titleLower: title.toLowerCase(),
        lang: card.getAttribute('data-lang'),
        p1,
        p1Lower: p1.toLowerCase(),
        p2,
        p2Lower: p2.toLowerCase(),
        p3,
        p3Lower: p3.toLowerCase(),
        p4,
        p4Lower: p4.toLowerCase(),
        combinedLower: [title, p1, p2, p3, p4].join(' ').toLowerCase()
      };
    });

    const fuse = new Fuse(paperData, {
      keys: [
        { name: 'title', weight: 3.0 },
        { name: 'p1', weight: 1.4 },
        { name: 'p4', weight: 0.8 },
        { name: 'p2', weight: 0.35 },
        { name: 'p3', weight: 0.15 }
      ],
      threshold: 0.28,
      ignoreLocation: true,
      includeScore: true
    });

    function tokenizeQuery(query) {
      return query
        .split(/\\s+/)
        .map(token => token.trim())
        .filter(Boolean);
    }

    function scorePaper(item, query, tokens, fuseMap) {
      let score = 0;

      if (item.titleLower === query) score += 1000;
      if (item.titleLower.startsWith(query)) score += 320;
      if (item.titleLower.includes(query)) score += 180;
      if (item.p1Lower.includes(query)) score += 120;
      if (item.p4Lower.includes(query)) score += 75;
      if (item.p2Lower.includes(query)) score += 35;
      if (item.p3Lower.includes(query)) score += 20;

      let matchedTokens = 0;

      tokens.forEach(token => {
        let tokenMatched = false;

        if (item.titleLower === token) {
          score += 260;
          tokenMatched = true;
        } else if (item.titleLower.startsWith(token)) {
          score += 130;
          tokenMatched = true;
        } else if (item.titleLower.includes(token)) {
          score += 75;
          tokenMatched = true;
        }

        if (item.p1Lower.includes(token)) {
          score += 48;
          tokenMatched = true;
        }

        if (item.p4Lower.includes(token)) {
          score += 28;
          tokenMatched = true;
        }

        if (token.length >= 3 && item.p2Lower.includes(token)) {
          score += 12;
          tokenMatched = true;
        }

        if (token.length >= 4 && item.p3Lower.includes(token)) {
          score += 6;
          tokenMatched = true;
        }

        if (tokenMatched) matchedTokens += 1;
      });

      if (tokens.length > 1) {
        score += matchedTokens * 25;
        if (matchedTokens === tokens.length) score += 140;
      }

      const fuseScore = fuseMap.get(item);
      if (fuseScore !== undefined) {
        score += Math.max(0, 80 - (fuseScore * 120));
      }

      return score;
    }

    function searchPapers(items, query) {
      const tokens = tokenizeQuery(query);
      const fuseResults = fuse.search(query);
      const fuseMap = new Map(
        fuseResults.map(result => [result.item, result.score ?? 1])
      );

      const ranked = items
        .map(item => ({
          item,
          score: scorePaper(item, query, tokens, fuseMap)
        }))
        .filter(entry => {
          if (entry.score > 0) return true;
          return tokens.length > 0 && tokens.every(token =>
            entry.item.combinedLower.includes(token)
          );
        })
        .sort((a, b) => {
          if (b.score !== a.score) return b.score - a.score;
          return a.item.title.localeCompare(b.item.title);
        });

      return ranked.map(entry => entry.item);
    }

    function updateView() {
      let results = [];

      const langFiltered = paperData.filter(item =>
        currentLang === 'all' || item.lang === currentLang
      );

      if (currentSearch) {
        results = searchPapers(langFiltered, currentSearch);
      } else {
        results = langFiltered;
      }

      const totalItems = results.length;
      const totalPages = Math.ceil(totalItems / pageSize);
      if (currentPage > totalPages) currentPage = Math.max(1, totalPages);

      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const paginatedItems = results.slice(start, end);

      paperData.forEach(item => item.el.style.display = 'none');
      paginatedItems.forEach(item => item.el.style.display = 'grid');

      noResults.style.display = totalItems === 0 ? 'block' : 'none';
      renderPaginationButtons(totalPages);
    }

    function renderPaginationButtons(totalPages) {
      paginationControls.innerHTML = '';
      if (totalPages <= 1) return;

      const createBtn = (label, page, isActive = false, isDisabled = false) => {
        const btn = document.createElement('button');
        btn.className = `page-btn ${isActive ? 'active' : ''}`;
        btn.innerText = label;
        btn.disabled = isDisabled;
        btn.addEventListener('click', () => {
          currentPage = page;
          updateView();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        return btn;
      };

      paginationControls.appendChild(
        createBtn('Prev', currentPage - 1, false, currentPage === 1)
      );

      for (let page = 1; page <= totalPages; page++) {
        if (totalPages > 7) {
          if (
            page === 1 ||
            page === totalPages ||
            (page >= currentPage - 1 && page <= currentPage + 1)
          ) {
            paginationControls.appendChild(
              createBtn(page, page, page === currentPage)
            );
          } else if (page === currentPage - 2 || page === currentPage + 2) {
            const dot = document.createElement('span');
            dot.innerText = '...';
            paginationControls.appendChild(dot);
          }
        } else {
          paginationControls.appendChild(createBtn(page, page, page === currentPage));
        }
      }

      paginationControls.appendChild(
        createBtn('Next', currentPage + 1, false, currentPage === totalPages)
      );
    }

    searchInput.addEventListener('input', event => {
      currentSearch = event.target.value.toLowerCase().trim();
      currentPage = 1;
      updateView();
    });

    filterBtns.forEach(btn => {
      btn.addEventListener('click', event => {
        filterBtns.forEach(filterBtn => filterBtn.classList.remove('active'));
        event.target.classList.add('active');
        currentLang = event.target.getAttribute('data-lang');
        currentPage = 1;
        updateView();
      });
    });

    updateView();
  </script>
</body>
</html>
"""

    index_path = os.path.join(base_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    print(
        f"Successfully created {index_path} with {len(all_files)} papers across "
        f"{len(active_langs)} languages."
    )


if __name__ == "__main__":
    generate_index()
