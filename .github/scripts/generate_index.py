import os
import re
import glob
import json
import yake
from datamuse import datamuse

# Initialize YAKE and Datamuse
kw_extractor = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=5, features=None)
dm = datamuse.Datamuse()

KNOWN_LANGS = {
    'kr': 'Korean (KR)',
    'en': 'English (EN)',
    'jp': 'Japanese (JP)',
    'cn': 'Chinese (CN)',
    'fr': 'French (FR)',
    'de': 'German (DE)',
    'es': 'Spanish (ES)'
}
METADATA_FILE = '.github/papers_metadata.json'

def get_synonyms(word):
    """Fetches up to 3 synonyms/related terms using the Datamuse API."""
    try:
        # 'rel_syn' for synonyms, 'rel_ml' for "means like"
        results = dm.words(ml=word, max=3)
        return [r['word'] for r in results]
    except:
        return []

def discover_acronyms(text):
    """Finds patterns like 'Full Name (ABC)' in text and returns synonym pairs."""
    pairs = set()
    # Pattern: Full Name (ABC)
    matches = re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\(([A-Z]{2,})\)', text)
    for m in matches:
        pairs.add((m.group(1).strip(), m.group(2).strip()))
    return pairs

def load_metadata():
    """Loads the persistent metadata file if it exists."""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load metadata: {e}")
    return {}

def save_metadata(metadata):
    """Saves the metadata dictionary back to the JSON file."""
    try:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving metadata: {e}")

def get_html_metadata(filepath, existing_metadata):
    """Categorizes metadata into prioritized groups (P1: HTML, P2: YAKE, P3: Syns, P4: Acronyms)."""
    rel_path = os.path.relpath(filepath).replace('\\', '/')
    
    # Check if we already have this paper in our metadata cache
    if rel_path in existing_metadata:
        m = existing_metadata[rel_path]
        return m['title'], m.get('p1_tags', ""), m.get('p2_tags', ""), m.get('p3_tags', ""), m.get('p4_tags', "")

    title = ""
    p1_tags, p2_tags, p3_tags, p4_tags = set(), set(), set(), set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            full_content = f.read() 
            
            # 1. Extract Title
            match = re.search(r'p2w-hero[^>]*>.*?<h1>(.*?)</h1>', full_content, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'<[^>]+>', '', title)
            else:
                match = re.search(r'<title>(.*?)</title>', full_content, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
            
            # 2. Priority 1 (P1): Manual Tags from .p2w-keyword elements (HIGHEST PRIORITY)
            # Use a more robust regex that ignores tag attributes
            kw_matches = re.findall(r'<a[^>]*class="p2w-keyword"[^>]*>(.*?)</a>', full_content, re.IGNORECASE | re.DOTALL)
            for kw in kw_matches:
                kw_text = re.sub(r'<[^>]+>', '', kw).strip()
                if kw_text:
                    p1_tags.add(kw_text)
            
            # --- CLEAN CONTENT FOR AUTO-PARSING ---
            # Strip <style> and <script> blocks to remove "var", "solid" etc.
            clean_body = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', full_content, flags=re.DOTALL | re.IGNORECASE)
            # Strip all other HTML tags
            clean_text = re.sub(r'<[^>]+>', ' ', clean_body)
            # Replace multiple spaces/newlines with single space
            clean_text = ' '.join(clean_text.split())
            
            # 3. Priority 2 (P2): YAKE Automatic Keyword Extraction (from Cleaned Body only)
            # Take first 5000 chars of body for analysis
            body_text = clean_text[:5000]
            yake_keywords = kw_extractor.extract_keywords(body_text)
            for kw, score in yake_keywords:
                # Avoid adding p1 tags again
                if kw.lower() not in [t.lower() for t in p1_tags]:
                    p2_tags.add(kw)
            
            # 4. Priority 4 (P4): Self-Learning Acronym Discovery (from Body)
            acronym_pairs = discover_acronyms(body_text)
            for full, acro in acronym_pairs:
                p4_tags.add(full)
                p4_tags.add(acro)
                
            # 5. Priority 3 (P3): Library-Driven Synonym Expansion (via Datamuse)
            # Expand manual tags AND discovered acronyms
            to_expand = list(p1_tags) + list(p4_tags)
            for tag in to_expand:
                if len(tag) > 2:
                    syns = get_synonyms(tag)
                    for s in syns:
                        if s.lower() not in [t.lower() for t in p1_tags] and s.lower() not in [t.lower() for t in p2_tags]:
                            p3_tags.add(s)
                            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    if title: title = re.sub(r'<[^>]+>', '', title)
    if not title: title = os.path.basename(filepath).split('.')[0].replace('-', ' ').title()
    return title, ", ".join(p1_tags), ", ".join(p2_tags), ", ".join(p3_tags), ", ".join(p4_tags)

def generate_index():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(base_dir)

    metadata = load_metadata()
    new_metadata = {}
    all_files = []
    active_langs = set()
    
    for entry in os.listdir('.'):
        if os.path.isdir(entry) and not entry.startswith('.') and entry not in ['node_modules', '__pycache__']:
            html_files = glob.glob(os.path.join(entry, '*.html'))
            if html_files:
                active_langs.add(entry)
                for f in html_files:
                    rel_path = os.path.relpath(f).replace('\\', '/')
                    title, p1, p2, p3, p4 = get_html_metadata(f, metadata)
                    paper_entry = { "lang": entry, "path": rel_path, "title": title, "p1": p1, "p2": p2, "p3": p3, "p4": p4 }
                    all_files.append(paper_entry)
                    new_metadata[rel_path] = { "title": title, "lang": entry, "p1_tags": p1, "p2_tags": p2, "p3_tags": p3, "p4_tags": p4 }
                    
    save_metadata(new_metadata)
    all_files.sort(key=lambda x: x['title'])
    active_langs = sorted(list(active_langs))

    filters_html = '<button class="filter-btn active" data-lang="all">All</button>\n'
    for lang in active_langs:
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        filters_html += f'        <button class="filter-btn" data-lang="{lang}">{display_name}</button>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jump2Paper archive</title>

  <!-- Open Graph / Social Media -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="Jump2Paper archive">
  <meta property="og:description" content="Explore Academic Papers in Professional Web Format. Optimized for readability and accessibility.">
  <meta property="og:image" content="./.github/images/og-image.png">
  <meta property="og:site_name" content="Jump2Paper archive">
  
  <!-- Fuse.js for Fuzzy Search -->
  <script src="https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.min.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@400;500;600&display=swap');

    :root {{
      --color-bg: #ffffff;
      --color-bg-soft: #f8f7f4;
      --color-text: #1a1a1a;
      --color-text-muted: #6b6b6b;
      --color-accent: #e8601c;
      --color-accent-light: #fdf0e8;
      --color-positive: #2d7d46;
      --color-positive-bg: #edf7f1;
      --color-negative: #c0392b;
      --color-negative-bg: #fdf0ee;
      --color-border: #e0ddd8;

      --font-body: 'Lora', Georgia, serif;
      --font-ui: 'DM Sans', system-ui, sans-serif;

      --text-base: 17px;
      --line-height: 1.8;
      --content-width: 800px;
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html {{ font-size: var(--text-base); }}

    body {{
      background: var(--color-bg);
      color: var(--color-text);
      font-family: var(--font-body);
      line-height: var(--line-height);
    }}

    .p2w-content {{ max-width: var(--content-width); margin: 0 auto; padding: 0 2rem; }}

    h1, h2, h3, h4, h5 {{ font-family: var(--font-ui); color: var(--color-text); line-height: 1.3; }}

    .p2w-hero {{
      padding: 5rem 0 3rem;
      border-bottom: 1px solid var(--color-border);
      text-align: center;
    }}
    .p2w-hero h1 {{ font-size: 2.4rem; font-weight: 600; margin-bottom: 1rem; }}
    .p2w-hero p {{ color: var(--color-text-muted); font-size: 1.1rem; }}

    /* 검색 및 필터 파트 */
    .controls-section {{
      padding: 2rem 0;
      border-bottom: 1px solid var(--color-border);
      background: var(--color-bg-soft);
    }}
    .controls-container {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      align-items: center;
    }}
    .search-input {{
      width: 100%;
      max-width: 500px;
      padding: 0.8rem 1.2rem;
      font-size: 1rem;
      font-family: var(--font-ui);
      border: 1px solid var(--color-border);
      border-radius: 8px;
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
      justify-content: center;
    }}
    .filter-btn {{
      font-family: var(--font-ui);
      font-size: 0.9rem;
      padding: 0.4rem 1.2rem;
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      color: var(--color-text-muted);
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn:hover {{ border-color: var(--color-accent); color: var(--color-accent); }}
    .filter-btn.active {{
      background: var(--color-accent);
      color: #fff;
      border-color: var(--color-accent);
    }}

    /* 문서 목록 파트 */
    .papers-section {{ padding: 3rem 0; min-height: 50vh; }}
    .paper-list {{ display: flex; flex-direction: column; gap: 1rem; }}
    .paper-card {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.2rem 1.5rem;
      border: 1px solid var(--color-border);
      border-radius: 8px;
      text-decoration: none;
      color: var(--color-text);
      transition: all 0.2s;
      background: var(--color-bg);
    }}
    .paper-card:hover {{
      border-color: var(--color-accent);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .paper-info {{ flex: 1; }}
    .paper-info h3 {{ font-size: 1.15rem; margin-bottom: 0.3rem; transition: color 0.2s; }}
    .paper-tags {{ 
      font-family: var(--font-ui); 
      font-size: 0.8rem; 
      color: var(--color-text-muted); 
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }}
    .tag-item {{
      background: #eee;
      padding: 0.1rem 0.4rem;
      border-radius: 3px;
    }}
    .paper-card:hover .paper-info h3 {{ color: var(--color-accent); }}
    
    /* 동적 언어 뱃지 공통 스타일 */
    .lang-badge {{
      font-family: var(--font-ui);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
      background: var(--color-bg-soft);
      border: 1px solid var(--color-border);
      color: var(--color-text-muted);
      margin-left: 1rem;
    }}
    .lang-badge.kr {{ background: #eef3fb; color: #3a6bbf; border: 1px solid #b8cef0; }}
    .lang-badge.en {{ background: var(--color-positive-bg); color: var(--color-positive); border: 1px solid #b8e0c8; }}
    
    /* 페이지네이션 */
    .pagination-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;
      margin-top: 3rem;
      font-family: var(--font-ui);
    }}
    .page-btn {{
      padding: 0.5rem 0.8rem;
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }}
    .page-btn:hover:not(:disabled) {{ border-color: var(--color-accent); color: var(--color-accent); }}
    .page-btn.active {{ background: var(--color-accent); color: white; border-color: var(--color-accent); }}
    .page-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    .no-results {{
      text-align: center;
      padding: 5rem 0;
      color: var(--color-text-muted);
      font-family: var(--font-ui);
      display: none;
    }}
  </style>
</head>
<body>

  <div class="p2w-hero">
    <div class="p2w-content">
      <h1>Paper2Web Archive</h1>
      <p>Explore our formatted academic papers.</p>
    </div>
  </div>

  <div class="controls-section">
    <div class="p2w-content controls-container">
      <input type="text" id="searchInput" class="search-input" placeholder="Search by title or category (e.g. LLM, RL)..." autocomplete="off">
      <div class="filter-group" id="filterGroup">
        {filters_html}      </div>
    </div>
  </div>

  <div class="papers-section p2w-content">
    <div class="paper-list" id="papersList">
"""
    
    for item in all_files:
        lang = item['lang']
        display_name = KNOWN_LANGS.get(lang.lower(), lang.upper())
        short_label = display_name.split(' (')[0] if ' (' in display_name else display_name
        
        # Sanitize attributes for HTML
        def clean_attr(val):
            return str(val).replace('\n', ' ').replace('\r', ' ').replace('"', '&quot;').strip()
            
        t_attr = clean_attr(item['title'])
        p1_attr = clean_attr(item['p1'])
        p2_attr = clean_attr(item['p2'])
        p3_attr = clean_attr(item['p3'])
        p4_attr = clean_attr(item['p4'])

        # UI Tags: Only show the HIGHEST priority tags (P1: Manual p2w-keywords)
        tags_html = ""
        ui_tags = [t.strip() for t in p1_attr.split(',') if t.strip()]
        if ui_tags:
            tags_html = '<div class="paper-tags">' + "".join([f'<span class="tag-item">{t}</span>' for t in ui_tags[:5]]) + '</div>'
        
        html_content += f"""
      <a href="{item['path']}" class="paper-card" data-title="{t_attr}" data-lang="{lang}" data-p1="{p1_attr}" data-p2="{p2_attr}" data-p3="{p3_attr}" data-p4="{p4_attr}">
        <div class="paper-info">
          <h3>{item['title']}</h3>
          {tags_html}
        </div>
        <div class="lang-badge {lang}">{short_label}</div>
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
    
    // Prepare data for Fuse.js
    const paperData = cards.map(card => ({
      el: card,
      title: card.getAttribute('data-title'),
      lang: card.getAttribute('data-lang'),
      p1: card.getAttribute('data-p1'),
      p2: card.getAttribute('data-p2'),
      p3: card.getAttribute('data-p3'),
      p4: card.getAttribute('data-p4')
    }));

    const fuse = new Fuse(paperData, {
      keys: [
        { name: 'title', weight: 2.0 }, // Absolute Top Priority
        { name: 'p1', weight: 0.8 },    // Manual Keywords (Priority 1)
        { name: 'p2', weight: 0.5 },    // Auto-extracted (Priority 2)
        { name: 'p3', weight: 0.2 },    // Synonyms (Priority 3)
        { name: 'p4', weight: 0.1 }     // Acronyms (Priority 4)
      ],
      threshold: 0.3, // Fuzzy threshold
      ignoreLocation: true
    });

    function updateView() {
      // 1. Filtering & Searching
      let results = [];
      
      // First, filter by language
      const langFiltered = paperData.filter(item => 
        currentLang === 'all' || item.lang === currentLang
      );

      if (currentSearch) {
        // Search within the language-filtered results
        const searchResults = fuse.search(currentSearch);
        // Only include those that are in our lang-filtered list
        results = searchResults
          .filter(r => langFiltered.includes(r.item))
          .map(r => r.item);
      } else {
        results = langFiltered;
      }

      // 2. Pagination
      const totalItems = results.length;
      const totalPages = Math.ceil(totalItems / pageSize);
      if (currentPage > totalPages) currentPage = Math.max(1, totalPages);

      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const paginatedItems = results.slice(start, end);

      // 3. Render
      // Hide everything first
      paperData.forEach(item => item.el.style.display = 'none');
      
      // Show matched & paginated items
      paginatedItems.forEach(item => item.el.style.display = 'flex');

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

      // Prev Button
      paginationControls.appendChild(createBtn('Prev', currentPage - 1, false, currentPage === 1));

      // Page Numbers (Simple version)
      for (let i = 1; i <= totalPages; i++) {
        if (totalPages > 7) {
          // Add some ellipsis logic if there are too many pages
          if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
             paginationControls.appendChild(createBtn(i, i, i === currentPage));
          } else if (i === currentPage - 2 || i === currentPage + 2) {
             const dot = document.createElement('span');
             dot.innerText = '...';
             paginationControls.appendChild(dot);
          }
        } else {
          paginationControls.appendChild(createBtn(i, i, i === currentPage));
        }
      }

      // Next Button
      paginationControls.appendChild(createBtn('Next', currentPage + 1, false, currentPage === totalPages));
    }

    searchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value.toLowerCase().trim();
      currentPage = 1; // Reset to first page
      updateView();
    });

    filterBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        filterBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentLang = e.target.getAttribute('data-lang');
        currentPage = 1; // Reset to first page
        updateView();
      });
    });

    // Initial View
    updateView();
  </script>
</body>
</html>
"""

    index_path = os.path.join(base_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"✅ Successfully created {index_path} with {len(all_files)} papers across {len(active_langs)} languages.")

if __name__ == "__main__":
    generate_index()
